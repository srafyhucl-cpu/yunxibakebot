"""企微员工助手订单查询计划解析。"""

from __future__ import annotations

import re
from datetime import date

from app.models.employee_agent import AnswerStyle, OrderQueryKind, OrderQueryPlan
from app.service.wecom.employee_agent_order_date import (
    remove_order_time_expressions,
    resolve_order_date_range,
)
from app.service.wecom.employee_agent_order_constants import (
    DEFAULT_RESULT_LIMIT,
    MAX_RESULT_LIMIT,
    ORDER_NO_PATTERN,
    ORDER_PENDING_STATUSES,
    ORDER_POLICY_KEYWORDS,
    ORDER_QUERY_KEYWORDS,
    ORDER_QUERY_PUNCTUATION_PATTERN,
    ORDER_QUERY_STOP_WORDS,
    ORDER_REFUND_KEYWORDS,
    ORDER_REVENUE_KEYWORDS,
    ORDER_STATUS_KEYWORDS,
)


def has_exact_order_no(query: str) -> bool:
    return bool(ORDER_NO_PATTERN.search(query))


def build_order_query_plan(
    query: str,
    today: date,
    kind: OrderQueryKind,
) -> OrderQueryPlan:
    date_from, date_to = resolve_order_date_range(query, today)
    return OrderQueryPlan(
        kind=kind,
        date_from=date_from,
        date_to=date_to,
        statuses=_resolve_order_statuses(query),
        keyword=_extract_order_keyword(query),
        needs_missing_logistics=_needs_missing_logistics(query),
        needs_refund=_needs_refund(query),
        aggregate_by="product" if kind == OrderQueryKind.TOP_PRODUCTS else "",
        sort_by="amount" if "金额" in query else "latest",
        limit=_extract_limit(query),
    )


def resolve_order_kind(query: str) -> OrderQueryKind:
    if any(word in query for word in ("卖得最多", "卖最多", "销量", "卖得多", "卖爆")):
        return OrderQueryKind.TOP_PRODUCTS
    if any(word in query for word in ORDER_REVENUE_KEYWORDS):
        return OrderQueryKind.SUMMARY
    if _needs_refund(query):
        return OrderQueryKind.SUMMARY
    if any(word in query for word in ("多少", "几单", "一共", "统计", "总共", "单量")):
        return OrderQueryKind.SUMMARY
    if any(word in query for word in ("详情", "具体", "订单号")):
        return OrderQueryKind.DETAIL
    return OrderQueryKind.LIST


def answer_style_for_order_kind(kind: OrderQueryKind) -> AnswerStyle:
    if kind == OrderQueryKind.LIST:
        return AnswerStyle.LIST
    if kind == OrderQueryKind.DETAIL:
        return AnswerStyle.DETAIL
    return AnswerStyle.SUMMARY


def extract_limit_from_value(value: object) -> int:
    """从 LLM 计划值中提取安全 limit。"""
    if isinstance(value, int):
        return max(1, min(value, MAX_RESULT_LIMIT))
    return _extract_limit(str(value or ""))


def looks_like_order_query(query: str) -> bool:
    if looks_like_order_policy_query(query):
        return False
    return any(word in query for word in ORDER_QUERY_KEYWORDS)


def looks_like_inventory_query(query: str) -> bool:
    return any(word in query for word in ("库存", "还够", "够吗", "还有吗"))


def looks_like_ops_query(capability_names: set[str]) -> bool:
    return bool(capability_names & {"ops_summary", "handoff_pending"})


def looks_like_order_policy_query(query: str) -> bool:
    return any(word in query for word in ORDER_POLICY_KEYWORDS)


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
    keyword = remove_order_time_expressions(query.strip())
    for stop_word in sorted(ORDER_QUERY_STOP_WORDS, key=len, reverse=True):
        keyword = keyword.replace(stop_word, " ")
    keyword = re.sub(r"E\d{12,}", " ", keyword, flags=re.IGNORECASE)
    keyword = ORDER_QUERY_PUNCTUATION_PATTERN.sub(" ", keyword)
    return " ".join(keyword.split())


def _needs_missing_logistics(query: str) -> bool:
    return any(
        word in query
        for word in ("没物流", "无物流", "暂无物流", "还没物流", "没出物流")
    )


def _needs_refund(query: str) -> bool:
    return any(word in query for word in ORDER_REFUND_KEYWORDS) and not (
        looks_like_order_policy_query(query)
    )


def _extract_limit(query: str) -> int:
    match = re.search(r"(\d+)\s*(?:条|个|单)", query)
    if not match:
        return DEFAULT_RESULT_LIMIT
    return max(1, min(int(match.group(1)), MAX_RESULT_LIMIT))
