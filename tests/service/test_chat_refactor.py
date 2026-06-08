from dataclasses import dataclass
from base64 import b64encode

import pytest

from app.models.message import Message, MessageRole
from app.models.session import Session, SessionStatus
from app.service.chat import TRANSFER_REPLY, ChatService, _build_history_text
from app.service.llm.intent import IntentType


def test_build_history_text_keeps_recent_dialog_and_truncates_content() -> None:
    history = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "second"},
        {"role": "tool", "content": "tool result"},
        {"role": "user", "content": "third"},
        {"role": "assistant", "content": "A" * 100},
        {"role": "user", "content": "fourth"},
    ]

    history_text = _build_history_text(history)

    assert "system" not in history_text
    assert "tool result" not in history_text
    assert "first" not in history_text
    assert "用户：third" in history_text
    assert "AI：" + ("A" * 80) in history_text
    assert "用户：fourth" in history_text


@dataclass
class _TransferCall:
    session_id: str
    user_id: str
    reason: str
    summary: str


class _FakeTransferManager:
    def __init__(self) -> None:
        self.calls: list[_TransferCall] = []

    async def request_transfer(
        self, session_id: str, user_id: str, reason: str = "", summary: str = ""
    ) -> object:
        self.calls.append(
            _TransferCall(
                session_id=session_id,
                user_id=user_id,
                reason=reason,
                summary=summary,
            )
        )
        return object()


class _FakeSessionRepo:
    def __init__(self) -> None:
        self.updated: list[tuple[str, SessionStatus]] = []

    async def update_status(self, session_id: str, status: SessionStatus) -> None:
        self.updated.append((session_id, status))


class _FakeMessageRepo:
    def __init__(self) -> None:
        self.saved: list[Message] = []

    async def save(self, message: Message) -> None:
        self.saved.append(message)


class _FakeAnalyticsRepo:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def add_event(self, **kwargs: object) -> None:
        self.events.append(kwargs)


@pytest.mark.asyncio
async def test_handle_transfer_intent_updates_state_and_saves_reply() -> None:
    service = ChatService.__new__(ChatService)
    transfer_mgr = _FakeTransferManager()
    session_repo = _FakeSessionRepo()
    message_repo = _FakeMessageRepo()
    service._transfer_mgr = transfer_mgr
    service._session_repo = session_repo
    service._message_repo = message_repo
    session = Session(id="session-1", channel="youzan", user_id="buyer-1")

    reply = await service._handle_transfer_intent(
        session=session,
        user_id="buyer-1",
        reason="need human support",
        history_text="old dialog " * 100,
    )

    assert reply == TRANSFER_REPLY
    assert transfer_mgr.calls[0].session_id == "session-1"
    assert transfer_mgr.calls[0].user_id == "buyer-1"
    assert transfer_mgr.calls[0].reason == "need human support"
    assert len(transfer_mgr.calls[0].summary) == 200
    assert session_repo.updated == [("session-1", SessionStatus.TRANSFER_PENDING)]
    assert len(message_repo.saved) == 1
    assert message_repo.saved[0].role == MessageRole.ASSISTANT
    assert message_repo.saved[0].content == TRANSFER_REPLY


def test_postprocess_reply_removes_markdown_marks() -> None:
    service = ChatService.__new__(ChatService)

    reply = service._postprocess_reply("**hello** __ok__", user_content="normal")

    assert reply == "hello ok"


@pytest.mark.asyncio
async def test_record_reply_latency_keeps_expected_meta() -> None:
    service = ChatService.__new__(ChatService)
    analytics_repo = _FakeAnalyticsRepo()
    service._analytics_repo = analytics_repo
    session = Session(id="session-1", channel="youzan", user_id="buyer-1")

    await service._record_reply_latency(
        session=session,
        user_id="buyer-1",
        channel="youzan",
        intent=IntentType.PRODUCT_CONSULTATION,
        intent_ms=12,
        timing={"rag_ms": 34, "llm_ms": 56, "tool_rounds": 1},
        loop_ms=78,
        total_ms=90,
    )

    assert len(analytics_repo.events) == 1
    event = analytics_repo.events[0]
    assert event["session_id"] == "session-1"
    assert event["buyer_id"] == "buyer-1"
    assert event["event_type"] == "reply_latency"
    assert '"intent": "PRODUCT_CONSULTATION"' in str(event["meta_data"])
    assert '"tool_rounds": 1' in str(event["meta_data"])


def test_normalize_image_data_uri_detects_png() -> None:
    service = ChatService.__new__(ChatService)
    png_base64 = b64encode(b"\x89PNG\r\n\x1a\nfake").decode("ascii")

    data_uri = service._normalize_image_data_uri(png_base64)

    assert data_uri.startswith("data:image/png;base64,")
    assert data_uri.endswith(png_base64)


def test_apply_multimodal_image_message_replaces_last_user_message() -> None:
    service = ChatService.__new__(ChatService)
    jpeg_base64 = b64encode(b"\xff\xd8\xff\xe0fake").decode("ascii")
    messages = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "answer"},
        {"role": "user", "content": "last"},
    ]

    service._apply_multimodal_image_message(messages, jpeg_base64, "session-1")

    assert messages[0]["content"] == "first"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"][0]["type"] == "image_url"
    assert messages[2]["content"][0]["image_url"]["url"].startswith(
        "data:image/jpeg;base64,"
    )
    assert messages[2]["content"][1] == {"type": "text", "text": "last"}
