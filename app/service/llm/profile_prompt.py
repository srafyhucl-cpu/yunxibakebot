"""顾客画像 Prompt 渲染。"""

import json
from typing import Any

from app.models.customer_profile import CustomerProfile

PROFILE_EMPTY_SECTION = ""


def render_customer_profile(profile: CustomerProfile | None) -> str:
    """把顾客画像渲染为给 AI 的只读提醒。"""
    if profile is None:
        return PROFILE_EMPTY_SECTION

    lines: list[str] = []
    if profile.display_name:
        lines.append(f"顾客称呼：{profile.display_name}")

    preferences = _render_json_value(profile.preferences_json)
    if preferences:
        lines.append(f"顾客偏好：{preferences}")

    order_summary = _render_json_value(profile.order_summary_json)
    if order_summary:
        lines.append(f"最近订单摘要：{order_summary}")

    allergens = _render_json_value(profile.allergens_json)
    if allergens:
        lines.append(
            f"该顾客登记过敏原：{allergens}。涉及成分时主动提醒顾客核对，不要替顾客判断能否食用。"
        )

    if not lines:
        return PROFILE_EMPTY_SECTION
    return "## 顾客档案\n" + "\n".join(f"- {line}" for line in lines) + "\n"


def _render_json_value(raw_json: str) -> str:
    try:
        parsed = json.loads(raw_json or "")
    except json.JSONDecodeError:
        return raw_json.strip()
    return _render_value(parsed)


def _render_value(value: Any) -> str:
    if value in ({}, [], "", None):
        return ""
    if isinstance(value, dict):
        parts = [
            f"{key}: {_render_value(item)}"
            for key, item in value.items()
            if item not in ("", None, [], {})
        ]
        return "、".join(parts)
    if isinstance(value, list):
        return "、".join(str(item) for item in value if item not in ("", None, [], {}))
    return str(value)
