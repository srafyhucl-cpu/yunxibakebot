"""企微员工助手订单规则计划。"""

from __future__ import annotations

import re
from datetime import date, timedelta

from app.models.employee_agent import (
    AgentIntent,
    AgentPlan,
    AnswerStyle,
    OrderQueryKind,
    OrderQueryPlan,
)
from app.service.wecom.employee_agent_capabilities import AgentCapabilityCard

DEFAULT_RESULT_LIMIT = 5
MAX_RESULT_LIMIT = 10
ORDER_NO_PATTERN = re.compile(r"\bE\d{12,}\b", re.IGNORECASE)
ORDER_PENDING_STATUSES = ("WAIT_SELLER_SEND_GOODS", "WAIT_BUYER_CONFIRM_GOODS")
ORDER_STATUS_KEYWORDS = {
    "WAIT_SELLER_SEND_GOODS": ("待发货", "没发货", "未发货", "还没发", "发货"),
    "WAIT_BUYER_CONFIRM_GOODS": ("待收货", "已发货", "配送中"),
    "TRADE_SUCCESS": ("已完成", "交易成功", "完成"),
    "TRADE_CLOSED": ("已关闭", "关闭", "取消"),
    "WAIT_BUYER_PAY": ("待付款", "未付款"),
}
ORDER_QUERY_STOP_WORDS = (
    "今天",
    "今日",
    "昨天",
    "最近",
    "订单",
    "下单",
    "有哪些",
    "还有",
    "多少",
    "几单",
    "卖了",
    "卖得最多",
    "未发货",
    "没发货",
    "待发货",
    "待处理",
    "库存",
    "还够",
    "够吗",
    "还有吗",
    "物流",
    "的",
    "吗",
)
ORDER_QUERY_PUNCTUATION_PATTERN = re.compile(r"[，。？！、；：,.?!;:]")


def build_rule_plan(
    query: str,
    capabilities: list[AgentCapabilityCard],
    today: date,
) -> AgentPlan:
    """按确定性规则生成员工助手计划。"""
    if not query.strip():
        return AgentPlan(intent=AgentIntent.UNSUPPORTED)
    if ORDER_NO_PATTERN.search(query):
        return _build_exact_order_plan(query, today)
    capability_names = {card.name for card in capabilities}
    has_order = "order_dynamic_query" in capability_names or _looks_like_order_query(
        query
    )
    if (
        has_order
        and "product_lookup" in capability_names
        and _looks_like_inventory_query(query)
    ):
        return _build_order_agent_plan(
            query,
            today,
            intent=AgentIntent.MULTI_TOOL,
            tools=("order_dynamic_query", "product_lookup"),
            answer_style=AnswerStyle.SUMMARY,
        )
    if has_order:
        return _build_order_agent_plan(
            query,
            today,
            intent=AgentIntent.ORDER_QUERY,
            tools=("order_dynamic_query",),
        )
    return _build_non_order_agent_plan(query, capability_names, has_order)


def extract_limit_from_value(value: object) -> int:
    """从 LLM 计划值中提取安全 limit。"""
    if isinstance(value, int):
        return max(1, min(value, MAX_RESULT_LIMIT))
    return _extract_limit(str(value or ""))


def _build_exact_order_plan(query: str, today: date) -> AgentPlan:
    return AgentPlan(
        intent=AgentIntent.ORDER_QUERY,
        tools=("order_dynamic_query",),
        query_plan=_order_plan_from_query(query, today, OrderQueryKind.DETAIL),
        answer_style=AnswerStyle.DETAIL,
    )


def _build_non_order_agent_plan(
    query: str,
    capability_names: set[str],
    has_order: bool,
) -> AgentPlan:
    if "product_lookup" in capability_names and not has_order:
        return AgentPlan(
            intent=AgentIntent.PRODUCT_QUERY,
            tools=("product_lookup",),
            answer_style=AnswerStyle.SUMMARY,
        )
    if _looks_like_ops_query(query, capability_names):
        return AgentPlan(
            intent=AgentIntent.OPS_QUERY,
            tools=tuple(sorted(capability_names)) or ("ops_summary",),
            answer_style=AnswerStyle.SUMMARY,
        )
    if "knowledge_answer" in capability_names:
        return AgentPlan(
            intent=AgentIntent.KNOWLEDGE_ANSWER,
            tools=("knowledge_answer",),
            answer_style=AnswerStyle.SUMMARY,
        )
    return AgentPlan(intent=AgentIntent.UNSUPPORTED)


