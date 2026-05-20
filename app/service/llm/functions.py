"""
Function Calling 工具定义与分发。

定义 LLM 可调用的工具：查订单、查商品、查物流、搜知识库。
dispatch_tool 根据工具名称路由到对应处理函数。

注意：transfer_to_human 工具由 ChatService 的工具调度循环直接处理，
不经过本模块，因为它需要 TransferManager 的依赖。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.logger import setup_logger
from app.models.session import Session

if TYPE_CHECKING:
    from app.service.knowledge_retriever import KnowledgeRetriever

# 最大连续工具调用轮数，超限后输出兜底回复
MAX_TOOL_ROUNDS = 3
# 知识检索返回条目数上限
PRODUCT_SEARCH_LIMIT = 3
KNOWLEDGE_SEARCH_LIMIT = 5

logger = setup_logger()

# DeepSeek Function Calling 工具定义（按需扩展）
FUNCTION_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_order_info",
            "description": "查询订单详细信息：状态、商品、金额、收货地址等",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_no": {"type": "string", "description": "订单号"},
                },
                "required": ["order_no"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_info",
            "description": "查询商品详情：价格、规格、库存等",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "商品名称"},
                    "product_id": {"type": "string", "description": "商品ID"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_logistics_info",
            "description": "查询物流配送进度",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_no": {"type": "string", "description": "订单号"},
                },
                "required": ["order_no"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_to_human",
            "description": "当用户要求转人工、表达不满或复杂售后问题时，转接人工客服",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "转人工原因"},
                },
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "搜索知识库，查找常见问题、店铺政策、产品介绍等",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                },
                "required": ["query"],
            },
        },
    },
]


async def get_order_info(knowledge_retriever: KnowledgeRetriever, order_no: str) -> str:
    """
    查询订单详细信息（内置已完成/已关闭订单状态机本地短路流控防线）。
    """
    db = knowledge_retriever._repo._db
    from app.repository.youzan_repo import YouzanOrderRepo
    order_repo = YouzanOrderRepo(db)

    try:
        # 1. 尝试本地状态机短路判定（抗有赞网关高频访问限流）
        local_order = await order_repo.get_by_order_no(order_no)
        if local_order and local_order["status"] in ("TRADE_SUCCESS", "TRADE_CLOSED"):
            logger.info("已完成/已关闭订单触发本地状态机短路秒回: order_no=%s", order_no)
            return json.dumps({
                "order_no": order_no,
                "status": local_order["status"],
                "amount_yuan": local_order["amount_fen"] / 100.0,
                "product_titles": local_order["product_titles"],
                "logistics_no": local_order["logistics_no"],
                "logistics_status": local_order["logistics_status"],
                "source": "local_short_circuit"
            }, ensure_ascii=False)

        # 2. 活跃订单则现场拉取有赞最新数据
        from app.service.youzan.client import YouzanClient
        from app.repository.config_repo import ConfigRepo
        yz_client = YouzanClient(config_repo=ConfigRepo(db))

        raw_order = await yz_client.get_order(order_no)
        await yz_client.close()

        if "response" not in raw_order or "trade" not in raw_order["response"]:
            return json.dumps({"order_no": order_no, "available": False, "message": "未找到此订单，请检查有赞订单号是否输入正确"}, ensure_ascii=False)

        trade = raw_order["response"]["trade"]
        status = trade.get("status", "WAIT_BUYER_PAY")
        payment_fen = int(float(trade.get("payment", 0)) * 100)
        buyer_id = trade.get("buyer_id", "") or trade.get("open_id", "")

        # 解析商品拼接串与购买总件数
        order_items = trade.get("orders", [])
        titles_list = []
        total_qty = 0
        for item in order_items:
            title = item.get("title", "商品")
            num = item.get("num", 1)
            titles_list.append(f"{title} x {num}")
            total_qty += num
        product_titles = ", ".join(titles_list)

        created = trade.get("created", "")
        updated = trade.get("update_time", "") or trade.get("created", "")

        # 3. 双轨向右：异步增量保存至 orders 交易物理大宽表
        await order_repo.upsert_order(
            order_no=order_no,
            buyer_id=buyer_id,
            status=status,
            amount_fen=payment_fen,
            logistics_no=local_order["logistics_no"] if local_order else "",
            logistics_status=local_order["logistics_status"] if local_order else "",
            product_titles=product_titles,
            total_quantity=total_qty,
            created_at=created,
            updated_at=updated
        )

        return json.dumps({
            "order_no": order_no,
            "status": status,
            "amount_yuan": payment_fen / 100.0,
            "product_titles": product_titles,
            "receiver_name": trade.get("receiver_name", "买家"),
            "receiver_mobile": trade.get("receiver_mobile", ""),
            "address": f"{trade.get('receiver_state','')}{trade.get('receiver_city','')}{trade.get('receiver_district','')}{trade.get('receiver_address','')}",
            "source": "youzan_live_api"
        }, ensure_ascii=False)

    except Exception as exc:
        logger.error("有赞订单查询失败: order_no=%s err=%s", order_no, exc)
        return json.dumps({"order_no": order_no, "available": False, "message": "订单查询发生系统异常，请稍后再试或联系人工客服"}, ensure_ascii=False)


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

    # 4. 触点三：AI 会话导购推荐埋点（内置 1 小时排他防刷滑动窗口去重）
    if session:
        from app.repository.analytics_repo import AnalyticsRepo
        import datetime
        db = knowledge_retriever._repo._db
        analytics_repo = AnalyticsRepo(db)

        for entry in entries:
            if entry.youzan_item_id:
                try:
                    # 反查 products 本地物理表以获取当前 alias
                    from app.repository.youzan_repo import YouzanProductRepo
                    product_repo = YouzanProductRepo(db)
                    product = await product_repo.get_by_id(int(entry.youzan_item_id))
                    if product:
                        alias = product["alias"]
                        # 1小时滑动窗口排重
                        is_duplicate = await analytics_repo.check_recent_recommend(session.id, alias, hour_limit=1)
                        if not is_duplicate:
                            await analytics_repo.add_event(
                                session_id=session.id,
                                buyer_id=session.user_id,
                                event_type="product_recommend",
                                event_source="ai_bot",
                                ref_id=alias,
                                meta_data=json.dumps({"title": entry.title}, ensure_ascii=False),
                                created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            )
                            logger.info("已成功记录 AI 推荐埋点触点 (1小时防刷校验通过): session=%s, alias=%s", session.id, alias)
                        else:
                            logger.debug("同会话1小时内针对同款商品产生过推荐行为，执行幂等去重跳过写入: alias=%s", alias)
                except Exception as telemetry_exc:
                    logger.warning("AI 推荐埋点记录失败: %s", telemetry_exc)

    results = [{"title": e.title, "content": e.content, "category": e.category} for e in entries]
    return json.dumps({"query": query, "results": results}, ensure_ascii=False)


async def get_logistics_info(knowledge_retriever: KnowledgeRetriever, order_no: str) -> str:
    """
    查询物流配送进度并反写更新 orders 交易物理大宽表。
    """
    db = knowledge_retriever._repo._db
    from app.service.youzan.client import YouzanClient
    from app.repository.config_repo import ConfigRepo

    try:
        yz_client = YouzanClient(config_repo=ConfigRepo(db))
        raw_logistics = await yz_client.get_logistics(order_no)
        await yz_client.close()

        if "response" not in raw_logistics:
            return json.dumps({"order_no": order_no, "available": False, "message": "未查询到物流派送信息，可能商家尚未发货"}, ensure_ascii=False)

        response = raw_logistics["response"]
        express_id = response.get("express_id", "")
        express_name = response.get("express_name", "")
        steps = response.get("transit_step_infos", [])

        step_descs = []
        for step in steps:
            time_str = step.get("status_time", "")
            desc = step.get("status_desc", "")
            step_descs.append(f"[{time_str}] {desc}")

        # 将快递单号与最新轨迹反写更新到 orders 宽表
        from app.repository.youzan_repo import YouzanOrderRepo
        order_repo = YouzanOrderRepo(db)
        local_order = await order_repo.get_by_order_no(order_no)
        if local_order:
            latest_step = step_descs[-1] if step_descs else "暂无轨迹"
            await order_repo.upsert_order(
                order_no=local_order["order_no"],
                buyer_id=local_order["buyer_id"],
                status=local_order["status"],
                amount_fen=local_order["amount_fen"],
                logistics_no=express_id,
                logistics_status=latest_step,
                product_titles=local_order["product_titles"],
                total_quantity=local_order["total_quantity"],
                created_at=local_order["created_at"],
                updated_at=local_order["updated_at"]
            )

        return json.dumps({
            "order_no": order_no,
            "express_name": express_name,
            "express_id": express_id,
            "steps": step_descs[:5],
            "message": "查询成功"
        }, ensure_ascii=False)

    except Exception as exc:
        logger.error("有赞物流查询失败: order_no=%s err=%s", order_no, exc)
        return json.dumps({"order_no": order_no, "available": False, "message": "物流查询发生异常，请稍后再试或联系人工客服获取配送进度"}, ensure_ascii=False)


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


async def dispatch_tool(
    tool_name: str,
    args: dict,
    session: Session | None = None,
    knowledge_retriever: KnowledgeRetriever | None = None,
) -> str:
    """
    根据工具名称分发到对应处理函数。

    参数：
        tool_name: 工具名称
        args: 工具参数字典
        session: 当前会话
        knowledge_retriever: 知识检索器（search_knowledge / get_product_info 必传）
    返回：
        工具执行结果的 JSON 字符串
    """
    match tool_name:
        case "get_order_info":
            if knowledge_retriever is None:
                return json.dumps({"message": "订单查询服务暂不可用"}, ensure_ascii=False)
            return await get_order_info(knowledge_retriever, **args)
        case "get_logistics_info":
            if knowledge_retriever is None:
                return json.dumps({"message": "物流查询服务暂不可用"}, ensure_ascii=False)
            return await get_logistics_info(knowledge_retriever, **args)
        case "get_product_info":
            if knowledge_retriever is None:
                return json.dumps({"message": "商品查询服务暂不可用"}, ensure_ascii=False)
            return await get_product_info(knowledge_retriever, session, **args)
        case "search_knowledge":
            if knowledge_retriever is None:
                return json.dumps({"message": "知识库服务暂不可用"}, ensure_ascii=False)
            return await search_knowledge(knowledge_retriever, **args)
        case "transfer_to_human":
            # 由 ChatService 工具调度循环拦截处理，此处为安全兜底
            return json.dumps({"status": "pending", "message": "正在为您转接人工客服"}, ensure_ascii=False)
        case _:
            return json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False)
