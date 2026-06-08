from dataclasses import dataclass

import pytest

from app.models.message import Message, MessageRole
from app.models.session import Session, SessionStatus
from app.service.chat import TRANSFER_REPLY, ChatService, _build_history_text


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
