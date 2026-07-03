"""企微员工助手回复事实保真。"""

from __future__ import annotations

import re

STOCK_VALUE_PATTERN = re.compile(r"库存\s*(\d+)")


def preserve_tool_facts(polished_reply: str, deterministic_reply: str) -> str:
    """避免 LLM 润色丢失工具结果里的关键数值。"""
    if not polished_reply.strip():
        return deterministic_reply
    if _misses_stock_values(polished_reply, deterministic_reply):
        return deterministic_reply
    return polished_reply


def _misses_stock_values(polished_reply: str, deterministic_reply: str) -> bool:
    stock_values = set(STOCK_VALUE_PATTERN.findall(deterministic_reply))
    return bool(stock_values) and not stock_values <= set(
        STOCK_VALUE_PATTERN.findall(polished_reply)
        or re.findall(r"\d+", polished_reply)
    )
