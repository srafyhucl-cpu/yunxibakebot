"""企微智能机器人运营工具展示格式化。"""

import re
from typing import Any

from app.service.wecom.intelligent_bot_tool_format import mask_phone, snippet

ADDRESS_PREVIEW_LENGTH = 4
IDENTIFIER_PREFIX_LENGTH = 4
IDENTIFIER_SUFFIX_LENGTH = 4
TRANSFER_ID_SUFFIX_LENGTH = 5
PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")
ADDRESS_PATTERN = re.compile(r"[\u4e00-\u9fa5A-Za-z0-9]{1,16}[路街道巷弄]\s*\d+\s*号?")


def compact_address(address: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(address.get("id", "")),
        "receiverName": str(address.get("receiverName", "")),
        "receiverPhoneMasked": mask_phone(str(address.get("receiverPhone", ""))),
        "addressPreview": mask_address(str(address.get("address", ""))),
        "isDefault": bool(address.get("isDefault", False)),
        "updatedAt": str(address.get("updatedAt", "")),
    }


def compact_transfer(transfer: Any) -> dict[str, Any]:
    return {
        "id": str(getattr(transfer, "id", "")),
        "sessionId": str(getattr(transfer, "session_id", "")),
        "userRef": mask_identifier(str(getattr(transfer, "user_id", ""))),
        "reason": str(getattr(transfer, "reason", "")),
        "summaryPreview": redact_sensitive_text(
            str(getattr(transfer, "conversation_summary", ""))
        ),
        "createdAt": str(getattr(transfer, "created_at", "")),
    }


def compact_group_followup(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id", "")),
        "customerName": str(item.get("customerName", "")),
        "customerPhoneMasked": mask_phone(str(item.get("customerPhone", ""))),
        "productName": str(item.get("productName", "")),
        "quantity": int(item.get("quantity", 0) or 0),
        "fulfillmentMethod": str(item.get("fulfillmentMethod", "")),
        "desiredTime": str(item.get("desiredTime", "")),
        "addressPreview": mask_address(str(item.get("address", ""))),
        "remarkPreview": redact_sensitive_text(str(item.get("remark", ""))),
        "status": str(item.get("status", "")),
    }


def compact_webhook(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "eventType": str(item.get("event_type", "")),
        "businessKey": str(item.get("business_key", "")),
        "errorType": str(item.get("error_type", "")),
        "errorMessagePreview": redact_sensitive_text(
            str(item.get("error_message", ""))
        ),
    }


def address_line(address: dict[str, Any]) -> str:
    default_label = "默认" if address["isDefault"] else "非默认"
    return (
        f"{address['receiverName']}｜{address['receiverPhoneMasked']}｜"
        f"{default_label}｜{address['addressPreview']}"
    )


def group_summary_line(summary: dict[str, Any]) -> str:
    campaign = summary.get("campaign", {})
    return (
        f"{campaign.get('title', '客户群批次')}："
        f"{summary.get('totalRegistrations', 0)} 人登记，"
        f"合计 {summary.get('totalQuantity', 0)} 份。"
    )


def transfer_line(item: dict[str, Any]) -> str:
    return f"工单尾号 {short_identifier(item['id'])}｜{item['reason'] or '未填写原因'}"


def ops_summary_line(summary: dict[str, Any]) -> str:
    counts = summary.get("counts", {})
    return (
        f"观察台状态：{summary.get('status', 'unknown')}；"
        f"内容失败 {counts.get('content_change_failures', 0)}，"
        f"Webhook 失败 {counts.get('webhook_failures', 0)}，"
        f"处理中 {counts.get('webhook_processing', 0)}，"
        f"慢请求 {counts.get('slow_webhooks', 0)}。"
    )


def webhook_line(item: dict[str, Any]) -> str:
    return (
        f"{item.get('eventType', '')}｜{item.get('businessKey', '')}｜"
        f"{item.get('errorType', '')}｜{item.get('errorMessagePreview', '')}"
    )


def offline_review_line(summary: Any) -> str:
    if not bool(getattr(summary, "ran", False)):
        reason = str(getattr(summary, "skipped_reason", "")) or "not_run"
        return f"最近一轮离线复盘未执行：{reason}。"
    return (
        "最近一轮离线复盘已执行："
        f"质检 {int(getattr(summary, 'review_count', 0) or 0)}，"
        f"知识缺口 {int(getattr(summary, 'gap_count', 0) or 0)}，"
        f"客户记忆 {int(getattr(summary, 'profile_count', 0) or 0)}。"
    )


def mask_address(address: str) -> str:
    compact_value = "".join(address.split())
    if not compact_value:
        return ""
    if len(compact_value) <= ADDRESS_PREVIEW_LENGTH:
        return compact_value[:1] + "***"
    return compact_value[:ADDRESS_PREVIEW_LENGTH] + "..."


def mask_identifier(value: str) -> str:
    compact_value = value.strip()
    if not compact_value:
        return ""
    if len(compact_value) <= IDENTIFIER_PREFIX_LENGTH + IDENTIFIER_SUFFIX_LENGTH:
        return "***"
    return (
        compact_value[:IDENTIFIER_PREFIX_LENGTH]
        + "..."
        + compact_value[-IDENTIFIER_SUFFIX_LENGTH:]
    )


def short_identifier(value: str) -> str:
    compact_value = value.strip()
    if not compact_value:
        return "***"
    return compact_value[-TRANSFER_ID_SUFFIX_LENGTH:]


def redact_sensitive_text(content: str) -> str:
    def replace_phone(match: re.Match[str]) -> str:
        return mask_phone(match.group(0))

    def replace_address(match: re.Match[str]) -> str:
        return mask_address(match.group(0))

    phone_redacted = PHONE_PATTERN.sub(replace_phone, content)
    return snippet(ADDRESS_PATTERN.sub(replace_address, phone_redacted))
