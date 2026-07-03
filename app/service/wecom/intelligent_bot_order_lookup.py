"""企微智能机器人订单查询编排。"""

from __future__ import annotations

import json
import re
from typing import Any

from app.logger import setup_logger
from app.models.employee_agent import OrderQueryKind, OrderQueryPlan, ToolResult
from app.service.llm.function_tool_order import get_logistics_info, get_order_info
from app.service.wecom.intelligent_bot_order_action_items import (
    answer_order_action_items,
)
from app.service.wecom.intelligent_bot_order_format import (
    build_order_list_tool_result,
    build_order_summary_tool_result,
    build_top_products_tool_result,
    youzan_order_detail_line,
    youzan_order_line,
)
from app.service.wecom.intelligent_bot_tool_response import ok_response

logger = setup_logger()

ORDER_LOOKUP_TOOL = "order_lookup"
YOUZAN_ORDER_NO_PATTERN = re.compile(r"\bE\d{12,}\b", re.IGNORECASE)
LOGISTICS_KEYWORDS = ("物流", "配送", "发货", "送到", "快递", "轨迹")
RECENT_ORDER_KEYWORDS = ("最近", "最新", "近几单", "这几单")
ORDER_QUERY_STOP_WORDS = (
    "帮我",
    "查一下",
    "查询",
    "查",
    "订单号",
    "订单",
    "下单记录",
    "下单",
)


class WeComOrderLookupService:
    """面向员工企微问答的订单查询服务。"""

    def __init__(
        self,
        *,
        order_service: Any = None,
        youzan_order_repo: Any = None,
        knowledge_retriever: Any = None,
        youzan_client: Any = None,
    ) -> None:
        self._order_service = order_service
        self._youzan_order_repo = youzan_order_repo
        self._knowledge_retriever = knowledge_retriever
        self._youzan_client = youzan_client

    async def lookup_orders(self, query: str, limit: int) -> dict[str, Any]:
        """执行订单查询并返回企微工具响应。"""
        order_no = _extract_youzan_order_no(query)
        if order_no:
            return await self._lookup_exact_youzan_order(query, order_no)
        search_keyword = _normalize_search_keyword(query)
        youzan_orders = await self._search_youzan_orders(query, search_keyword, limit)
        if youzan_orders:
            return _build_youzan_search_response(query, youzan_orders)
        return await self._lookup_platform_orders(query, search_keyword, limit)

    async def answer_agent_query(
        self,
        query: str,
        plan: OrderQueryPlan,
    ) -> ToolResult:
        """按员工 Agent 查询计划返回订单工具结果。"""
        if self._youzan_order_repo is None:
            return ToolResult(
                ok=False,
                summary="订单数据源暂不可用。",
                next_action="请到后台订单页人工核对。",
            )
        if plan.kind == OrderQueryKind.TOP_PRODUCTS:
            top_products = await self._youzan_order_repo.list_top_products(plan)
            return build_top_products_tool_result(query, top_products)
        if plan.kind == OrderQueryKind.ACTION_ITEMS:
            return await answer_order_action_items(
                self._youzan_order_repo,
                query,
                plan,
            )
        summary = await self._youzan_order_repo.summarize_orders(plan)
        orders = await self._youzan_order_repo.query_orders(plan)
        if plan.kind == OrderQueryKind.SUMMARY:
            return build_order_summary_tool_result(query, summary, orders)
        return build_order_list_tool_result(query, summary, orders)

    async def _lookup_exact_youzan_order(
        self, query: str, order_no: str
    ) -> dict[str, Any]:
        if self._knowledge_retriever is None:
            return await self._lookup_exact_order_from_repo(query, order_no)
        raw_result = await self._call_youzan_order_tool(query, order_no)
        parsed_result = _parse_tool_json(raw_result)
        compact_order = _compact_live_order(parsed_result, order_no)
        orders_text = youzan_order_detail_line(compact_order)
        return ok_response(
            ORDER_LOOKUP_TOOL,
            query,
            "已按有赞交易号查询订单。",
            ordersText=orders_text,
            orders=[compact_order],
            nextAction="如需改状态、退款或补发，请进入有赞或后台人工处理。",
        )

    async def _call_youzan_order_tool(self, query: str, order_no: str) -> str:
        if _is_logistics_query(query):
            return await get_logistics_info(
                self._knowledge_retriever,
                order_no,
                self._youzan_client,
            )
        return await get_order_info(
            self._knowledge_retriever,
            order_no,
            self._youzan_client,
        )

    async def _lookup_exact_order_from_repo(
        self, query: str, order_no: str
    ) -> dict[str, Any]:
        if self._youzan_order_repo is None:
            return _empty_order_response(query)
        order = await self._youzan_order_repo.get_by_order_no(order_no)
        if not order:
            return _empty_order_response(query)
        return _build_youzan_search_response(query, [order])

    async def _search_youzan_orders(
        self, query: str, search_keyword: str, limit: int
    ) -> list[dict[str, Any]]:
        if self._youzan_order_repo is None:
            return []
        if _is_recent_order_query(query):
            return await self._youzan_order_repo.list_recent_orders(limit=limit)
        return await self._youzan_order_repo.search_orders(search_keyword, limit=limit)

    async def _lookup_platform_orders(
        self, query: str, search_keyword: str, limit: int
    ) -> dict[str, Any]:
        if self._order_service is None:
            return _empty_order_response(query)
        result = await self._order_service.list_admin_orders(
            page=1,
            keyword=search_keyword,
        )
        orders = [
            _compact_platform_order(item) for item in result.get("items", [])[:limit]
        ]
        total = int(result.get("total", len(orders)) or 0)
        orders_text = "\n".join(_platform_order_line(item) for item in orders)
        return ok_response(
            ORDER_LOOKUP_TOOL,
            query,
            f"找到 {total} 个匹配订单，当前返回 {len(orders)} 个。",
            ordersText=orders_text or "未找到匹配订单",
            orders=orders,
            nextAction="如需改状态或处理退款，请进入后台订单页操作。",
        )


