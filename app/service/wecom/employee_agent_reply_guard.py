"""企微员工助手回复事实保真。"""

from __future__ import annotations

import re

STOCK_VALUE_PATTERN = re.compile(r"库存\s*(\d+)")
DELIVERY_DATE_PATTERN = re.compile(r"约送\s*(20\d{2}-\d{2}-\d{2})")
ORDER_TAIL_PATTERN = re.compile(r"尾号\s*([A-Za-z0-9]+)")
PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")
LONG_IDENTIFIER_PATTERN = re.compile(r"\b[A-Z]?\d{14,}\b")
PRIVATE_FIELD_PATTERN = re.compile(
    r"(buyer|mobile|phone|address|receiver|tid|oid)",
    re.IGNORECASE,
)
PRIVATE_REPLY_TERMS = (
    "手机号",
    "电话",
    "完整订单号",
    "完整地址",
    "收货地址",
    "买家ID",
    "买家 id",
)
ACTION_INSIGHT_REQUIRED_TERMS = ("优先级", "压力")
ACTION_INSIGHT_SOURCE_MARKERS = ("发货压力", "优先级")
PRESSURE_LABEL_PATTERN = re.compile(r"发货压力[:：]\s*(偏高|中等|低)")
RELATIVE_DELIVERY_DATE_TERMS = (
    "今天",
    "明天",
    "后天",
    "昨天",
    "前天",
    "本周",
    "这周",
    "周末",
    "下周",
)
OVERDUE_DELIVERY_SOURCE_MARKER = "已过约送时间"
OVERDUE_DELIVERY_ACCEPTABLE_TERMS = ("已过", "已逾期", "超时")
OVERDUE_DELIVERY_DETOUR_TERMS = ("需在", "前完成", "前安排")
FULFILLMENT_ORDER_LIST_SOURCE_MARKERS = ("按约送时间", "履约风险")
FULFILLMENT_ORDER_LIST_REQUIRED_TERMS = ("尾号", "约送", "物流")
FULFILLMENT_ORDER_LIST_STATUS_TERMS = ("待发货", "待收货")
MISSING_LOGISTICS_SOURCE_MARKERS = ("暂无物流", "无物流")
MISSING_LOGISTICS_REQUIRED_TERM = "物流"
MISSING_LOGISTICS_EXCLUSION_TERMS = (
    "已剔除",
    "不含已关闭",
    "不含退款",
    "剔除已关闭",
    "剔除退款",
)
EMPTY_ORDER_SCOPE_MARKERS = ("没有查到约送日期", "没有查到下单日期")
EMPTY_ORDER_DETOUR_TERMS = (
    "换商品名",
    "时间范围再查",
    "日期需确认",
    "确认日期是否正确",
)
CUSTOMER_REPLY_SOURCE_MARKER = "给客户可复制回复"
CUSTOMER_REPLY_REQUIRED_TERMS = ("客户", "回复")
TOP_PRODUCTS_TIE_SOURCE_MARKERS = ("销量并列", "第一梯队销量并列")
TOP_PRODUCTS_SOURCE_MARKERS = ("按销量粗略排行", "销量排行")
TOP_PRODUCTS_STOCKING_ADVICE_TERMS = ("优先备货",)
TOP_PRODUCTS_TIE_ACCEPTABLE_TERMS = ("并列", "持平")
TOP_PRODUCTS_TIE_FORBIDDEN_TERMS = ("优先备货", "销量第一", "当前爆款")


def preserve_tool_facts(polished_reply: str, deterministic_reply: str) -> str:
    """避免 LLM 润色丢失工具结果里的关键数值。"""
    if not polished_reply.strip():
        return deterministic_reply
    if _misses_stock_values(polished_reply, deterministic_reply):
        return deterministic_reply
    if _misses_pressure_label(polished_reply, deterministic_reply):
        return deterministic_reply
    if _misses_action_insight_markers(polished_reply, deterministic_reply):
        return deterministic_reply
    if _introduces_relative_delivery_date(polished_reply, deterministic_reply):
        return deterministic_reply
    if _distorts_overdue_delivery_marker(polished_reply, deterministic_reply):
        return deterministic_reply
    if _compresses_fulfillment_order_list(polished_reply, deterministic_reply):
        return deterministic_reply
    if _misses_missing_logistics_marker(polished_reply, deterministic_reply):
        return deterministic_reply
    if _distorts_missing_logistics_closed_refund_scope(
        polished_reply,
        deterministic_reply,
    ):
        return deterministic_reply
    if _introduces_empty_order_detour(polished_reply, deterministic_reply):
        return deterministic_reply
    if _misses_customer_reply(polished_reply, deterministic_reply):
        return deterministic_reply
    if _distorts_top_products_tie(polished_reply, deterministic_reply):
        return deterministic_reply
    if _introduces_top_products_stocking_advice(polished_reply, deterministic_reply):
        return deterministic_reply
    if _introduces_private_markers(polished_reply, deterministic_reply):
        return deterministic_reply
    return polished_reply


def _misses_stock_values(polished_reply: str, deterministic_reply: str) -> bool:
    stock_values = set(STOCK_VALUE_PATTERN.findall(deterministic_reply))
    return bool(stock_values) and not stock_values <= set(
        STOCK_VALUE_PATTERN.findall(polished_reply)
        or re.findall(r"\d+", polished_reply)
    )


