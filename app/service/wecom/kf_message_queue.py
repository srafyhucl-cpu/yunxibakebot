"""微信客服异步消息队列 + 后台 Worker。

职责：
- 接收入队请求，立即返回（<1ms）
- 后台循环消费队列，调用 ChatService 处理 AI 对话
- 使用 /kf/send_msg 发送回复（与自建应用的 /message/send 完全独立）
- 解析 UMP 统一媒体协议标记，分离文本和卡片/图片发送

使用方式：
    lifespan startup:  kf_queue.start_worker(chat_service)
    callback 入队:      kf_queue.enqueue(KfIncomingMessage(...))
    lifespan shutdown:   await kf_queue.stop()
"""

import asyncio
import re
from dataclasses import dataclass
from urllib.parse import unquote

from app.logger import setup_logger
from app.service.wecom.base_queue import BaseWeComMessageQueue
from app.service.wecom.processed_message_cache import ProcessedMessageCache

logger = setup_logger()

# 已处理的 msg_id 集合（内存去重，防止企微重复推送导致 AI 多次回复）
# 最大缓存条数（防止内存泄漏）
_MAX_PROCESSED_CACHE = 5000
_processed_msg_cache = ProcessedMessageCache(max_size=_MAX_PROCESSED_CACHE)

# 队列容量上限（满队列时新消息被丢弃）
QUEUE_MAX_SIZE = 1000

# UMP 标记正则：[UMP: type=xxx&key=value&...]
UMP_PATTERN = re.compile(r"\[UMP:\s*(.*?)\]")


def _parse_ump_tags(text: str) -> tuple[str, list[dict]]:
    """
    从回复文本中解析 UMP 标记。

    返回：(纯文本, UMP标签列表)
    每个UMP标签是解析后的参数字典。
    """
    ump_list: list[dict] = []

    def _replacer(match: re.Match[str]) -> str:
        raw = match.group(1)
        params: dict[str, str] = {}
        for pair in raw.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                params[k.strip()] = unquote(v.strip())
        if params:
            ump_list.append(params)
        return ""  # 移除标记文本

    clean_text = UMP_PATTERN.sub(_replacer, text).strip()
    return clean_text, ump_list


@dataclass(frozen=True)
class KfIncomingMessage:
    """微信客服入队消息（不可变数据对象）。"""

    external_userid: str  # 微信客户的 external_userid
    open_kfid: str  # 客服账号 ID
    content: str  # 文本内容（文本消息为原文，非文本消息为占位描述）
    msg_id: str  # 消息唯一 ID
    msgtype: str = "text"  # 消息类型（text/image/voice/video/file/location 等）
    media_id: str = ""  # 非文本消息的素材 ID（用于下载）


