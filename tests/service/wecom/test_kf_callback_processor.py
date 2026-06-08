import time

import pytest

from app.service.wecom.kf_callback_processor import KfCallbackProcessor
from app.service.wecom.kf_message_queue import KfIncomingMessage


class FakeKfClient:
    def __init__(
        self,
        sync_result: dict,
        inactive_users: set[str] | None = None,
    ) -> None:
        self.sync_result = sync_result
        self.inactive_users = inactive_users or set()
        self.checked_users: list[str] = []

    async def sync_kf_messages(self, kf_token: str) -> dict:
        assert kf_token == "token-1"
        return self.sync_result

    async def ensure_kf_session_active(self, external_userid: str) -> bool:
        self.checked_users.append(external_userid)
        return external_userid not in self.inactive_users


class FakeKfQueue:
    def __init__(self) -> None:
        self.messages: list[KfIncomingMessage] = []

    async def enqueue(self, msg: KfIncomingMessage) -> bool:
        self.messages.append(msg)
        return True


@pytest.mark.asyncio
async def test_processor_filters_stale_and_duplicate_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = int(time.time())
    monkeypatch.setattr(time, "time", lambda: now)
    sync_result = {
        "errcode": 0,
        "msg_list": [
            {
                "origin": 3,
                "msgtype": "text",
                "msgid": "fresh-text",
                "external_userid": "user-1",
                "send_time": now,
                "text": {"content": "想订生日蛋糕"},
            },
            {
                "origin": 3,
                "msgtype": "text",
                "msgid": "fresh-text",
                "external_userid": "user-1",
                "send_time": now,
                "text": {"content": "重复消息"},
            },
            {
                "origin": 3,
                "msgtype": "text",
                "msgid": "stale-text",
                "external_userid": "user-1",
                "send_time": now - 121,
                "text": {"content": "历史消息"},
            },
            {
                "origin": 3,
                "msgtype": "image",
                "msgid": "image-1",
                "external_userid": "user-1",
                "send_time": now,
                "image": {"media_id": "media-1"},
            },
            {
                "origin": 3,
                "msgtype": "voice",
                "msgid": "voice-1",
                "external_userid": "user-1",
                "send_time": now,
                "voice": {"media_id": "media-voice"},
            },
            {
                "origin": 4,
                "msgtype": "event",
                "msgid": "system-1",
                "external_userid": "user-1",
            },
        ],
    }
    queue = FakeKfQueue()
    processor = KfCallbackProcessor(FakeKfClient(sync_result), queue)

    await processor.handle_callback({"Token": "token-1", "OpenKfId": "kf-1"})

    assert [msg.msg_id for msg in queue.messages] == ["fresh-text", "image-1"]
    assert queue.messages[0].open_kfid == "kf-1"
    assert queue.messages[0].content == "想订生日蛋糕"
    assert queue.messages[1].msgtype == "image"
    assert queue.messages[1].media_id == "media-1"


@pytest.mark.asyncio
async def test_processor_skips_messages_when_session_is_inactive() -> None:
    sync_result = {
        "errcode": 0,
        "msg_list": [
            {
                "origin": 3,
                "msgtype": "text",
                "msgid": "text-1",
                "external_userid": "user-1",
                "text": {"content": "你好"},
            }
        ],
    }
    queue = FakeKfQueue()
    client = FakeKfClient(sync_result, inactive_users={"user-1"})
    processor = KfCallbackProcessor(client, queue)

    await processor.handle_callback({"Token": "token-1", "OpenKfId": "kf-1"})

    assert queue.messages == []
    assert client.checked_users == ["user-1"]


@pytest.mark.asyncio
async def test_processor_ignores_callback_without_token() -> None:
    queue = FakeKfQueue()
    processor = KfCallbackProcessor(FakeKfClient({"errcode": 0}), queue)

    await processor.handle_callback({"OpenKfId": "kf-1"})

    assert queue.messages == []
