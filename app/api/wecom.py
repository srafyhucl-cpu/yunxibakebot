"""企微回调入口（统一：自建应用 + 微信客服）。

客户发消息给员工（自建应用）、或微信用户发消息给客服（微信客服），都推送到此接口。
需要先在企微后台配置回调 URL，并开启「微信客服消息和事件」开关。

流程：
1. GET 请求验证 URL（echostr 解密）
2. POST 接收消息/事件通知（解密 XML → 根据类型分发处理）

消息类型分流：
- MsgType=text  → 自建应用消息 → 入队 wecom_queue
- MsgType=event + Event=kf_msg_or_event → 微信客服通知 → sync_msg拉取 → 入队 kf_queue

异步设计：
- 回调接口只负责解密 + 入队（<1ms），满足企微 5s 超时要求
- 实际 AI 对话 + 发回复由各队列的 Worker 执行
"""

import time
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.logger import setup_logger
from app.service.wecom.crypto import decrypt, verify_signature

logger = setup_logger()

router = APIRouter(prefix="/api/v1/wecom", tags=["wecom"])


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
    """验证回调 URL（企微 GET 请求）。自建应用与微信共用此验证。"""
    if not settings.WECOM_ENCODING_AES_KEY or not settings.WECOM_TOKEN:
        logger.error("WECOM_ENCODING_AES_KEY 或 WECOM_TOKEN 未配置")
        return PlainTextResponse("配置错误", status_code=500)

    if not verify_signature(
        settings.WECOM_TOKEN, timestamp, nonce, echostr, msg_signature
    ):
        logger.warning("URL 验证签名失败")
        return PlainTextResponse("签名验证失败", status_code=403)

    try:
        plain = decrypt(settings.WECOM_ENCODING_AES_KEY, echostr)
        return PlainTextResponse(plain)
    except Exception as exc:
        logger.error("echostr 解密失败: %s", exc)
        return PlainTextResponse("解密失败", status_code=500)


async def _handle_kf_callback(msg: dict) -> None:
    """
    处理微信客服回调通知。

    收到 event=kf_msg_or_event 后：
    1. 从 XML 中提取 Token 和 OpenKfId
    2. 用 Token 调 /kf/sync_msg 拉取具体消息内容（JSON）
    3. 过滤客户文本消息（origin=3, msgtype=text）
    4. 异步入队到 kf_queue
    """
    kf_token = msg.get("Token", "")
    open_kfid = msg.get("OpenKfId", "")

    if not kf_token:
        logger.warning("客服回调事件中无 Token 字段，忽略")
        return

    logger.info("收到客服回调通知 open_kfid=%s token=%s...", open_kfid, kf_token[:8])

    # 用 Token 调用 sync_msg 拉取消息
    from app.service.wecom.client import get_wecom_client

    client = get_wecom_client()
    try:
        sync_result = await client.sync_kf_messages(kf_token=kf_token)
    except Exception as exc:
        logger.error("sync_msg 拉取消息失败: %s", exc)
        return

    if sync_result.get("errcode") != 0:
        logger.error(
            "sync_msg 返回错误 err=%s %s",
            sync_result.get("errcode"),
            sync_result.get("errmsg"),
        )
        return

    # 处理消息列表
    from app.service.wecom.kf_message_queue import kf_queue, KfIncomingMessage

    msg_list = sync_result.get("msg_list", [])
    enqueued_count = 0

    for item in msg_list:
        origin = item.get("origin", 0)
        msgtype = item.get("msgtype", "")

        # 只处理客户发送的文本消息（origin=3 表示客户发）
        if origin != 3 or msgtype != "text":
            if origin == 4:
                logger.debug(
                    "客服系统事件 type=%s msg_id=%s",
                    item.get("event_type", msgtype),
                    item.get("msgid", ""),
                )
            elif origin == 5:
                logger.debug("接待人员消息（无需处理）msg_id=%s", item.get("msgid", ""))
            continue

        external_userid = item.get("external_userid", "")
        text_content = item.get("text", {}).get("content", "")
        item_msg_id = item.get("msgid", "")

        if not text_content.strip():
            continue

        logger.info(
            "收到客服文本消息 user=%s content=%s msg_id=%s",
            external_userid,
            text_content[:50],
            item_msg_id,
        )

        # 抢先将会话分配给智能助手（避免被系统自动分配为人工接待）
        # 状态 0→1 是允许的；若已是其他状态则忽略错误
        await client.ensure_kf_session_active(external_userid)

        success = await kf_queue.enqueue(
            KfIncomingMessage(
                external_userid=external_userid,
                open_kfid=open_kfid,
                content=text_content,
                msg_id=item_msg_id,
            )
        )
        if success:
            enqueued_count += 1
        else:
            logger.warning("客服消息队列已满，丢弃 user=%s", external_userid)

    logger.info("客服回调处理完成 共%d条消息 入队%d条", len(msg_list), enqueued_count)


@router.post("/callback")
async def receive_message(request: Request) -> PlainTextResponse:
    """接收企微推送的消息和事件（POST）。根据类型分流处理。"""
    if not settings.WECOM_ENCODING_AES_KEY or not settings.WECOM_TOKEN:
        return PlainTextResponse("配置错误", status_code=500)

    raw = await request.body()
    xml_str = raw.decode("utf-8")

    # 签名参数从 URL query string 获取（非 XML body）
    msg_signature = request.query_params.get("msg_signature", "")
    timestamp = request.query_params.get("timestamp", str(int(time.time())))
    nonce = request.query_params.get("nonce", "")

    # 加密消息体从 XML body 提取
    try:
        root = ET.fromstring(xml_str)
        encrypt_xml = root.findtext("Encrypt") or ""
    except ET.ParseError as exc:
        logger.error("XML 解析失败: %s", exc)
        return PlainTextResponse("XML 解析失败", status_code=400)

    # 验签
    if not verify_signature(
        settings.WECOM_TOKEN, timestamp, nonce, encrypt_xml, msg_signature
    ):
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

    # ── 分流：微信客服事件 ──
    if msg_type == "event":
        event_type = msg.get("Event", "")
        if event_type == "kf_msg_or_event":
            await _handle_kf_callback(msg)
        else:
            logger.info("收到其他企微事件 type=%s（未处理）", event_type)
        return PlainTextResponse("")

    # ── 自建应用消息（原有逻辑）──
    content = msg.get("Content", "")
    from_user = msg.get("FromUserName", "")
    msg_id = msg.get("MsgId", "")

    logger.info(
        "收到企微消息 type=%s from=%s msg_id=%s",
        msg_type,
        from_user,
        msg_id,
    )

    # 空文本消息直接忽略
    if msg_type == "text" and not content.strip():
        return PlainTextResponse("")

    # 非文本消息（图片/语音/视频等）：显式记录，便于排查与后续扩展
    if msg_type != "text":
        logger.info(
            "企微非文本消息暂不支持，已跳过处理 type=%s from=%s msg_id=%s",
            msg_type,
            from_user,
            msg_id,
        )
        return PlainTextResponse("")

    # 异步入队：立即返回，后台 Worker 负责处理
    from app.service.wecom.message_queue import wecom_queue, WeComIncomingMessage

    success = await wecom_queue.enqueue(
        WeComIncomingMessage(
            external_user_id=from_user,
            content=content,
            channel_msg_id=msg_id,
        )
    )
    if not success:
        logger.warning("企微消息队列已满，丢弃消息 user=%s", from_user)

    # 企微回调要求立即返回 200，内容为空
    return PlainTextResponse("")