class KfMessageQueue(BaseWeComMessageQueue[KfIncomingMessage]):
    """微信客服异步消息队列 + 后台 Worker。"""

    def __init__(self) -> None:
        super().__init__(QUEUE_MAX_SIZE, "微信客服消息队列")

    async def enqueue(self, msg: KfIncomingMessage) -> bool:
        """
        入队（非阻塞）。
        返回 True 表示入队成功，False 表示队列已满。
        """
        # 1. 内存去重（在入队前端进行，防范微信客服历史重推消息塞爆队列）
        if not _processed_msg_cache.add_if_new(msg.msg_id):
            logger.debug("入队拦截：重复消息已跳过 msg_id=%s", msg.msg_id)
            return True
        # 防止内存无限增长：超过上限时清空旧数据

        try:
            self._queue.put_nowait(msg)
            return True
        except asyncio.QueueFull:
            logger.warning(
                "客服消息队列已满（%d），丢弃消息 user=%s",
                QUEUE_MAX_SIZE,
                msg.external_userid,
            )
            return False

    async def _process_one(self, msg: KfIncomingMessage) -> None:
        """
        处理单条客服消息的完整流程：
        1. 非文本消息处理：图片→下载+识别，其他→兜底提示
        2. 文本/图片消息：调用 ChatService 进行 AI 对话
        3. 解析回复中的 UMP 标记（卡片/图片）
        4. 通过 /kf/send_msg 发送纯文本和链接消息
        """
        if self._chat_service is None:
            logger.error("ChatService 未注入，无法处理客服消息")
            return

        from app.database import db_session_scope
        from app.service.wecom.client import get_wecom_client

        client = get_wecom_client()

        # ── 非文本消息预处理 ──
        image_base64: str = ""
        effective_content = msg.content
        nontext_fallback_map = {
            "video": "抱歉，我暂时无法查看视频，麻烦您用文字描述一下需要咨询的问题~",
            "file": "抱歉，我暂时无法接收文件，请直接用文字告诉我您的问题，我会尽快为您解答 :)",
            "location": "我看到您发了一个位置信息~ 请问是想了解配送范围还是门店地址呢？",
        }

        if msg.msgtype != "text":
            # 图片消息：尝试下载并转 base64 交给 AI 识别
            if msg.msgtype == "image" and msg.media_id:
                try:
                    media_bytes = await client.download_kf_temp_media(msg.media_id)
                    if media_bytes:
                        import base64

                        image_base64 = base64.b64encode(media_bytes).decode("utf-8")
                        effective_content = "[用户发送了一张图片]"
                        logger.info(
                            "图片素材已下载 size=%dB user=%s",
                            len(media_bytes),
                            msg.external_userid,
                        )
                    else:
                        # 下载失败，走兜底
                        effective_content = ""
                except Exception as exc:
                    logger.error(
                        "下载图片素材异常 user=%s err=%s", msg.external_userid, exc
                    )
                    effective_content = ""

            # 语音消息：下载后调用 MiMo ASR 转文字
            elif msg.msgtype == "voice" and msg.media_id:
                try:
                    from app.service.llm.client import asr_transcribe
                    from app.utils import convert_amr_to_wav

                    voice_bytes = await client.download_kf_temp_media(msg.media_id)
                    if voice_bytes:
                        # 企微语音默认为 amr 格式，MiMo ASR 支持 wav/mp3，先转码为 wav
                        try:
                            wav_bytes = await convert_amr_to_wav(voice_bytes)
                        except Exception as convert_err:
                            logger.error(
                                "语音转码失败 user=%s err=%s",
                                msg.external_userid,
                                convert_err,
                            )
                            wav_bytes = None

                        if wav_bytes:
                            import base64

                            audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")
                            raw_asr_text = await asr_transcribe(
                                audio_base64=audio_b64,
                                mime_type="audio/wav",
                                language="zh",
                            )
                            asr_text = raw_asr_text.strip()
                            if asr_text:
                                effective_content = f"[语音] {asr_text}"
                                logger.info(
                                    "ASR 语音转文字成功 原文=%s user=%s",
                                    asr_text[:50],
                                    msg.external_userid,
                                )
                            else:
                                effective_content = ""
                        else:
                            effective_content = ""
                    else:
                        effective_content = ""
                except Exception as exc:
                    logger.error(
                        "语音 ASR 转写异常 user=%s err=%s",
                        msg.external_userid,
                        exc,
                    )
                    effective_content = ""
            else:
                effective_content = ""

            if not image_base64 and not effective_content:
                # 非图片或图片下载失败 → 直接回复兜底提示，不调 AI
                fallback = nontext_fallback_map.get(
                    msg.msgtype,
                    "您好~ 我暂时只能识别文字和图片消息，麻烦用文字描述一下哦 :)",
                )
                logger.info(
                    "非文本消息返回兜底提示 type=%s user=%s",
                    msg.msgtype,
                    msg.external_userid,
                )
                result = await client.send_kf_text(msg.external_userid, fallback)
                if result.get("errcode") != 0:
                    logger.error(
                        "兜底提示发送失败 user=%s err=%s",
                        msg.external_userid,
                        result.get("errmsg"),
                    )
                return

        # 确保会话处于可发消息状态（企微限制：非智能助手状态无法API发送）
        can_send = await client.ensure_kf_session_active(msg.external_userid)
        if not can_send:
            logger.info("客服会话不可用，跳过回复 user=%s", msg.external_userid)
            return

        # Worker 绕过 API 层直接调用 service，需自行提供数据库上下文
        async with db_session_scope():
            # 处理前同步 session 状态与企微实际状态
            # 场景：之前转人工后企微会话已结束（state=4），用户重新发消息
            # 触发企微创建新会话（state=0/1），但数据库 session.status 还是 transfer_pending
            # 此时需要重置 session 为 active，让 AI 能正常回复
            from app.models.session import SessionStatus
            from app.repository.session_repo import SessionRepo

            session_repo = SessionRepo()
            session = await session_repo.get_active(msg.external_userid, "wecom_kf")
            if session and session.status in (
                "transfer_pending",
                "human_service",
            ):
                # 查询企微实际会话状态
                kf_state = await client.get_kf_service_state(msg.external_userid)
                # 企微状态 0(未处理)、1(智能助手) 或 4(已结束)
                # 说明旧的人工会话已结束，应重置 session 让 AI 继续服务
                if kf_state is not None and kf_state in (0, 1, 4):
                    await session_repo.update_status(session.id, SessionStatus.ACTIVE)
                    logger.info(
                        "企微会话已重建(state=%d)，重置session %s 为active",
                        kf_state,
                        session.id,
                    )

            reply = await self._chat_service.handle_message(
                channel="wecom_kf",  # 用独立渠道标识区分来源
                user_id=msg.external_userid,
                content=effective_content,
                channel_msg_id=msg.msg_id,
                image_base64=image_base64 or None,
            )

            if not reply:
                return

            # 处理完 AI 回复后，检查 session 是否因转人工而变为人工状态
            # 如果是，则通知企微将会话切换为人工接待模式（service_state=3）
            from app.repository.session_repo import SessionRepo

            session_repo = SessionRepo()
            session = await session_repo.get_active(msg.external_userid, "wecom_kf")
            if session and session.status in (
                "transfer_pending",
                "human_service",
            ):
                logger.info(
                    "会话已进入人工状态(%s)，切换企微为人工接待 mode user=%s",
                    session.status,
                    msg.external_userid,
                )
                trans_result = await client._trans_service_state(
                    msg.external_userid,
                    3,
                )
                if not trans_result:
                    logger.error("切换人工接待模式失败 user=%s", msg.external_userid)

        # 解析 UMP 标记，分离纯文本和卡片/图片
        clean_text, ump_tags = _parse_ump_tags(reply)

        # 发送纯文本（如果解析后还有内容）
        if clean_text:
            result = await client.send_kf_text(msg.external_userid, clean_text)
            if result.get("errcode") != 0:
                logger.error(
                    "客服文本回复发送失败 user=%s err=%s",
                    msg.external_userid,
                    result.get("errmsg"),
                )

        # 发送 UMP 卡片（type=card 用 link 图文链接消息）
        for ump in ump_tags:
            ump_type = ump.get("type", "")
            if ump_type == "card":
                await self._send_card(client, msg.external_userid, ump)
            elif ump_type == "image":
                logger.debug("UMP image 暂不单独发送（图片已内置在 card 中）")

    async def _send_card(self, client, external_userid: str, card: dict) -> None:
        """
        发送商品卡片（link 图文链接消息）。

        流程：
        1. 如果有商品图片 → 下载图片 → 上传到企微素材库获取 thumb_media_id
        2. 用 thumb_media_id 发送 link 图文消息（微信端可显示为卡片）
        3. 若无图片或上传失败 → 降级为文本消息
        """
        title = card.get("title", "商品推荐")
        price = card.get("price", "")
        img_url = card.get("src", "")
        link_url = card.get("url", "")

        # 构建描述：标题 + 价格
        description = f"¥{price}" if price else title

        # 尝试上传缩略图（企微 link 消息的 thumb_media_id 必填）
        thumb_media_id = ""
        if img_url:
            try:
                # 下载商品图片（httpx 直接 await，不用 async with）
                img_resp = await client._client.get(img_url, timeout=10)
                if img_resp.status_code == 200:
                    img_data = await img_resp.aread()
                    logger.info(
                        "已下载商品图片 size=%dB url=%s",
                        len(img_data),
                        img_url[:80],
                    )
                    # 上传到企微素材库
                    thumb_media_id = await client.upload_kf_temp_media(
                        file_data=img_data,
                        file_type="image",
                        file_name=f"{title}.jpg",
                    )
                else:
                    logger.warning(
                        "下载商品图片失败 status=%d url=%s",
                        img_resp.status_code,
                        img_url[:80],
                    )
            except Exception as e:
                logger.warning("下载/上传商品图片异常 url=%s err=%s", img_url[:80], e)

        # 发送 link 图文消息
        result = await client.send_kf_link(
            external_userid=external_userid,
            title=title,
            url=link_url or "",
            desc=description,
            thumb_media_id=thumb_media_id or "",
        )
        if result.get("errcode") == 0:
            logger.info("客服商品卡片已发送 user=%s title=%s", external_userid, title)
            return

        # link 消息失败，降级为文本消息
        logger.warning(
            "客服link卡片发送失败，降级为文本消息 user=%s err=%s",
            external_userid,
            result.get("errmsg"),
        )

        text_parts = [f"📦 {title}"]
        if price:
            text_parts.append(f"💰 ¥{price}")
        if link_url:
            text_parts.append(f"🔗 {link_url}")
        if img_url:
            text_parts.append(f"🖼️ {img_url}")

        fallback_text = "\n".join(text_parts)
        text_result = await client.send_kf_text(external_userid, fallback_text)
        if text_result.get("errcode") != 0:
            logger.error(
                "客服商品卡片文本降级也失败 user=%s err=%s",
                external_userid,
                text_result.get("errmsg"),
            )

    def _message_log_context(self, msg: KfIncomingMessage) -> str:
        return f"user={msg.external_userid} msg_id={msg.msg_id}"


# ── 全局单例 ────────────────────────────────────────────────
kf_queue = KfMessageQueue()
