"""
有赞商品事件处理器。

处理有赞 Webhook 推送的商品上下架及属性变更事件（item_*）：
- 物理宽表 Upsert（youzan_products）
- RAG 增量知识库同步（上架更新 / 下架物理擦除）
- 触点一：价格/库存异动审计埋点（price_sync / stock_alert）
"""

import json

from app.logger import setup_logger
from app.models.content_change_history import (
    ChangeAction,
    ChangeEntityType,
    SyncSource,
    WriteResult,
)
from app.models.youzan_webhook_event import (
    YouzanWebhookBusinessType,
    YouzanWebhookStatus,
)
from app.repository.content_change_history_repo import ContentChangeHistoryRepo
from app.repository.youzan_webhook_event_repo import YouzanWebhookEventRepo
from app.service.knowledge_admin import DEFAULT_PRIORITY
from app.service.youzan.audit_helper import mark_audit
from app.service.youzan.client import YOUZAN_GOODS_H5_BASE_URL
from app.service.observability import (
    ContentChangeLogger,
    build_product_change_summary,
)
from app.utils import now_str

logger = setup_logger()

# 知识库常见成分特征标签（用于 RAG 搜索词索引增强）
SPECIAL_INGREDIENTS = [
    "蜜红豆",
    "抹茶",
    "草莓",
    "芒果",
    "提拉米苏",
    "巧克力",
    "动物奶油",
    "夹心",
    "千层",
    "乳酪",
    "芝士",
    "冷藏",
    "保质期",
]


def _extract_item_tags(
    title: str, skus: list, item_props: list, desc_clean: str
) -> tuple[list, list, list]:
    """从 SKU 和属性配置中提取规格名称、属性名称和成分标签。"""
    spec_names: list[str] = []
    for sku in skus:
        prop_json = sku.get("properties_name_json", "")
        if prop_json:
            try:
                props = json.loads(prop_json)
                spec_names.extend(p.get("v", "") for p in props if p.get("v", ""))
            except Exception as exc:
                logger.warning("解析商品规格失败: %s", exc)

    prop_names: list[str] = []
    for prop in item_props:
        if prop.get("prop_name", ""):
            prop_names.append(prop["prop_name"])
        for model in prop.get("text_models", []):
            if model.get("prop_text_name", ""):
                prop_names.append(model["prop_text_name"])

    found_ingredients = [
        ing for ing in SPECIAL_INGREDIENTS if ing in desc_clean or ing in title
    ]
    return spec_names, prop_names, found_ingredients


def _build_rag_content(
    title: str,
    alias: str,
    status_lbl: str,
    skus: list,
    item_props: list,
    price_fen: int,
    stock: int,
    desc_clean: str,
    tags_str: str,
    item_id: int = 0,
    image: str = "",
) -> str:
    """构建 RAG 知识库商品内容 Markdown 文本。末尾附 UMP 商品卡片标签供 LLM 原样输出。"""
    sku_lines: list[str] = []
    for sku in skus:
        price_yuan = sku.get("price", price_fen) / 100.0
        qty = sku.get("quantity", 0)
        prop_json = sku.get("properties_name_json", "")
        prop_desc = "标准规格"
        if prop_json:
            try:
                props = json.loads(prop_json)
                prop_desc = " | ".join(f"{p.get('k')}:{p.get('v')}" for p in props)
            except Exception as exc:
                logger.warning("解析 SKU 属性失败: %s", exc)
        sku_lines.append(
            f"- 规格型号【{prop_desc}】：售价 ￥{price_yuan:.2f} 元，当前可用库存 {qty} 件"
        )
    skus_text = (
        "\n".join(sku_lines)
        if sku_lines
        else f"- 规格：单售价 ￥{price_fen / 100.0:.2f} 元，当前可用总库存 {stock} 件"
    )

    prop_lines: list[str] = []
    for prop in item_props:
        p_name = prop.get("prop_name", "")
        is_mult = " (允许多选)" if prop.get("is_multiple") else " (单选)"
        options = []
        for model in prop.get("text_models", []):
            opt_val = model.get("prop_text_name", "")
            opt_price = model.get("price", 0) / 100.0
            opt_price_desc = f" (加价: +￥{opt_price:.2f}元)" if opt_price > 0 else ""
            options.append(f"{opt_val}{opt_price_desc}")
        prop_lines.append(f"- 【{p_name}】{is_mult}：{'、'.join(options)}")
    props_text = (
        "\n".join(prop_lines) if prop_lines else "- 定制加料选项：暂无特殊定制属性"
    )

    from urllib.parse import quote as _q

    detail_url = f"{YOUZAN_GOODS_H5_BASE_URL}?alias={alias}"
    fallback_desc = "精品烘焙推荐，新西兰进口动物奶油调配，不含防腐剂。建议0-4℃冷藏并于3天内食用完毕。"
    ump_line = ""
    if item_id and image and alias:
        min_price_fen = min(
            (s.get("price", price_fen) for s in skus), default=price_fen
        )
        price_str = f"{min_price_fen / 100:.2f}"
        ump_line = (
            f"\n[UMP: type=card&id={item_id}&title={_q(title)}"
            f"&price={price_str}&src={_q(image)}"
            f"&url={_q(detail_url)}]"
        )
    return (
        f"商品名称：{title}\n"
        f"在售状态：{status_lbl}\n"
        f"商品规格及秒级实时库存明细：\n{skus_text}\n\n"
        f"可定制口味、蛋糕胚、夹心及甜度选项（SPU 自定义属性）：\n{props_text}\n\n"
        f"商品特征与配方属性标签：{tags_str}\n"
        f"直购下单链接：{detail_url}\n"
        f"原料配方、保质期及夹心介绍：\n{desc_clean or fallback_desc}" + ump_line
    )


