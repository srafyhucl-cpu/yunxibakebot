"""企微员工助手订单时间范围解析。"""

from __future__ import annotations

import re
from datetime import date, timedelta

from app.service.wecom.employee_agent_order_constants import (
    CHINESE_DAY_NUMBERS,
    MAX_RESULT_LIMIT,
)


def resolve_order_date_range(query: str, today: date) -> tuple[str, str]:
    """把员工口语时间范围转成订单查询日期边界。"""
    recent_days = extract_recent_days(query)
    if recent_days is not None:
        date_from = today - timedelta(days=recent_days - 1)
        return date_from.isoformat(), today.isoformat()
    if any(word in query for word in ("本周", "这周", "本星期", "这个星期")):
        week_start = today - timedelta(days=today.weekday())
        return week_start.isoformat(), today.isoformat()
    if "昨天" in query:
        target_day = today - timedelta(days=1)
        return target_day.isoformat(), target_day.isoformat()
    if any(word in query for word in ("今天", "今日", "晚上")):
        return today.isoformat(), today.isoformat()
    return "", ""


def remove_order_time_expressions(query: str) -> str:
    """移除会污染商品关键词的相对时间表达。"""
    keyword = re.sub(r"(?:最近|近)\s*\d+\s*天", " ", query)
    return re.sub(r"(?:最近|近)\s*[一二三四五六七八九十]\s*天", " ", keyword)


def extract_recent_days(query: str) -> int | None:
    match = re.search(r"(?:最近|近)\s*(\d+)\s*天", query)
    if match:
        return max(1, min(int(match.group(1)), MAX_RESULT_LIMIT))
    chinese_match = re.search(r"(?:最近|近)\s*([一二三四五六七八九十])\s*天", query)
    if chinese_match:
        days = CHINESE_DAY_NUMBERS.get(chinese_match.group(1), 0)
        return max(1, min(days, MAX_RESULT_LIMIT)) if days else None
    if any(word in query for word in ("近一周", "最近一周", "最近7天", "近7天")):
        return 7
    return None
