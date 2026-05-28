"""
Function Calling 工具实现：商品查询与知识库检索。

提供 get_product_info（RAG 检索 + 实时有赞 API 刷新 + AI 导购埋点）和 search_knowledge（通用知识库检索）。
"""

from __future__ import annotations

import datetime
import json
import re
from typing import TYPE_CHECKING

from app.logger import setup_logger
from app.utils import now_str
from app.models.content_change_history import (
    ChangeAction,
    ChangeEntityType,
    SyncSource,
    WriteResult,
)
from app.models.session import Session
from app.repository.content_change_history_repo import ContentChangeHistoryRepo
from app.service.llm.function_defs import KNOWLEDGE_SEARCH_LIMIT, PRODUCT_SEARCH_LIMIT
from app.service.knowledge_admin import DEFAULT_PRIORITY
from app.service.observability import ContentChangeLogger, build_product_change_summary
from app.service.youzan.event_item import _build_rag_content, _extract_item_tags

if TYPE_CHECKING:
    from app.service.knowledge_retriever import KnowledgeRetriever
    from app.service.youzan.client import YouzanClient

logger = setup_logger()

PRODUCT_CACHE_TTL_SECONDS = 300


async def _get_cached_product_if_fresh(item_id: int, db) -> dict | None:
    """
    检查 youzan_products 表中商品是否在 TTL 内仍然新鲜。
    若 updated_at 距现在不超过 PRODUCT_CACHE_TTL_SECONDS，返回基本信息字典；
    否则返回 None，触发实时刷新。
    """
    from app.repository.youzan_repo import YouzanProductRepo
    product = await YouzanProductRepo(db).get_by_id(item_id)
    if not product or not product.get("updated_at"):
        return None
    try:
        updated_dt = datetime.datetime.strptime(product["updated_at"], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    age_seconds = (datetime.datetime.now() - updated_dt).total_seconds()
    if age_seconds > PRODUCT_CACHE_TTL_SECONDS:
        return None
    logger.debug("商品 TTL 缓存命中: item_id=%s age_seconds=%.1f", item_id, age_seconds)
    return {
        "item_id": item_id,
        "title": product["title"],
        "price_fen": product["price_fen"],
        "stock": product["stock"],
        "tags": product.get("tags", ""),
        "updated_at": product["updated_at"],
        "desc": product.get("desc", ""),
        "skus": json.loads(product.get("skus_json") or "[]"),
    }


async def _refresh_product_live(
    item_id: int,
    youzan_client: YouzanClient,
    db,
    knowledge_retriever: KnowledgeRetriever,
) -> dict | None:
    """
    调用有赞 API 获取商品实时数据，回写 youzan_products + knowledge_base + 向量索引。
    返回商品基本信息字典，失败时返回 None。
    """
    from app.repository.youzan_repo import YouzanProductRepo
    from app.repository.knowledge_repo import KnowledgeRepo
    history_logger = ContentChangeLogger(ContentChangeHistoryRepo(db))

    try:
        raw = await youzan_client.get_product(item_id)
        if isinstance(raw, dict) and raw.get("gw_err_resp"):
            logger.error("商品实时刷新 API 拒绝: item_id=%s err=%s", item_id, raw["gw_err_resp"])
            await history_logger.log_failed(
                entity_type=ChangeEntityType.PRODUCT,
                entity_key=str(item_id),
                category="product",
                title=f"商品 {item_id}",
                source=SyncSource.CHAT_LIVE_REFRESH,
                source_ref=str(item_id),
                action=ChangeAction.UPSERT,
                error_type="gw_err_resp",
                error_message=str(raw["gw_err_resp"]),
            )
            return None
        outer = raw.get("data") or raw.get("response") if isinstance(raw, dict) else None
        if not isinstance(outer, dict) or "item" not in outer:
            logger.error("商品实时刷新响应结构异常: item_id=%s raw_keys=%s", item_id, list(raw.keys()) if isinstance(raw, dict) else type(raw))
            await history_logger.log_failed(
                entity_type=ChangeEntityType.PRODUCT,
                entity_key=str(item_id),
                category="product",
                title=f"商品 {item_id}",
                source=SyncSource.CHAT_LIVE_REFRESH,
                source_ref=str(item_id),
                action=ChangeAction.UPSERT,
                error_type="missing_item",
                error_message="商品接口响应缺少 item",
            )
            return None
        item = outer["item"]
        title = item.get("title", "")
        alias = item.get("alias", "") or str(item_id)
        price_fen = item.get("price", 0)
        stock = item.get("quantity", 0)
        image = item.get("pic_url") or item.get("image") or ""
        skus = item.get("skus", [])
        item_props = item.get("item_props", [])
        raw_desc = item.get("desc", "") or item.get("summary", "") or ""
        desc_clean = re.sub(r"\s+", " ", re.sub(r"\n+", "\n", re.sub(r"<.*?>", "", raw_desc))).strip()
        spec_names, prop_names, ingredients = _extract_item_tags(title, skus, item_props, desc_clean)
        tags_str = ", ".join(["\u5728\u552e"] + list(set(spec_names)) + list(set(prop_names)) + list(set(ingredients)))
        updated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        product_result = await YouzanProductRepo(db).upsert_product(
            item_id=item_id, title=title, alias=alias, price_fen=price_fen,
            stock=stock, image=image, is_active=1, updated_at=updated_at,
            skus_json=json.dumps(skus, ensure_ascii=False),
            item_props_json=json.dumps(item_props, ensure_ascii=False),
            desc=desc_clean, tags=tags_str,
            sync_source=SyncSource.CHAT_LIVE_REFRESH,
            sync_ref=str(item_id),
        )
        content_md = _build_rag_content(title, alias, "\u5728\u552e", skus, item_props, price_fen, stock, desc_clean, tags_str, item_id=item_id, image=image)
        knowledge_result = await KnowledgeRepo(db).upsert_product_knowledge(
            youzan_item_id=str(item_id), title=title, content=content_md,
            keywords=f"\u5546\u54c1, \u4ef7\u683c, \u63a8\u8350, \u86cb\u7cd5, {title}, {tags_str}",
            priority=DEFAULT_PRIORITY, updated_at=updated_at,
            sync_source=SyncSource.CHAT_LIVE_REFRESH,
            sync_ref=str(item_id),
        )
        vs = knowledge_retriever._vs
        if vs and knowledge_result == WriteResult.APPLIED:
            vector = vs._get_model().encode([f"{title} {content_md}"], normalize_embeddings=True)[0].tolist()
            await vs.upsert_one(str(item_id), vector)
        if product_result == WriteResult.APPLIED or knowledge_result == WriteResult.APPLIED:
            await history_logger.log_success(
                entity_type=ChangeEntityType.PRODUCT,
                entity_key=str(item_id),
                category="product",
                title=title,
                source=SyncSource.CHAT_LIVE_REFRESH,
                source_ref=str(item_id),
                action=ChangeAction.UPSERT,
                change_summary=build_product_change_summary(
                    item_id=item_id,
                    title=title,
                    alias=alias,
                    price_fen=price_fen,
                    stock=stock,
                    is_active=1,
                    tags=tags_str,
                    updated_at=updated_at,
                    product_result=product_result,
                    knowledge_result=knowledge_result,
                ),
                occurred_at=updated_at,
            )
        logger.info("商品实时刷新写入成功: item_id=%s title=%s", item_id, title)
        return {"item_id": item_id, "title": title, "price_fen": price_fen, "stock": stock,
                "tags": tags_str, "updated_at": updated_at}
    except Exception as exc:
        logger.error("商品实时刷新失败: item_id=%s err=%s", item_id, exc)
        await history_logger.log_failed(
            entity_type=ChangeEntityType.PRODUCT,
            entity_key=str(item_id),
            category="product",
            title=f"商品 {item_id}",
            source=SyncSource.CHAT_LIVE_REFRESH,
            source_ref=str(item_id),
            action=ChangeAction.UPSERT,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        return None


async def get_product_info(
    knowledge_retriever: KnowledgeRetriever,
    session: Session | None = None,
    youzan_client: YouzanClient | None = None,
    product_name: str = "",
    product_id: str = "",
) -> str:
    """查询商品信息。当 product_id 为数字 item_id 且 youzan_client 可用时，先实时调用有赞 API 刷新数据；
    否则按名称走 RAG 检索，并静默注入 AI 导购推荐埋点。"""
    if product_id and product_id.isdigit() and youzan_client is not None:
        db = knowledge_retriever._repo._db
        cached = await _get_cached_product_if_fresh(int(product_id), db)
        if cached is not None:
            return json.dumps({"source": "db_cache", "product": cached}, ensure_ascii=False)
        live = await _refresh_product_live(int(product_id), youzan_client, db, knowledge_retriever)
        if live:
            return json.dumps({"source": "live_api", "product": live}, ensure_ascii=False)
        return json.dumps({"message": "\u5b9e时商品查询失败，请稍后重试"}, ensure_ascii=False)

    query = product_name or product_id
    if not query:
        return json.dumps({"message": "未提供商品名称或ID"}, ensure_ascii=False)
    try:
        entries = await knowledge_retriever.search(query, limit=PRODUCT_SEARCH_LIMIT)
    except Exception as exc:
        logger.error("商品知识检索失败: query=%s err=%s", query, exc)
        return json.dumps({"message": "商品查询暂时无法使用，请联系人工客服"}, ensure_ascii=False)
    if not entries:
        return json.dumps({"query": query, "results": [], "message": "未找到相关商品知识"}, ensure_ascii=False)

    # 触点三：AI 会话导购推荐埋点（内置 1 小时排他防刷滑动窗口去重）
    if session:
        from app.repository.analytics_repo import AnalyticsRepo
        db = knowledge_retriever._repo._db
        analytics_repo = AnalyticsRepo(db)

        for entry in entries:
            if entry.youzan_item_id:
                try:
                    from app.repository.youzan_repo import YouzanProductRepo
                    product_repo = YouzanProductRepo(db)
                    product = await product_repo.get_by_id(int(entry.youzan_item_id))
                    if product:
                        alias = product["alias"]
                        is_duplicate = await analytics_repo.check_recent_recommend(session.id, alias, hour_limit=1)
                        if not is_duplicate:
                            await analytics_repo.add_event(
                                session_id=session.id,
                                buyer_id=session.user_id,
                                event_type="product_recommend",
                                event_source="ai_bot",
                                ref_id=alias,
                                meta_data=json.dumps({"title": entry.title}, ensure_ascii=False),
                                created_at=now_str(),
                            )
                            logger.info("已成功记录 AI 推荐埋点触点 (1小时防刷校验通过): session=%s, alias=%s", session.id, alias)
                        else:
                            logger.debug("同会话1小时内针对同款商品产生过推荐行为，执行幂等去重跳过写入: alias=%s", alias)
                except Exception as telemetry_exc:
                    logger.warning("AI 推荐埋点记录失败: %s", telemetry_exc)

    results = [{"title": e.title, "content": e.content, "category": e.category} for e in entries]
    return json.dumps({"query": query, "results": results}, ensure_ascii=False)


async def search_knowledge(knowledge_retriever: KnowledgeRetriever, query: str) -> str:
    """使用知识库检索常见问题、店铺政策、产品介绍等。"""
    try:
        entries = await knowledge_retriever.search(query, limit=KNOWLEDGE_SEARCH_LIMIT)
    except Exception as exc:
        logger.error("知识库检索失败: query=%s err=%s", query, exc)
        return json.dumps({"query": query, "results": [], "message": "知识库查询失败，请稍后重试"}, ensure_ascii=False)
    if not entries:
        return json.dumps({"query": query, "results": [], "message": "未找到相关知识"}, ensure_ascii=False)
    results = [{"title": e.title, "content": e.content, "category": e.category} for e in entries]
    return json.dumps({"query": query, "results": results}, ensure_ascii=False)
