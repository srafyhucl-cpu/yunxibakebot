"""
webhook 消息解析辅助函数。

从有赞 Webhook payload 中提取 trace_id、msg 字段、业务类型与业务主键。
"""

import hashlib
import json
import urllib.parse

from app.models.youzan_webhook_event import YouzanWebhookBusinessType


def extract_trace_id(request) -> str:
    """从请求头 X-Rontgen 中提取 traceId。"""
    rontgen = request.headers.get("x-rontgen", "")
    for part in rontgen.split(";"):
        if part.startswith("traceId="):
            return part[len("traceId=") :]
    return ""


def parse_payload_msg(payload: dict) -> dict:
    """解析 payload 中的 msg 字段（可能是 JSON 字符串或字典）。"""
    raw_msg = payload.get("msg")
    if isinstance(raw_msg, dict):
        return raw_msg
    if not raw_msg:
        return {}
    try:
        parsed = json.loads(urllib.parse.unquote(str(raw_msg)))
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def extract_business_fields(
    payload: dict, event_type: str, buyer_id: str
) -> tuple[str, str]:
    """从 webhook payload 提取业务类型与业务主键。

    item_id 解析委托给 app.service.youzan.webhook.parse_item_id。
    """
    from app.service.youzan.webhook import parse_item_id

    event_type_lower = event_type.lower()
    msg_obj = parse_payload_msg(payload)
    if event_type_lower.startswith("trade_"):
        tid = msg_obj.get("tid", "")
        if not tid:
            order_info = msg_obj.get("full_order_info", {}).get("order_info", {})
            tid = order_info.get("tid", "")
        return YouzanWebhookBusinessType.TRADE, str(tid)
    if (
        event_type_lower.startswith("item_")
        or event_type_lower == "youzan_item_skustockorsoldnumupdated"
    ):
        item_id = parse_item_id(payload, msg_obj)
        return YouzanWebhookBusinessType.ITEM, str(item_id or "")
    if buyer_id:
        return YouzanWebhookBusinessType.CHAT, buyer_id
    return YouzanWebhookBusinessType.UNKNOWN, ""


def build_payload_summary(
    payload: dict, event_type: str, business_type: str, business_key: str
) -> str:
    """构建 payload 摘要（截断至 300 字符），用于审计记录。"""
    summary = {
        "id": payload.get("id", ""),
        "msg_id": payload.get("msg_id", ""),
        "type": event_type,
        "business_type": business_type,
        "business_key": business_key,
        "timestamp": payload.get("timestamp", ""),
        "msg_type": payload.get("msg_type", ""),
        "buyer_id": payload.get("buyer_id", ""),
    }
    return json.dumps(summary, ensure_ascii=False)[:300]