async def _sync_rag_knowledge(
    db,
    knowledge_retriever,
    item_id: int,
    title: str,
    content_md: str,
    tags_str: str,
    updated_at_str: str,
    is_active: int,
) -> str:
    """根据商品在售状态增量更新或擦除 RAG 知识库条目。"""
    from app.repository.knowledge_product_repo import KnowledgeProductRepo

    knowledge_repo = KnowledgeProductRepo(db)

    if is_active == 1:
        result = await knowledge_repo.upsert_product_knowledge(
            youzan_item_id=str(item_id),
            title=title,
            content=content_md,
            keywords=f"商品, 价格, 推荐, 蛋糕, {title}, {tags_str}",
            priority=DEFAULT_PRIORITY,
            updated_at=updated_at_str,
            sync_source=SyncSource.YOUZAN_WEBHOOK,
            sync_ref=str(item_id),
        )
        vs = knowledge_retriever._vs
        if vs and result == WriteResult.APPLIED:
            vector = (
                vs._get_model()
                .encode([f"{title} {content_md}"], normalize_embeddings=True)[0]
                .tolist()
            )
            await vs.upsert_one(str(item_id), vector)
        return result
    else:
        result = await knowledge_repo.delete_product_knowledge(
            str(item_id),
            sync_source=SyncSource.YOUZAN_WEBHOOK,
            sync_ref=str(item_id),
        )
        vs = knowledge_retriever._vs
        if vs and result == WriteResult.APPLIED:
            await vs.delete_one(str(item_id))
        return result


