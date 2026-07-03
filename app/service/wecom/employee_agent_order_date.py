"""企微员工助手订单时间范围解析。"""

from __future__ import annotations

import re
from datetime import date, timedelta

from app.service.wecom.employee_agent_order_constants import (
    CHINESE_DAY_NUMBERS,
    MAX_RESULT_LIMIT,
)

ORDER_DATE_FIELD = "order_time"
DELIVERY_DATE_FIELD = "delivery_time"
WEEKEND_START_OFFSET = 5
WEEKEND_END_OFFSET = 6
MONTH_DAY_PATTERN = re.compile(r"(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*(?:日|号)?")
SLASH_DATE_PATTERN = re.compile(r"(?<!\d)(\d{1,2})\s*[/-]\s*(\d{1,2})(?!\d)")


def resolve_order_date_range(query: str, today: date) -> tuple[str, str]:
    """把员工口语时间范围转成订单查询日期边界。"""
    recent_days = extract_recent_days(query)
    if recent_days is not None:
        date_from = today - timedelta(days=recent_days - 1)
        return date_from.isoformat(), today.isoformat()
    if any(word in query for word in ("本周", "这周", "本星期", "这个星期")):
        week_start = today - timedelta(days=today.weekday())
        return week_start.isoformat(), today.isoformat()
    if any(word in query for word in ("本周末", "这个周末", "周末")):
        return _resolve_weekend_range(today)
    if "后天" in query:
        target_day = today + timedelta(days=2)
        return target_day.isoformat(), target_day.isoformat()
    if "明天" in query:
        target_day = today + timedelta(days=1)
        return target_day.isoformat(), target_day.isoformat()
    if "昨天" in query:
        target_day = today - timedelta(days=1)
        return target_day.isoformat(), target_day.isoformat()
    if any(
        word in query
        for word in ("今天", "今日", "上午", "中午", "下午", "傍晚", "晚上", "夜里")
    ):
        return today.isoformat(), today.isoformat()
    specific_day = _extract_specific_month_day(query, today)
    if specific_day is not None:
        return specific_day.isoformat(), specific_day.isoformat()
    return "", ""


def remove_order_time_expressions(query: str) -> str:
    """移除会污染商品关键词的相对时间表达。"""
    keyword = re.sub(r"(?:最近|近)\s*\d+\s*天", " ", query)
    keyword = re.sub(r"(?:最近|近)\s*[一二三四五六七八九十]\s*天", " ", keyword)
    keyword = MONTH_DAY_PATTERN.sub(" ", keyword)
    return SLASH_DATE_PATTERN.sub(" ", keyword)


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


def resolve_order_date_field(query: str) -> str:
    """解析订单日期过滤口径。"""
    if any(
        word in query
        for word in (
            "约送",
            "配送",
            "送达",
            "送到",
            "履约",
            "发货压力",
            "快超时",
            "要超时",
            "来不及",
            "待处理",
            "上午",
            "中午",
            "下午",
            "傍晚",
            "晚上",
            "夜里",
        )
    ):
        return DELIVERY_DATE_FIELD
    return ORDER_DATE_FIELD


def _resolve_weekend_range(today: date) -> tuple[str, str]:
    week_start = today - timedelta(days=today.weekday())
    weekend_start = week_start + timedelta(days=WEEKEND_START_OFFSET)
    weekend_end = week_start + timedelta(days=WEEKEND_END_OFFSET)
    if today > weekend_end:
        weekend_start += timedelta(days=7)
        weekend_end += timedelta(days=7)
    return weekend_start.isoformat(), weekend_end.isoformat()


def _extract_specific_month_day(query: str, today: date) -> date | None:
    match = MONTH_DAY_PATTERN.search(query) or SLASH_DATE_PATTERN.search(query)
    if match is None:
        return None
    month = int(match.group(1))
    day = int(match.group(2))
    try:
        return date(today.year, month, day)
    except ValueError:
        return None
