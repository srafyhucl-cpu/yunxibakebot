"""
有赞商品事件处理器。

处理有赞 Webhook 推送的商品上下架及属性变更事件（item_*）：
- 物理宽表 Upsert（youzan_products）
- RAG 增量知识库同步（上架更新 / 下架物理擦除）
- 触点一：价格/库存异动审计埋点（price_sync / stock_alert）
"""

import datetime
import json
import re

from app.logger import setup_logger

logger = setup_logger()

# 知识库常见成分特征标签（用于 RAG 搜索词索引增强）
SPECIAL_INGREDIENTS = [
    "蜜红豆", "抹茶", "草莓", "芒果", "提拉米苏", "巧克力",
    "动物奶油", "夹心", "千层", "乳酪", "芝士", "冷藏", "保质期",
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

    found_ingredients = [ing for ing in SPECIAL_INGREDIENTS if ing in desc_clean or ing in title]
    return spec_names, prop_names, found_ingredients


def _build_rag_content(
    title: str, alias: str, status_lbl: str,
    skus: list, item_props: list,
    price_fen: int, stock: int, desc_clean: str, tags_str: str,
) -> str:
    """构建 RAG 知识库商品内容 Markdown 文本。"""
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
        sku_lines.append(f"- 规格型号【{prop_desc}】：售价 ￥{price_yuan:.2f} 元，当前可用库存 {qty} 件")
    skus_text = "\n".join(sku_lines) if sku_lines else f"- 规格：单售价 ￥{price_fen/100.0:.2f} 元，当前可用总库存 {stock} 件"

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
    props_text = "\n".join(prop_lines) if prop_lines else "- 定制加料选项：暂无特殊定制属性"

    detail_url = f"https://h5.youzan.com/v2/showcase/goods?alias={alias}"
    fallback_desc = "精品烘焙推荐，新西兰进口动物奶油调配，不含防腐剂。建议0-4℃冷藏并于3天内食用完毕。"
    return (
        f"商品名称：{title}\n"
        f"在售状态：{status_lbl}\n"
        f"商品规格及秒级实时库存明细：\n{skus_text}\n\n"
        f"可定制口味、蛋糕胚、夹心及甜度选项（SPU 自定义属性）：\n{props_text}\n\n"
        f"商品特征与配方属性标签：{tags_str}\n"
        f"直购下单链接：{detail_url}\n"
        f"原料配方、保质期及夹心介绍：\n{desc_clean or fallback_desc}"
    )


async def _sync_rag_knowledge(
    db, knowledge_retriever,
    item_id: int, title: str, content_md: str,
    tags_str: str, updated_at_str: str, is_active: int,
) -> None:
    """根据商品在售状态增量更新或擦除 RAG 知识库条目。"""
    from app.repository.knowledge_repo import KnowledgeRepo
    knowledge_repo = KnowledgeRepo(db)

    if is_active == 1:
        await knowledge_repo.upsert_product_knowledge(
            youzan_item_id=str(item_id),
            title=title,
            content=content_md,
            keywords=f"商品, 价格, 推荐, 蛋糕, {title}, {tags_str}",
            priority=50,
            updated_at=updated_at_str,
        )
        vs = knowledge_retriever._vs
        if vs:
            vector = vs._get_model().encode([f"{title} {content_md}"], normalize_embeddings=True)[0].tolist()
            await vs.upsert_one(str(item_id), vector)
    else:
        await knowledge_repo.delete_product_knowledge(str(item_id))
        vs = knowledge_retriever._vs
        if vs:
            await vs.delete_one(str(item_id))


async def handle_item_event(
    db, youzan_client, knowledge_retriever, event_type: str, msg_obj: dict, updated_at_str: str
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
    _inner_data: dict = {}
    if not item_id:
        try:
            _raw_data = msg_obj.get("data", "{}")
            _inner_data = json.loads(_raw_data) if isinstance(_raw_data, str) else _raw_data
            item_id = _inner_data.get("item_id", 0)
        except Exception as exc:
            logger.warning("解析有赞事件内层 data 失败: %s", exc)
    if not item_id:
        logger.warning("有赞商品事件缺少 item_id")
        return

    logger.info("开始处理有赞商品 Webhook 事件 [%s]: item_id=%s", event_type, item_id)

    product_repo = YouzanProductRepo(db)
    analytics_repo = AnalyticsRepo(db)

    try:
        old_price, old_stock = -1, -1
        local_product = await product_repo.get_by_id(item_id)
        if local_product:
            old_price = local_product["price_fen"]
            old_stock = local_product["stock"]

        raw_product = await youzan_client.get_product(item_id)

        outer_data = raw_product.get("data") or raw_product.get("response") if isinstance(raw_product, dict) else None
        if not isinstance(outer_data, dict) or "item" not in outer_data:
            return

        item_data = outer_data["item"]
        title = item_data.get("title", "")
        alias = item_data.get("alias", "")
        price_fen = item_data.get("price", 0)
        stock = item_data.get("quantity", 0)
        image = item_data.get("pic_url") or item_data.get("image") or ""
        is_active = 0 if ("instock" in event_type or event_type.endswith("Instock")) else 1
        if event_type == "ITEM_STATE" and "is_display" in _inner_data:
            is_active = 1 if _inner_data.get("is_display") else 0
        skus = item_data.get("skus", [])
        item_props = item_data.get("item_props", [])

        raw_desc = item_data.get("desc", "") or item_data.get("summary", "") or ""
        desc_clean = re.sub(r"\s+", " ", re.sub(r"\n+", "\n", re.sub(r"<.*?>", "", raw_desc))).strip()

        spec_names, prop_names, found_ingredients = _extract_item_tags(title, skus, item_props, desc_clean)
        status_lbl = "在售" if is_active == 1 else "下架"
        tags_str = ", ".join([status_lbl] + list(set(spec_names)) + list(set(prop_names)) + list(set(found_ingredients)))

        await product_repo.upsert_product(
            item_id=item_id,
            title=title,
            alias=alias,
            price_fen=price_fen,
            stock=stock,
            image=image,
            is_active=is_active,
            updated_at=updated_at_str,
            skus_json=json.dumps(skus, ensure_ascii=False),
            item_props_json=json.dumps(item_props, ensure_ascii=False),
            desc=desc_clean,
            tags=tags_str,
        )

        content_md = _build_rag_content(title, alias, status_lbl, skus, item_props, price_fen, stock, desc_clean, tags_str)
        await _sync_rag_knowledge(db, knowledge_retriever, item_id, title, content_md, tags_str, updated_at_str, is_active)

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if old_price != -1 and old_price != price_fen:
            await analytics_repo.add_event(
                session_id=None, buyer_id=None, event_type="price_sync",
                event_source="webhook_youzan", ref_id=str(item_id),
                meta_data=json.dumps({"product_title": title, "old_price_fen": old_price, "new_price_fen": price_fen}, ensure_ascii=False),
                created_at=now_str,
            )
            logger.info("已成功记录商品价格调价审计埋点: title=%s, old=%d, new=%d", title, old_price, price_fen)

        if old_stock != -1 and old_stock != stock:
            await analytics_repo.add_event(
                session_id=None, buyer_id=None, event_type="stock_alert",
                event_source="webhook_youzan", ref_id=str(item_id),
                meta_data=json.dumps({"product_title": title, "old_stock": old_stock, "new_stock": stock}, ensure_ascii=False),
                created_at=now_str,
            )
            logger.info("已成功记录商品库存预警审计埋点: title=%s, old_stock=%d, new_stock=%d", title, old_stock, stock)

    except Exception as exc:
        logger.error("处理有赞商品系统事件失败: item_id=%s err=%s", item_id, exc)
