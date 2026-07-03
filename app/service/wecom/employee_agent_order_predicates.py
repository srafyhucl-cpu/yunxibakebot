"""企微员工助手订单问法谓词。"""

from __future__ import annotations

from app.service.wecom.employee_agent_order_keywords import (
    ORDER_FULFILLMENT_RISK_KEYWORDS,
    ORDER_POLICY_KEYWORDS,
    ORDER_REFUND_KEYWORDS,
)


def needs_missing_logistics(query: str) -> bool:
    """判断是否查询无物流订单。"""
    return any(
        word in query
        for word in ("没物流", "无物流", "暂无物流", "还没物流", "没出物流")
    )


def needs_refund(query: str) -> bool:
    """判断是否查询退款/售后订单数据。"""
    return any(word in query for word in ORDER_REFUND_KEYWORDS) and not (
        looks_like_order_policy_query(query)
    )


def needs_fulfillment_risk(query: str) -> bool:
    """判断是否查询履约风险订单。"""
    return any(word in query for word in ORDER_FULFILLMENT_RISK_KEYWORDS)


def looks_like_order_policy_query(query: str) -> bool:
    """判断是否退款规则、话术或政策类知识问法。"""
    return any(word in query for word in ORDER_POLICY_KEYWORDS)


def resolve_sort_by(query: str) -> str:
    """解析订单查询排序口径。"""
    if needs_fulfillment_risk(query):
        return "delivery_time"
    return "amount" if "金额" in query else "latest"