async def handle_item_event(
    db,
    youzan_client,
    knowledge_retriever,
    event_type: str,
    msg_obj: dict,
    updated_at_str: str,
    msg_id: str = "",
    audit_repo: YouzanWebhookEventRepo | None = None,
    audit_id: int | None = None,
) -> None:
    """
    处理有赞商品系统事件。

    参数：
        db: aiosqlite 数据库连接
        youzan_client: 共享 YouzanClient 单例（避免并发刷新 token 竞态）
        knowledge_retriever: 知识检索器（用于 RAG 向量同步）
        event_type: 事件类型（如 item_ItemAdd）
        msg_obj: 有赞 Webhook msg 字段解码后的字典
        updated_at_str: 事件时间字符串
    """
    from app.repository.youzan_repo import YouzanProductRepo
    from app.repository.analytics_repo import AnalyticsRepo

    item_id = msg_obj.get("item_id", 0)
    # 始终解析内层 data：ITEM_STATE 的 is_display 等状态字段依赖它，
    # 不能因 item_id 已由上游解析而跳过，否则会丢失下架状态判定
    _inner_data: dict = {}
    _raw_data = msg_obj.get("data", "{}")
    try:
        _parsed = json.loads(_raw_data) if isinstance(_raw_data, str) else _raw_data
        _inner_data = _parsed if isinstance(_parsed, dict) else {}
    except Exception as exc:
        logger.warning("解析有赞事件内层 data 失败: %s", exc)
    if not item_id:
        item_id = _inner_data.get("item_id", 0)
    if not item_id:
        logger.warning("有赞商品事件缺少 item_id")
        await mark_audit(
            audit_repo,
            audit_id,
            YouzanWebhookStatus.SKIPPED,
            "item_missing_item_id",
            business_type=YouzanWebhookBusinessType.ITEM,
            error_type="missing_item_id",
        )
        return

    logger.info("开始处理有赞商品 Webhook 事件 [%s]: item_id=%s", event_type, item_id)
    await mark_audit(
        audit_repo,
        audit_id,
        YouzanWebhookStatus.PROCESSING,
        "item_api_fetch",
        business_type=YouzanWebhookBusinessType.ITEM,
        business_key=str(item_id),
    )

    product_repo = YouzanProductRepo(db)
    analytics_repo = AnalyticsRepo(db)
    history_logger = ContentChangeLogger(ContentChangeHistoryRepo(db))

    try:
        old_price, old_stock = -1, -1
        local_product = await product_repo.get_by_id(item_id)
        if local_product:
            old_price = local_product["price_fen"]
            old_stock = local_product["stock"]

        raw_product = await youzan_client.get_product(item_id)

        if isinstance(raw_product, dict) and raw_product.get("gw_err_resp"):
            logger.error(
                "商品事件 API 拒绝: item_id=%s err=%s",
                item_id,
                raw_product["gw_err_resp"],
            )
            await mark_audit(
                audit_repo,
                audit_id,
                YouzanWebhookStatus.FAILED,
                "item_api_rejected",
                business_type=YouzanWebhookBusinessType.ITEM,
                error_type="gw_err_resp",
                error_message=str(raw_product["gw_err_resp"]),
                business_key=str(item_id),
            )
            await history_logger.log_failed(
                entity_type=ChangeEntityType.PRODUCT,
                entity_key=str(item_id),
                category="product",
                title=f"商品 {item_id}",
                source=SyncSource.YOUZAN_WEBHOOK,
                source_ref=str(item_id),
                webhook_msg_id=msg_id,
                action=ChangeAction.UPSERT,
                error_type="gw_err_resp",
                error_message=str(raw_product["gw_err_resp"]),
            )
            return
        from app.service.youzan.product_sync import (
            parse_product_from_api,
            build_tags_str,
            sync_product_to_db,
            sync_product_to_rag,
        )

        parsed = parse_product_from_api(raw_product, item_id)
        if parsed is None:
            logger.error("商品事件响应结构异常: item_id=%s", item_id)
            await mark_audit(
                audit_repo,
                audit_id,
                YouzanWebhookStatus.FAILED,
                "item_api_bad_response",
                business_type=YouzanWebhookBusinessType.ITEM,
                error_type="missing_item",
                business_key=str(item_id),
            )
            await history_logger.log_failed(
                entity_type=ChangeEntityType.PRODUCT,
                entity_key=str(item_id),
                category="product",
                title=f"商品 {item_id}",
                source=SyncSource.YOUZAN_WEBHOOK,
                source_ref=str(item_id),
                webhook_msg_id=msg_id,
                action=ChangeAction.UPSERT,
                error_type="missing_item",
                error_message="商品接口响应缺少 item",
            )
            return

        title = parsed["title"]
        is_active = (
            0 if ("instock" in event_type or event_type.endswith("Instock")) else 1
        )
        if event_type == "ITEM_STATE" and "is_display" in _inner_data:
            is_active = 1 if _inner_data.get("is_display") else 0
        else:
            _is_explicit_state_event = (
                "instock" in event_type.lower()
                or "onsale" in event_type.lower()
                or event_type == "ITEM_STATE"
            )
            if not _is_explicit_state_event and local_product is not None:
                is_active = local_product["is_active"]

        status_lbl = "在售" if is_active == 1 else "下架"
        tags_str = build_tags_str(parsed, status_lbl)

        product_result = await sync_product_to_db(
            product_repo,
            parsed,
            is_active,
            updated_at_str,
            tags_str,
            SyncSource.YOUZAN_WEBHOOK,
            str(item_id),
        )
        knowledge_result = await sync_product_to_rag(
            db,
            knowledge_retriever,
            parsed,
            is_active,
            tags_str,
            status_lbl,
            updated_at_str,
            SyncSource.YOUZAN_WEBHOOK,
            str(item_id),
        )

        price_fen = parsed["price_fen"]
        stock = parsed["stock"]
        event_time = now_str()
        if old_price != -1 and old_price != price_fen:
            await analytics_repo.add_event(
                session_id=None,
                buyer_id=None,
                event_type="price_sync",
                event_source="webhook_youzan",
                ref_id=str(item_id),
                meta_data=json.dumps(
                    {
                        "product_title": title,
                        "old_price_fen": old_price,
                        "new_price_fen": price_fen,
                    },
                    ensure_ascii=False,
                ),
                created_at=event_time,
            )
            logger.info(
                "已成功记录商品价格调价审计埋点: title=%s, old=%d, new=%d",
                title,
                old_price,
                price_fen,
            )

        if old_stock != -1 and old_stock != stock:
            await analytics_repo.add_event(
                session_id=None,
                buyer_id=None,
                event_type="stock_alert",
                event_source="webhook_youzan",
                ref_id=str(item_id),
                meta_data=json.dumps(
                    {
                        "product_title": title,
                        "old_stock": old_stock,
                        "new_stock": stock,
                    },
                    ensure_ascii=False,
                ),
                created_at=event_time,
            )
            logger.info(
                "已成功记录商品库存预警审计埋点: title=%s, old_stock=%d, new_stock=%d",
                title,
                old_stock,
                stock,
            )
        if (
            product_result == WriteResult.APPLIED
            or knowledge_result == WriteResult.APPLIED
        ):
            await history_logger.log_success(
                entity_type=ChangeEntityType.PRODUCT,
                entity_key=str(item_id),
                category="product",
                title=title,
                source=SyncSource.YOUZAN_WEBHOOK,
                source_ref=str(item_id),
                webhook_msg_id=msg_id,
                action=ChangeAction.UPSERT
                if is_active == 1
                else ChangeAction.DEACTIVATE,
                change_summary=build_product_change_summary(
                    item_id=item_id,
                    title=title,
                    alias=parsed["alias"],
                    price_fen=price_fen,
                    stock=stock,
                    is_active=is_active,
                    tags=tags_str,
                    product_result=product_result,
                    knowledge_result=knowledge_result,
                    updated_at=updated_at_str,
                    old_price_fen=old_price
                    if old_price != -1 and old_price != price_fen
                    else None,
                    old_stock=old_stock
                    if old_stock != -1 and old_stock != stock
                    else None,
                ),
                occurred_at=updated_at_str,
            )
        await mark_audit(
            audit_repo,
            audit_id,
            YouzanWebhookStatus.PROCESSED,
            "item_processed",
            business_type=YouzanWebhookBusinessType.ITEM,
            business_key=str(item_id),
        )

    except Exception as exc:
        logger.error("处理有赞商品系统事件失败: item_id=%s err=%s", item_id, exc)
        await history_logger.log_failed(
            entity_type=ChangeEntityType.PRODUCT,
            entity_key=str(item_id),
            category="product",
            title=f"商品 {item_id}",
            source=SyncSource.YOUZAN_WEBHOOK,
            source_ref=str(item_id),
            webhook_msg_id=msg_id,
            action=ChangeAction.UPSERT,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        await mark_audit(
            audit_repo,
            audit_id,
            YouzanWebhookStatus.FAILED,
            "item_failed",
            business_type=YouzanWebhookBusinessType.ITEM,
            error_type=type(exc).__name__,
            error_message=str(exc),
            business_key=str(item_id),
        )