def _introduces_private_markers(
    polished_reply: str,
    deterministic_reply: str,
) -> bool:
    for term in PRIVATE_REPLY_TERMS:
        if term in polished_reply and term not in deterministic_reply:
            return True
    for pattern in (PHONE_PATTERN, LONG_IDENTIFIER_PATTERN, PRIVATE_FIELD_PATTERN):
        if pattern.search(polished_reply) and not pattern.search(deterministic_reply):
            return True
    return False


def _misses_pressure_label(polished_reply: str, deterministic_reply: str) -> bool:
    match = PRESSURE_LABEL_PATTERN.search(deterministic_reply)
    if not match:
        return False
    expected_label = match.group(1)
    return "压力" not in polished_reply or expected_label not in polished_reply


def _misses_action_insight_markers(
    polished_reply: str,
    deterministic_reply: str,
) -> bool:
    has_action_insight = all(
        marker in deterministic_reply for marker in ACTION_INSIGHT_SOURCE_MARKERS
    )
    if not has_action_insight:
        return False
    return any(term not in polished_reply for term in ACTION_INSIGHT_REQUIRED_TERMS)


def _introduces_relative_delivery_date(
    polished_reply: str,
    deterministic_reply: str,
) -> bool:
    delivery_dates = set(DELIVERY_DATE_PATTERN.findall(deterministic_reply))
    if not delivery_dates:
        return False
    return any(
        term in polished_reply and term not in deterministic_reply
        for term in RELATIVE_DELIVERY_DATE_TERMS
    )


def _distorts_overdue_delivery_marker(
    polished_reply: str,
    deterministic_reply: str,
) -> bool:
    if OVERDUE_DELIVERY_SOURCE_MARKER not in deterministic_reply:
        return False
    keeps_overdue_marker = any(
        term in polished_reply for term in OVERDUE_DELIVERY_ACCEPTABLE_TERMS
    )
    if not keeps_overdue_marker:
        return True
    return any(term in polished_reply for term in OVERDUE_DELIVERY_DETOUR_TERMS)


def _compresses_fulfillment_order_list(
    polished_reply: str,
    deterministic_reply: str,
) -> bool:
    if not _has_fulfillment_order_list(deterministic_reply):
        return False
    if any(
        term not in polished_reply for term in FULFILLMENT_ORDER_LIST_REQUIRED_TERMS
    ):
        return True
    if not any(term in polished_reply for term in FULFILLMENT_ORDER_LIST_STATUS_TERMS):
        return True
    source_tail_count = len(ORDER_TAIL_PATTERN.findall(deterministic_reply))
    polished_tail_count = len(ORDER_TAIL_PATTERN.findall(polished_reply))
    return polished_tail_count < source_tail_count


def _has_fulfillment_order_list(deterministic_reply: str) -> bool:
    has_list_marker = any(
        marker in deterministic_reply
        for marker in FULFILLMENT_ORDER_LIST_SOURCE_MARKERS
    )
    if not has_list_marker:
        return False
    return len(ORDER_TAIL_PATTERN.findall(deterministic_reply)) > 1


def _misses_missing_logistics_marker(
    polished_reply: str,
    deterministic_reply: str,
) -> bool:
    has_missing_logistics = any(
        marker in deterministic_reply for marker in MISSING_LOGISTICS_SOURCE_MARKERS
    )
    if not has_missing_logistics:
        return False
    return MISSING_LOGISTICS_REQUIRED_TERM not in polished_reply


def _distorts_missing_logistics_closed_refund_scope(
    polished_reply: str,
    deterministic_reply: str,
) -> bool:
    has_missing_logistics = any(
        marker in deterministic_reply for marker in MISSING_LOGISTICS_SOURCE_MARKERS
    )
    if not has_missing_logistics:
        return False
    introduces_exclusion = any(
        term in polished_reply for term in MISSING_LOGISTICS_EXCLUSION_TERMS
    )
    if not introduces_exclusion:
        return False
    return not any(
        term in deterministic_reply for term in MISSING_LOGISTICS_EXCLUSION_TERMS
    )


def _introduces_empty_order_detour(
    polished_reply: str,
    deterministic_reply: str,
) -> bool:
    has_specific_empty_scope = any(
        marker in deterministic_reply for marker in EMPTY_ORDER_SCOPE_MARKERS
    )
    if not has_specific_empty_scope:
        return False
    return any(term in polished_reply for term in EMPTY_ORDER_DETOUR_TERMS)


def _misses_customer_reply(polished_reply: str, deterministic_reply: str) -> bool:
    if CUSTOMER_REPLY_SOURCE_MARKER not in deterministic_reply:
        return False
    return any(term not in polished_reply for term in CUSTOMER_REPLY_REQUIRED_TERMS)


def _distorts_top_products_tie(
    polished_reply: str,
    deterministic_reply: str,
) -> bool:
    has_top_products_tie = any(
        marker in deterministic_reply for marker in TOP_PRODUCTS_TIE_SOURCE_MARKERS
    )
    if not has_top_products_tie:
        return False
    if not any(term in polished_reply for term in TOP_PRODUCTS_TIE_ACCEPTABLE_TERMS):
        return True
    return any(term in polished_reply for term in TOP_PRODUCTS_TIE_FORBIDDEN_TERMS)


def _introduces_top_products_stocking_advice(
    polished_reply: str,
    deterministic_reply: str,
) -> bool:
    has_top_products_result = any(
        marker in deterministic_reply for marker in TOP_PRODUCTS_SOURCE_MARKERS
    )
    if not has_top_products_result:
        return False
    return any(
        term in polished_reply and term not in deterministic_reply
        for term in TOP_PRODUCTS_STOCKING_ADVICE_TERMS
    )
