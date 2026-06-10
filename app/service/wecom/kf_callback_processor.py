"""微信客服回调业务处理器。"""

import time
from dataclasses import dataclass
from typing import Protocol

from app.logger import setup_logger
from app.service.wecom.kf_message_queue import KfIncomingMessage, kf_queue
from app.service.wecom.kf_servicer_sync import (
    SyncedServicerMessage,
    save_servicer_messages,
)

logger = setup_logger()

STALE_MESSAGE_MAX_DELAY_SECONDS = 120
CUSTOMER_ORIGIN = 3
SYSTEM_ORIGIN = 4
SERVICER_ORIGIN = 5


class KfClientProtocol(Protocol):
    async def sync_kf_messages(self, kf_token: str) -> dict:
        """拉取微信客服消息。"""

    async def ensure_kf_session_active(self, external_userid: str) -> bool:
        """确认微信客服会话可回复。"""


class KfQueueProtocol(Protocol):
    async def enqueue(self, msg: KfIncomingMessage) -> bool:
        """入队微信客服消息。"""


@dataclass(frozen=True)
class QueuedNontextMessage:
    """等待入队的非文本客服消息。"""

    external_userid: str
    open_kfid: str
    msgtype: str
    media_id: str
    msg_id: str


class KfCallbackProcessor:
    """处理微信客服事件通知，并将可回复消息投递到客服队列。"""

    def __init__(
        self,
        client: KfClientProtocol,
        queue: KfQueueProtocol = kf_queue,
    ) -> None:
        self._client = client
        self._queue = queue

    async def handle_callback(self, msg: dict) -> None:
        """处理微信客服回调通知。"""
        kf_token = msg.get("Token", "")
        open_kfid = msg.get("OpenKfId", "")

        if not kf_token:
            logger.warning("客服回调事件中无 Token 字段，忽略")
            return

        logger.info(
            "收到客服回调通知 open_kfid=%s token=%s...", open_kfid, kf_token[:8]
        )
        try:
            sync_result = await self._client.sync_kf_messages(kf_token=kf_token)
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

        msg_list = sync_result.get("msg_list", [])
        user_messages, nontext_messages, servicer_messages = self._collect_messages(
            msg_list,
            open_kfid,
        )
        synced_count = await save_servicer_messages(servicer_messages)
        enqueued_count = await self._enqueue_messages(
            open_kfid,
            user_messages,
            nontext_messages,
        )
        logger.info(
            "客服回调处理完成 total=%d queued=%d human_synced=%d",
            len(msg_list),
            enqueued_count,
            synced_count,
        )

    def _collect_messages(
        self,
        msg_list: list[dict],
        open_kfid: str,
    ) -> tuple[
        dict[str, dict[str, dict]],
        list[QueuedNontextMessage],
        list[SyncedServicerMessage],
    ]:
        user_messages: dict[str, dict[str, dict]] = {}
        nontext_processed_users: set[str] = set()
        nontext_messages: list[QueuedNontextMessage] = []
        servicer_messages: list[SyncedServicerMessage] = []

        for item in msg_list:
            if self._is_stale_message(item):
                continue

            if self._is_servicer_message(item):
                servicer_message = self._build_servicer_message(item)
                if servicer_message is not None:
                    servicer_messages.append(servicer_message)
                continue

            if not self._is_customer_message(item):
                continue

            external_userid = item.get("external_userid", "")
            msgtype = item.get("msgtype", "")
            if msgtype == "text":
                self._collect_text_message(user_messages, external_userid, item)
            else:
                self._collect_nontext_message(
                    nontext_processed_users,
                    nontext_messages,
                    external_userid,
                    open_kfid,
                    item,
                )

        return user_messages, nontext_messages, servicer_messages

    def _is_stale_message(self, item: dict) -> bool:
        send_time = item.get("send_time", 0)
        if send_time <= 0:
            return False

        delay = int(time.time()) - send_time
        if delay <= STALE_MESSAGE_MAX_DELAY_SECONDS:
            return False

        logger.info(
            "跳过微信客服过期的历史重推消息 msg_id=%s send_time=%d delay=%ds",
            item.get("msgid", ""),
            send_time,
            delay,
        )
        return True

    def _is_customer_message(self, item: dict) -> bool:
        origin = item.get("origin", 0)
        msgtype = item.get("msgtype", "")
        item_msgid = item.get("msgid", "")
        if origin == CUSTOMER_ORIGIN:
            return True
        if origin == SYSTEM_ORIGIN:
            logger.debug(
                "客服系统事件 type=%s msg_id=%s",
                item.get("event_type", msgtype),
                item_msgid,
            )
        return False

    def _is_servicer_message(self, item: dict) -> bool:
        return item.get("origin", 0) == SERVICER_ORIGIN

    def _build_servicer_message(self, item: dict) -> SyncedServicerMessage | None:
        external_userid = item.get("external_userid", "")
        msg_id = item.get("msgid", "")
        msgtype = item.get("msgtype", "")
        if not external_userid or not msg_id:
            return None

        if msgtype == "text":
            content = item.get("text", {}).get("content", "").strip()
        else:
            content = f"[{msgtype}消息]"
        if not content:
            return None

        return SyncedServicerMessage(
            external_userid=external_userid,
            content=f"[人工客服] {content}",
            msg_id=msg_id,
        )

    def _collect_text_message(
        self,
        user_messages: dict[str, dict[str, dict]],
        external_userid: str,
        item: dict,
    ) -> None:
        text_content = item.get("text", {}).get("content", "")
        item_msgid = item.get("msgid", "")
        if not text_content.strip():
            return

        user_dict = user_messages.setdefault(external_userid, {})
        if item_msgid in user_dict:
            logger.debug(
                "重复消息已跳过 user=%s msg_id=%s", external_userid, item_msgid
            )
            return

        user_dict[item_msgid] = item
        logger.info(
            "收到客服文本消息 user=%s content=%s msg_id=%s",
            external_userid,
            text_content[:50],
            item_msgid,
        )

    def _collect_nontext_message(
        self,
        nontext_processed_users: set[str],
        nontext_messages: list[QueuedNontextMessage],
        external_userid: str,
        open_kfid: str,
        item: dict,
    ) -> None:
        item_msgid = item.get("msgid", "")
        msgtype = item.get("msgtype", "")
        if external_userid in nontext_processed_users:
            logger.debug(
                "重复非文本消息已跳过 user=%s msg_id=%s",
                external_userid,
                item_msgid,
            )
            return

        nontext_processed_users.add(external_userid)
        media_id = self._extract_media_id(item)
        logger.info(
            "收到客服非文本消息 type=%s user=%s media_id=%s msg_id=%s",
            msgtype,
            external_userid,
            media_id[:20] if media_id else "(空)",
            item_msgid,
        )
        nontext_messages.append(
            QueuedNontextMessage(
                external_userid=external_userid,
                open_kfid=open_kfid,
                msgtype=msgtype,
                media_id=media_id,
                msg_id=item_msgid,
            )
        )

    def _extract_media_id(self, item: dict) -> str:
        msgtype = item.get("msgtype", "")
        if msgtype in ("image", "voice", "video", "file"):
            return item.get(msgtype, {}).get("media_id", "")
        return ""

    async def _enqueue_messages(
        self,
        open_kfid: str,
        user_messages: dict[str, dict[str, dict]],
        nontext_messages: list[QueuedNontextMessage],
    ) -> int:
        enqueued_count = 0
        for external_userid, message_by_id in user_messages.items():
            if not await self._can_reply(external_userid, len(message_by_id)):
                continue
            for message_id, item in message_by_id.items():
                if await self._queue.enqueue(
                    KfIncomingMessage(
                        external_userid=external_userid,
                        open_kfid=open_kfid,
                        content=item["text"]["content"],
                        msg_id=message_id,
                        msgtype="text",
                    )
                ):
                    enqueued_count += 1
                else:
                    logger.warning("客服消息队列已满，丢弃 user=%s", external_userid)

        for nontext_message in nontext_messages:
            if not await self._can_reply(nontext_message.external_userid, 1):
                continue
            if await self._queue.enqueue(
                KfIncomingMessage(
                    external_userid=nontext_message.external_userid,
                    open_kfid=nontext_message.open_kfid,
                    content=f"[{nontext_message.msgtype}消息]",
                    msg_id=nontext_message.msg_id,
                    msgtype=nontext_message.msgtype,
                    media_id=nontext_message.media_id,
                )
            ):
                enqueued_count += 1
            else:
                logger.warning(
                    "客服消息队列已满，丢弃非文本消息 user=%s type=%s",
                    nontext_message.external_userid,
                    nontext_message.msgtype,
                )
        return enqueued_count

    async def _can_reply(self, external_userid: str, message_count: int) -> bool:
        can_reply = await self._client.ensure_kf_session_active(external_userid)
        if not can_reply:
            logger.info(
                "用户会话不可用，跳过 %d 条消息 user=%s",
                message_count,
                external_userid,
            )
        return can_reply
