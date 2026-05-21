"""企微回调入口。

客户发消息给员工时，企微推送到此接口。
需要先在企微后台配置回调 URL。

流程：
1. GET 请求验证 URL（echostr 解密）
2. POST 接收消息（解密 XML → 交给 ChatService 处理 → 发回复）
"""

import time
import xml.etree.ElementTree as ET
from collections.abc import Callable

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.logger import setup_logger
from app.service.wecom.crypto import decrypt, verify_signature

logger = setup_logger()

router = APIRouter(prefix="/api/v1/wecom", tags=["wecom"])

# 消息处理回调（由 ChatService 注册）
_message_handler: Callable | None = None


def register_handler(handler: Callable) -> None:
    """注册消息处理函数。"""
    global _message_handler
    _message_handler = handler


def _parse_message_xml(xml_str: str) -> dict:
    """解析企微回调消息 XML 为字典。"""
    root = ET.fromstring(xml_str)
    result: dict = {}
    for child in root:
        result[child.tag] = child.text or ""
    return result


@router.get("/callback")
async def verify_url(
    msg_signature: str,
    timestamp: str,
    nonce: str,
    echostr: str,
) -> PlainTextResponse:
    """验证回调 URL（企微 GET 请求）。"""
    if not settings.WECOM_ENCODING_AES_KEY or not settings.WECOM_TOKEN:
        logger.error("WECOM_ENCODING_AES_KEY 或 WECOM_TOKEN 未配置")
        return PlainTextResponse("配置错误", status_code=500)

    if not verify_signature(settings.WECOM_TOKEN, timestamp, nonce, echostr, msg_signature):
        logger.warning("URL 验证签名失败")
        return PlainTextResponse("签名验证失败", status_code=403)

    try:
        plain = decrypt(settings.WECOM_ENCODING_AES_KEY, echostr)
        return PlainTextResponse(plain)
    except Exception as exc:
        logger.error("echostr 解密失败: %s", exc)
        return PlainTextResponse("解密失败", status_code=500)


@router.post("/callback")
async def receive_message(request: Request) -> PlainTextResponse:
    """接收企微推送的消息（POST）。"""
    if not settings.WECOM_ENCODING_AES_KEY or not settings.WECOM_TOKEN:
        return PlainTextResponse("配置错误", status_code=500)

    raw = await request.body()
    xml_str = raw.decode("utf-8")

    # 提取加密字段
    try:
        root = ET.fromstring(xml_str)
        msg_signature = root.findtext("MsgSignature") or ""
        timestamp = root.findtext("TimeStamp") or str(int(time.time()))
        nonce = root.findtext("Nonce") or ""
        encrypt_xml = root.findtext("Encrypt") or ""
    except ET.ParseError as exc:
        logger.error("XML 解析失败: %s", exc)
        return PlainTextResponse("XML 解析失败", status_code=400)

    # 验签
    if not verify_signature(settings.WECOM_TOKEN, timestamp, nonce, encrypt_xml, msg_signature):
        logger.warning("消息签名验证失败")
        return PlainTextResponse("签名验证失败", status_code=403)

    # 解密
    try:
        plain_xml = decrypt(settings.WECOM_ENCODING_AES_KEY, encrypt_xml)
    except Exception as exc:
        logger.error("消息解密失败: %s", exc)
        return PlainTextResponse("解密失败", status_code=500)

    msg = _parse_message_xml(plain_xml)
    msg_type = msg.get("MsgType", "")
    content = msg.get("Content", "")
    from_user = msg.get("FromUserName", "")
    msg_id = msg.get("MsgId", "")

    logger.info(
        "收到企微消息 type=%s from=%s msg_id=%s",
        msg_type, from_user, msg_id,
    )

    # 只处理文本消息
    if msg_type != "text" or not content.strip():
        return PlainTextResponse("")

    # 转给 ChatService 处理
    if _message_handler:
        try:
            await _message_handler(
                channel="wecom_1on1",
                user_id=from_user,
                content=content,
                channel_msg_id=msg_id,
            )
        except Exception as exc:
            logger.error("消息处理失败: %s", exc)

    # 企微回调要求立即返回 200，内容为空
    return PlainTextResponse("")