def _extract_youzan_order_no(query: str) -> str:
    match = YOUZAN_ORDER_NO_PATTERN.search(query)
    return match.group(0).upper() if match else ""


def _is_logistics_query(query: str) -> bool:
    return any(keyword in query for keyword in LOGISTICS_KEYWORDS)


def _is_recent_order_query(query: str) -> bool:
    return any(keyword in query for keyword in RECENT_ORDER_KEYWORDS)


def _normalize_search_keyword(query: str) -> str:
    keyword = query.strip()
    for stop_word in ORDER_QUERY_STOP_WORDS:
        keyword = keyword.replace(stop_word, " ")
    compact_keyword = " ".join(keyword.split())
    return compact_keyword or query.strip()


def _parse_tool_json(raw_result: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_result)
    except json.JSONDecodeError:
        logger.warning("企微订单查询工具返回非 JSON，已降级展示")
        return {"message": raw_result}
    return parsed if isinstance(parsed, dict) else {"message": raw_result}


def _build_youzan_search_response(
    query: str, orders: list[dict[str, Any]]
) -> dict[str, Any]:
    compact_orders = [_compact_youzan_order(order) for order in orders]
    orders_text = "\n".join(youzan_order_line(order) for order in compact_orders)
    return ok_response(
        ORDER_LOOKUP_TOOL,
        query,
        f"找到 {len(compact_orders)} 个有赞匹配订单。",
        ordersText=orders_text or "未找到匹配订单",
        orders=compact_orders,
        nextAction="如需实时刷新详情或物流，请带有赞交易号继续追问。",
    )


def _empty_order_response(query: str) -> dict[str, Any]:
    return ok_response(
        ORDER_LOOKUP_TOOL,
        query,
        "未找到匹配订单。",
        ordersText="未找到匹配订单",
        orders=[],
        nextAction="请确认有赞交易号、手机号、客户名或商品关键词是否准确。",
    )


def _compact_live_order(order: dict[str, Any], order_no: str) -> dict[str, Any]:
    return {
        "source": str(order.get("source", "youzan_live")),
        "orderNo": str(order.get("order_no") or order_no),
        "status": str(order.get("status") or order.get("status_str") or ""),
        "amountFen": _yuan_to_fen(order.get("amount_yuan")),
        "productTitles": str(order.get("product_titles", "")),
        "payTime": str(order.get("pay_time", "")),
        "deliveryArea": _join_area(
            order.get("delivery_province"),
            order.get("delivery_city"),
            order.get("delivery_district"),
        ),
        "deliveryTime": str(order.get("delivery_time", "")),
        "logisticsNo": str(order.get("logistics_no") or order.get("express_id") or ""),
        "logisticsStatus": _latest_logistics_status(order),
        "message": str(order.get("message", "")),
    }


def _compact_youzan_order(order: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "youzan_orders",
        "orderNo": str(order.get("order_no", "")),
        "status": str(order.get("status", "")),
        "amountFen": int(order.get("amount_fen", 0) or 0),
        "productTitles": str(order.get("product_titles", "")),
        "totalQuantity": int(order.get("total_quantity", 0) or 0),
        "payTime": str(order.get("pay_time", "")),
        "deliveryArea": _join_area(
            order.get("delivery_province"),
            order.get("delivery_city"),
            order.get("delivery_district"),
        ),
        "deliveryTime": str(order.get("delivery_time", "")),
        "logisticsNo": str(order.get("logistics_no", "")),
        "logisticsStatus": str(order.get("logistics_status", "")),
        "refundState": int(order.get("refund_state", 0) or 0),
    }


def _compact_platform_order(order: dict[str, Any]) -> dict[str, Any]:
    from app.service.wecom.intelligent_bot_tool_format import compact_order

    compact_order = compact_order(order)
    compact_order["source"] = "platform_orders"
    return compact_order


def _platform_order_line(order: dict[str, Any]) -> str:
    from app.service.wecom.intelligent_bot_tool_format import order_line

    return order_line(order)


def _join_area(*parts: object) -> str:
    return "".join(str(part) for part in parts if part)


def _yuan_to_fen(value: Any) -> int:
    try:
        return int(round(float(value or 0) * 100))
    except (TypeError, ValueError):
        return 0


def _latest_logistics_status(order: dict[str, Any]) -> str:
    steps = order.get("steps")
    if isinstance(steps, list) and steps:
        return str(steps[0])
    return str(order.get("logistics_status", ""))
