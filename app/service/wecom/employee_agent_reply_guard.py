"""企微员工助手回复事实保真。"""

from __future__ import annotations

import re

STOCK_VALUE_PATTERN = re.compile(r"库存\s*(\d+)")
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
MISSING_LOGISTICS_SOURCE_MARKERS = ("暂无物流", "无物流")
MISSING_LOGISTICS_REQUIRED_TERM = "物流"


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
    if _misses_missing_logistics_marker(polished_reply, deterministic_reply):
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