def _build_order_agent_plan(
    query: str,
    today: date,
    *,
    intent: AgentIntent,
    tools: tuple[str, ...],
    answer_style: AnswerStyle | None = None,
) -> AgentPlan:
    order_kind = _resolve_order_kind(query)
    return AgentPlan(
        intent=intent,
        tools=tools,
        query_plan=_order_plan_from_query(query, today, order_kind),
        answer_style=answer_style or _answer_style_for_order_kind(order_kind),
    )


def _order_plan_from_query(
    query: str,
    today: date,
    kind: OrderQueryKind,
) -> OrderQueryPlan:
    date_from, date_to = _resolve_date_range(query, today)
    statuses = _resolve_order_statuses(query)
    return OrderQueryPlan(
        kind=kind,
        date_from=date_from,
        date_to=date_to,
        statuses=statuses,
        keyword=_extract_order_keyword(query),
        needs_missing_logistics=_needs_missing_logistics(query),
        aggregate_by="product" if kind == OrderQueryKind.TOP_PRODUCTS else "",
        sort_by="amount" if "金额" in query else "latest",
        limit=_extract_limit(query),
    )


def _resolve_order_kind(query: str) -> OrderQueryKind:
    if any(word in query for word in ("卖得最多", "卖最多", "销量", "卖得多")):
        return OrderQueryKind.TOP_PRODUCTS
    if any(word in query for word in ("多少", "几单", "一共", "统计", "总共")):
        return OrderQueryKind.SUMMARY
    if any(word in query for word in ("详情", "具体", "订单号")):
        return OrderQueryKind.DETAIL
    return OrderQueryKind.LIST


def _answer_style_for_order_kind(kind: OrderQueryKind) -> AnswerStyle:
    if kind == OrderQueryKind.LIST:
        return AnswerStyle.LIST
    if kind == OrderQueryKind.DETAIL:
        return AnswerStyle.DETAIL
    return AnswerStyle.SUMMARY


def _resolve_date_range(query: str, today: date) -> tuple[str, str]:
    if "昨天" in query:
        target_day = today - timedelta(days=1)
        return target_day.isoformat(), target_day.isoformat()
    if any(word in query for word in ("今天", "今日", "晚上")):
        return today.isoformat(), today.isoformat()
    return "", ""


def _resolve_order_statuses(query: str) -> tuple[str, ...]:
    if "待处理" in query:
        return ORDER_PENDING_STATUSES
    statuses = [
        status
        for status, keywords in ORDER_STATUS_KEYWORDS.items()
        if any(keyword in query for keyword in keywords)
    ]
    return tuple(dict.fromkeys(statuses))


def _extract_order_keyword(query: str) -> str:
    keyword = query.strip()
    for stop_word in ORDER_QUERY_STOP_WORDS:
        keyword = keyword.replace(stop_word, " ")
    keyword = re.sub(r"E\d{12,}", " ", keyword, flags=re.IGNORECASE)
    keyword = ORDER_QUERY_PUNCTUATION_PATTERN.sub(" ", keyword)
    return " ".join(keyword.split())


def _needs_missing_logistics(query: str) -> bool:
    return any(word in query for word in ("没物流", "无物流", "暂无物流", "还没物流"))


def _extract_limit(query: str) -> int:
    match = re.search(r"(\d+)\s*(?:条|个|单)", query)
    if not match:
        return DEFAULT_RESULT_LIMIT
    return max(1, min(int(match.group(1)), MAX_RESULT_LIMIT))


def _looks_like_order_query(query: str) -> bool:
    return any(
        word in query
        for word in ("订单", "下单", "发货", "物流", "几单", "待处理", "卖得多", "销量")
    )


def _looks_like_inventory_query(query: str) -> bool:
    return any(word in query for word in ("库存", "还够", "够吗", "还有吗"))


def _looks_like_ops_query(query: str, capability_names: set[str]) -> bool:
    return bool(capability_names & {"ops_summary", "handoff_pending"})
