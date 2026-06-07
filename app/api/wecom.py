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

    # 第一步：按用户分组收集客户消息（origin=3）
    # 文本消息按 msg_id 去重；非文本消息（图片/语音/视频等）提取 media_id 一并入队
    user_messages: dict[str, dict[str, dict]] = {}  # {user: {msgid: item}}
    nontext_messages: list[
        dict
    ] = []  # 非文本消息列表（每个用户最多保留一条，避免刷屏）
    nontext_processed_users: set[str] = (
        set()
    )  # 已处理非文本消息的用户（每个用户每轮只处理一条）

    for item in msg_list:
        origin = item.get("origin", 0)
        msgtype = item.get("msgtype", "")
        item_msgid = item.get("msgid", "")

        if origin != 3:
            if origin == 4:
                logger.debug(
                    "客服系统事件 type=%s msg_id=%s",
                    item.get("event_type", msgtype),
                    item_msgid,
                )
            elif origin == 5:
                logger.debug("接待人员消息（无需处理）msg_id=%s", item_msgid)
            continue

        external_userid = item.get("external_userid", "")

        # 文本消息：按 msg_id 去重后入队
        if msgtype == "text":
            text_content = item.get("text", {}).get("content", "")
            if not text_content.strip():
                continue

            # 同一 msg_id 的重复推送只保留一条，不同 msg_id 都保留
            user_dict = user_messages.setdefault(external_userid, {})
            if item_msgid not in user_dict:
                user_dict[item_msgid] = item
                logger.info(
                    "收到客服文本消息 user=%s content=%s msg_id=%s",
                    external_userid,
                    text_content[:50],
                    item_msgid,
                )
            else:
                logger.debug(
                    "重复消息已跳过 user=%s msg_id=%s", external_userid, item_msgid
                )

        # 非文本消息：提取 media_id，每用户每轮只保留一条（避免连续发多张图导致多次调用）
        else:
            # 每个用户本轮回调中只处理第一条非文本消息
            if external_userid not in nontext_processed_users:
                nontext_processed_users.add(external_userid)
                media_id = ""
                # 各类型的 media_id 提取位置不同
                if msgtype == "image":
                    media_id = item.get("image", {}).get("media_id", "")
                elif msgtype == "voice":
                    media_id = item.get("voice", {}).get("media_id", "")
                elif msgtype == "video":
                    media_id = item.get("video", {}).get("media_id", "")
                elif msgtype == "file":
                    media_id = item.get("file", {}).get("media_id", "")

                logger.info(
                    "收到客服非文本消息 type=%s user=%s media_id=%s msg_id=%s",
                    msgtype,
                    external_userid,
                    media_id[:20] if media_id else "(空)",
                    item_msgid,
                )
                nontext_messages.append(
                    {
                        "external_userid": external_userid,
                        "open_kfid": open_kfid,
                        "msgtype": msgtype,
                        "media_id": media_id,
                        "msg_id": item_msgid,
                    }
                )

    # 第二步：对每个用户做一次会话状态处理，然后入队所有去重后的消息（文本 + 非文本）
    enqueued_count = 0
    for ext_uid, msg_dict in user_messages.items():
        # 抢先处理会话状态（新会话分配给智能助手，人工会话则结束）
        can_reply = await client.ensure_kf_session_active(ext_uid)
        if not can_reply:
            logger.info(
                "用户会话不可用，跳过 %d 条消息 user=%s",
                len(msg_dict),
                ext_uid,
            )
            continue

        for _msgid, item in msg_dict.items():
            success = await kf_queue.enqueue(
                KfIncomingMessage(
                    external_userid=ext_uid,
                    open_kfid=open_kfid,
                    content=item["text"]["content"],
                    msg_id=_msgid,
                    msgtype="text",
                )
            )
            if success:
                enqueued_count += 1
            else:
                logger.warning("客服消息队列已满，丢弃 user=%s", ext_uid)

    # 入队非文本消息（图片/语音/视频等）
    for nontext in nontext_messages:
        ext_uid = nontext["external_userid"]
        # 非文本消息也需要确认会话状态
        can_reply = await client.ensure_kf_session_active(ext_uid)
        if not can_reply:
            logger.info(
                "用户会话不可用，跳过非文本消息 type=%s user=%s",
                nontext["msgtype"],
                ext_uid,
            )
            continue

        success = await kf_queue.enqueue(
            KfIncomingMessage(
                external_userid=ext_uid,
                open_kfid=nontext["open_kfid"],
                content=f"[{nontext['msgtype']}消息]",
                msg_id=nontext["msg_id"],
                msgtype=nontext["msgtype"],
                media_id=nontext["media_id"],
            )
        )
        if success:
            enqueued_count += 1
        else:
            logger.warning(
                "客服消息队列已满，丢弃非文本消息 user=%s type=%s",
                ext_uid,
                nontext["msgtype"],
            )

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
