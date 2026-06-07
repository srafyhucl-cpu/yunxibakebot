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

logger = setup_logger()

# 已处理的 msg_id 集合（内存去重，防止企微重复推送导致 AI 多次回复）
_processed_msg_ids: set[str] = set()
# 最大缓存条数（防止内存泄漏）
_MAX_PROCESSED_CACHE = 5000

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
    content: str  # 文本内容
    msg_id: str  # 消息唯一 ID


class KfMessageQueue:
    """微信客服异步消息队列 + 后台 Worker。"""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[KfIncomingMessage] = asyncio.Queue(
            maxsize=QUEUE_MAX_SIZE
        )
        self._worker_task: asyncio.Task[None] | None = None
        self._chat_service = None  # 延迟注入（lifespan 启动时设置）

    async def enqueue(self, msg: KfIncomingMessage) -> bool:
        """
        入队（非阻塞）。
        返回 True 表示入队成功，False 表示队列已满。
        """
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

    def start_worker(self, chat_service) -> None:
        """
        启动后台消费任务。

        参数：
            chat_service: ChatService 实例，用于处理消息和发送回复
        必须在事件循环中调用（通常在 lifespan startup 阶段）。
        """
        if self._worker_task is not None and not self._worker_task.done():
            logger.warning("客服 Worker 已在运行，跳过重复启动")
            return

        self._chat_service = chat_service
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("微信客服消息队列 Worker 已启动")

    async def stop(self) -> None:
        """停止后台 Worker（应用关闭时调用）。"""
        if self._worker_task is None or self._worker_task.done():
            return

        self._worker_task.cancel()
        try:
            await self._worker_task
        except asyncio.CancelledError:
            pass
        self._worker_task = None
        logger.info("微信客服消息队列 Worker 已停止")

    @property
    def queue_size(self) -> int:
        """当前队列中待处理的消息数量（用于监控）。"""
        return self._queue.qsize()

    async def _worker_loop(self) -> None:
        """后台循环：持续从队列取消息并处理。"""
        logger.info("微信客服消息队列 Worker 开始运行")
        while True:
            try:
                # 阻塞等待下一条消息
                msg = await self._queue.get()
            except (asyncio.CancelledError, GeneratorExit):
                break

            try:
                await self._process_one(msg)
            except Exception as exc:
                # 异常隔离：单条失败不影响后续处理
                logger.error(
                    "客服消息处理异常 user=%s msg_id=%s err=%s",
                    msg.external_userid,
                    msg.msg_id,
                    exc,
                )
            finally:
                self._queue.task_done()

    async def _process_one(self, msg: KfIncomingMessage) -> None:
        """
        处理单条客服消息的完整流程：
        0. 消息去重（防止企微重复推送）
        1. 调用 ChatService 进行 AI 对话
        2. 解析回复中的 UMP 标记（卡片/图片）
        3. 通过 /kf/send_msg 发送纯文本和链接消息
        """
        # 消息去重：同一 msg_id 不重复处理
        if msg.msg_id in _processed_msg_ids:
            logger.debug("重复消息已跳过 msg_id=%s", msg.msg_id)
            return
        _processed_msg_ids.add(msg.msg_id)
        # 防止内存无限增长：超过上限时清空旧数据
        if len(_processed_msg_ids) > _MAX_PROCESSED_CACHE:
            _processed_msg_ids.clear()
            logger.info("已处理消息缓存已清空（达到上限 %d）", _MAX_PROCESSED_CACHE)
        if self._chat_service is None:
            logger.error("ChatService 未注入，无法处理客服消息")
            return

        from app.database import db_session_scope
        from app.service.wecom.client import get_wecom_client

        client = get_wecom_client()

        # 确保会话处于可发消息状态（企微限制：非智能助手状态无法API发送）
        can_send = await client.ensure_kf_session_active(msg.external_userid)
        if not can_send:
            logger.info("客服会话不可用，跳过回复 user=%s", msg.external_userid)
            return

        # Worker 绕过 API 层直接调用 service，需自行提供数据库上下文
        async with db_session_scope():
            reply = await self._chat_service.handle_message(
                channel="wecom_kf",  # 用独立渠道标识区分来源
                user_id=msg.external_userid,
                content=msg.content,
                channel_msg_id=msg.msg_id,
            )

            if not reply:
                return

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


# ── 全局单例 ────────────────────────────────────────────────
kf_queue = KfMessageQueue()
