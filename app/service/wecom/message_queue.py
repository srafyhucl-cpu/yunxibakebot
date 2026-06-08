"""企微异步消息队列 + 后台 Worker。

职责：
- 接收入队请求，立即返回（<1ms），满足企微回调 5s 超时要求
- 后台循环消费队列，调用 ChatService 处理
- 异常隔离：单条消息失败不影响其他消息
- 解析 UMP 统一媒体协议标记，分离文本和卡片/图片发送

使用方式：
    lifespan startup:  wecom_queue.start_worker(chat_service)
    callback 入队:      wecom_queue.enqueue(WeComIncomingMessage(...))
    lifespan shutdown:   await wecom_queue.stop()
"""

import asyncio
import re
from dataclasses import dataclass
from urllib.parse import unquote

from app.logger import setup_logger
from app.service.wecom.base_queue import BaseWeComMessageQueue

logger = setup_logger()

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
class WeComIncomingMessage:
    """企微入队消息（不可变数据对象）。"""

    external_user_id: str
    content: str
    channel_msg_id: str


class WeComMessageQueue(BaseWeComMessageQueue[WeComIncomingMessage]):
    """企微异步消息队列 + 后台 Worker。"""

    def __init__(self) -> None:
        super().__init__(QUEUE_MAX_SIZE, "企微消息队列")

    async def enqueue(self, msg: WeComIncomingMessage) -> bool:
        """
        入队（非阻塞）。
        返回 True 表示入队成功，False 表示队列已满。
        """
        try:
            self._queue.put_nowait(msg)
            return True
        except asyncio.QueueFull:
            logger.warning(
                "企微消息队列已满（%d），丢弃消息 user=%s",
                QUEUE_MAX_SIZE,
                msg.external_user_id,
            )
            return False

    async def _process_one(self, msg: WeComIncomingMessage) -> None:
        """
        处理单条企微消息的完整流程：
        1. 调用 ChatService 进行 AI 对话
        2. 解析回复中的 UMP 标记（卡片/图片）
        3. 发送纯文本和卡片消息
        """
        if self._chat_service is None:
            logger.error("ChatService 未注入，无法处理消息")
            return

        from app.database import db_session_scope
        from app.service.wecom.client import get_wecom_client

        client = get_wecom_client()

        # Worker 绕过 API 层直接调用 service，需自行提供数据库上下文
        async with db_session_scope():
            reply = await self._chat_service.handle_message(
                channel="wecom_1on1",
                user_id=msg.external_user_id,
                content=msg.content,
                channel_msg_id=msg.channel_msg_id,
            )

            if not reply:
                return

            # 解析 UMP 标记，分离纯文本和卡片/图片
            clean_text, ump_tags = _parse_ump_tags(reply)

            # 发送纯文本（如果解析后还有内容）
            if clean_text:
                result = await client.send_text(msg.external_user_id, clean_text)
                if result.get("errcode") != 0:
                    logger.error(
                        "企微回复发送失败 user=%s err=%s",
                        msg.external_user_id,
                        result.get("errmsg"),
                    )

            # 发送 UMP 卡片（type=card 用 news 图文消息）
            for ump in ump_tags:
                ump_type = ump.get("type", "")
                if ump_type == "card":
                    await self._send_card(client, msg.external_user_id, ump)
                elif ump_type == "image":
                    logger.debug("UMP image 暂不单独发送（图片已内置在 card 中）")

    async def _send_card(self, client, user_id: str, card: dict) -> None:
        """
        发送商品卡片（使用企微 news 图文消息格式）。

        card 参数包含: title, price, src(图片), url(链接)
        """
        title = card.get("title", "商品推荐")
        price = card.get("price", "")
        img_url = card.get("src", "")
        link_url = card.get("url", "")

        # 构建描述：标题 + 价格
        description = f"¥{price}" if price else title

        result = await client.send_news(
            user_id=user_id,
            title=title,
            description=description,
            url=link_url or "",
            pic_url=img_url,
        )
        if result.get("errcode") != 0:
            logger.error(
                "商品卡片发送失败 user=%s err=%s",
                user_id,
                result.get("errmsg"),
            )

    def _message_log_context(self, msg: WeComIncomingMessage) -> str:
        return f"user={msg.external_user_id} msg_id={msg.channel_msg_id}"


# ── 全局单例 ────────────────────────────────────────────────
wecom_queue = WeComMessageQueue()
