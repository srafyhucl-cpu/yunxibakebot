"""
Function Calling 工具实现：商品查询与知识库检索。

提供 get_product_info（RAG 检索 + AI 导购埋点）和 search_knowledge（通用知识库检索）。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.logger import setup_logger
from app.models.session import Session
from app.service.llm.function_defs import KNOWLEDGE_SEARCH_LIMIT, PRODUCT_SEARCH_LIMIT

if TYPE_CHECKING:
    from app.service.knowledge_retriever import KnowledgeRetriever

logger = setup_logger()


async def get_product_info(
    knowledge_retriever: KnowledgeRetriever,
    session: Session | None = None,
    product_name: str = "",
    product_id: str = "",
) -> str:
    """使用知识库（RAG+双轨制）检索商品信息，并静默注入 AI 导购推荐埋点触点。"""
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
        import datetime
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
                                created_at=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
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
