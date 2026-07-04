"""企微员工助手订单列表结构保真。"""

from __future__ import annotations

import re

ORDER_TAIL_PATTERN = re.compile(r"尾号\s*([A-Za-z0-9]+)")
ORDER_AMOUNT_PATTERN = re.compile(r"\d+(?:\.\d{1,2})?\s*元")
ORDER_LIST_SOURCE_MARKERS = ("按最新订单展示", "按约送时间")
ORDER_LIST_STATUS_TERMS = ("待付款", "待发货", "待收货", "交易成功", "已关闭", "已付款")
ORDER_LIST_LOGISTICS_TERMS = ("暂无物流", "无物流", "有物流单号")


def compresses_employee_order_list(
    polished_reply: str,
    deterministic_reply: str,
) -> bool:
    source_tail_count = _employee_order_list_tail_count(deterministic_reply)
    if source_tail_count <= 1:
        return False
    if len(ORDER_TAIL_PATTERN.findall(polished_reply)) < source_tail_count:
        return True
    if _misses_per_order_terms(
        polished_reply,
        deterministic_reply,
        ORDER_LIST_STATUS_TERMS,
        source_tail_count,
    ):
        return True
    if (
        len(ORDER_AMOUNT_PATTERN.findall(deterministic_reply)) >= (source_tail_count)
        and len(ORDER_AMOUNT_PATTERN.findall(polished_reply)) < source_tail_count
    ):
        return True
    return _misses_per_order_terms(
        polished_reply,
        deterministic_reply,
        ORDER_LIST_LOGISTICS_TERMS,
        source_tail_count,
    )


def _employee_order_list_tail_count(deterministic_reply: str) -> int:
    if not any(marker in deterministic_reply for marker in ORDER_LIST_SOURCE_MARKERS):
        return 0
    return len(ORDER_TAIL_PATTERN.findall(deterministic_reply))


def _misses_per_order_terms(
    polished_reply: str,
    deterministic_reply: str,
    terms: tuple[str, ...],
    source_tail_count: int,
) -> bool:
    if _source_term_count(deterministic_reply, terms) < source_tail_count:
        return False
    return _source_term_count(polished_reply, terms) < source_tail_count


def _source_term_count(source_text: str, terms: tuple[str, ...]) -> int:
    term_pattern = "|".join(
        re.escape(term) for term in sorted(terms, key=len, reverse=True)
    )
    return len(re.findall(term_pattern, source_text))
