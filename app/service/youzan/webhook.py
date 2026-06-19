"""
有赞 Webhook 工具函数集。

包含签名验证、消息解析、item_id 多级降级提取等通用逻辑。
"""

import hashlib
import hmac
import json

from app.exceptions import AuthError
from app.logger import setup_logger

logger = setup_logger()


def verify_signature(
    client_id: str, client_secret: str, raw_body: bytes, signature_header: str
) -> bool:
    """验证有赞消息推送签名：MD5(client_id + raw_body + client_secret)。"""
    expected = hashlib.md5(
        (
            client_id + raw_body.decode("utf-8", errors="replace") + client_secret
        ).encode()
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def parse_webhook_payload(body: bytes) -> dict:
    """解析 webhook JSON 负载，解析失败抛出 AuthError。"""
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        logger.error("Invalid Youzan webhook payload: %s", exc)
        raise AuthError("Invalid JSON payload") from exc


def parse_item_id(payload: dict, msg_obj: dict | None = None) -> str | None:
    """
    从有赞 webhook payload 中多级降级提取 item_id。

    查找优先级（从高到低）：
    1. msg_obj.item_id（msg 字段内层）
    2. msg_obj.data.item_id（msg.data 内层，支持 JSON 字符串自动解析）
    3. payload.data.item_id（payload 外层的 data 子字段）
    4. payload.item_id（payload 顶层）
    5. payload.id（仅当值为纯数字字符串时采纳，排除含字母的消息标识）

    参数：
        payload: 有赞 Webhook 原始 payload 字典
        msg_obj: 已解析的 msg 对象字典（可选）

    返回：
        解析出的 item_id 字符串，未找到时返回 None
    """
    if msg_obj is None:
        msg_obj = {}

    # 1. msg_obj.item_id（直接字段）
    item_id = msg_obj.get("item_id")
    if item_id:
        return str(item_id)

    # 2. msg_obj.data.item_id（支持 JSON 字符串自动解析）
    msg_data = msg_obj.get("data", {})
    if isinstance(msg_data, str):
        try:
            msg_data = json.loads(msg_data)
        except Exception:
            msg_data = {}
    if isinstance(msg_data, dict):
        item_id = msg_data.get("item_id")
        if item_id:
            return str(item_id)

    # 3. payload.data.item_id
    payload_data = payload.get("data", {})
    if isinstance(payload_data, dict):
        item_id = payload_data.get("item_id")
        if item_id:
            return str(item_id)

    # 4. payload.item_id（顶层）
    item_id = payload.get("item_id")
    if item_id:
        return str(item_id)

    # 5. payload.id（仅纯数字值有效，排除含字母的消息标识如 20260527091748314JAM）
    raw_id = payload.get("id")
    if raw_id is not None:
        raw_id_str = str(raw_id)
        if raw_id_str.isdigit():
            return raw_id_str

    return None
