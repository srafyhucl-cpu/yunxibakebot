from dataclasses import dataclass
from base64 import b64encode
from types import SimpleNamespace

import pytest

from app.exceptions import LLMError
from app.service import chat_ai_loop as chat_ai_loop_module
from app.service import chat_llm as chat_llm_module
from app.service import chat_llm_request as chat_llm_request_module
from app.models.message import Message, MessageRole
from app.models.session import Session, SessionStatus
from app.models.session_scope import SessionScope
from app.service.chat import TRANSFER_REPLY
from app.service.chat_ai_loop import (
    AiConversationLoopDependencies,
    AiConversationLoopRequest,
    run_ai_conversation_loop,
)
from app.service.chat_context import prepare_chat_context
from app.service.chat_intent import build_history_text
from app.service.chat_message_flow import (
    ChatMessageFlowDependencies,
    handle_transfer_intent,
)
from app.service.chat_llm import (
    LlmChoiceResult,
    LlmRequestContext,
    LlmToolLoopContext,
    complete_llm_tool_conversation,
    request_llm_choice,
    select_llm_model,
)
from app.service.chat_multimodal import (
    apply_multimodal_image_message,
    normalize_image_data_uri,
)
from app.service.chat_reply import postprocess_reply, record_reply_latency
from app.service.chat_tools import (
    ToolExecutionContext,
    parse_tool_arguments,
    process_tool_calls,
)
from app.service.chat_transfer import HumanTransferContext, request_human_transfer
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

    history_text = build_history_text(history)

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
        self.extra_updates: list[tuple[str, str]] = []

    async def update_status(self, session_id: str, status: SessionStatus) -> None:
        self.updated.append((session_id, status))

    async def update_extra(self, session_id: str, extra_info: str) -> None:
        self.extra_updates.append((session_id, extra_info))


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


class _FakeKnowledgeRetriever:
    def __init__(self) -> None:
        self.search_calls: list[tuple[str, int]] = []
        self.keyword_calls: list[tuple[str, int]] = []

    async def search(self, query: str, limit: int = 8) -> list:
        self.search_calls.append((query, limit))
        return []

    async def search_keyword_only(self, query: str, limit: int = 8) -> list:
        self.keyword_calls.append((query, limit))
        return []


@pytest.mark.asyncio
async def test_handle_transfer_intent_updates_state_and_saves_reply() -> None:
    transfer_mgr = _FakeTransferManager()
    session_repo = _FakeSessionRepo()
    message_repo = _FakeMessageRepo()
    session = Session(id="session-1", channel="youzan", user_id="buyer-1")

    async def fake_alerter(message: str) -> None:
        raise AssertionError(message)

    reply = await handle_transfer_intent(
        dependencies=ChatMessageFlowDependencies(
            session_mgr=object(),
            session_repo=session_repo,
            message_repo=message_repo,
            transfer_mgr=transfer_mgr,
            analytics_repo=object(),
            ai_loop_dependencies=AiConversationLoopDependencies(
                session_mgr=object(),
                knowledge=object(),
                transfer_mgr=transfer_mgr,
                session_repo=session_repo,
                youzan_client=object(),
                fallback_reply="fallback",
                timeout_reply="timeout",
                failure_alerter=fake_alerter,
            ),
            fallback_reply="fallback",
            transfer_reply=TRANSFER_REPLY,
        ),
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
    assert (
        SessionScope.BOT_THEN_HANDOFF_PARTIAL.value in session_repo.extra_updates[0][1]
    )
    assert len(message_repo.saved) == 1
    assert message_repo.saved[0].role == MessageRole.ASSISTANT
    assert message_repo.saved[0].content == TRANSFER_REPLY


def test_postprocess_reply_removes_markdown_marks() -> None:
    reply = postprocess_reply("**hello** __ok__", user_content="normal")

    assert reply == "hello ok"


@pytest.mark.asyncio
async def test_record_reply_latency_keeps_expected_meta() -> None:
    analytics_repo = _FakeAnalyticsRepo()
    session = Session(id="session-1", channel="youzan", user_id="buyer-1")

    await record_reply_latency(
        analytics_repo=analytics_repo,
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


@pytest.mark.asyncio
async def test_prepare_chat_context_builds_system_message_and_preserves_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    knowledge = _FakeKnowledgeRetriever()
    history = [{"role": "user", "content": "hello"}]

    async def fake_rewrite_query(user_query: str, history: str = "") -> str:
        return f"rewritten:{user_query}:{history}"

    monkeypatch.setattr(
        "app.service.chat_context.rewrite_query",
        fake_rewrite_query,
    )

    chat_context = await prepare_chat_context(
        knowledge=knowledge,
        user_query="cake",
        history_text="old",
        intent=IntentType.PRODUCT_CONSULTATION,
        history=history,
    )

    assert knowledge.search_calls == [("rewritten:cake:old", 8)]
    assert chat_context.messages[0]["role"] == "system"
    assert chat_context.messages[1:] == history
    assert isinstance(chat_context.rag_ms, int)


def test_normalize_image_data_uri_detects_png() -> None:
    png_base64 = b64encode(b"\x89PNG\r\n\x1a\nfake").decode("ascii")

    data_uri = normalize_image_data_uri(png_base64)

    assert data_uri.startswith("data:image/png;base64,")
    assert data_uri.endswith(png_base64)


def test_apply_multimodal_image_message_replaces_last_user_message() -> None:
    jpeg_base64 = b64encode(b"\xff\xd8\xff\xe0fake").decode("ascii")
    messages = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "answer"},
        {"role": "user", "content": "last"},
    ]

    apply_multimodal_image_message(messages, jpeg_base64, "session-1")

    assert messages[0]["content"] == "first"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"][0]["type"] == "image_url"
    assert messages[2]["content"][0]["image_url"]["url"].startswith(
        "data:image/jpeg;base64,"
    )
    assert messages[2]["content"][1] == {"type": "text", "text": "last"}


def test_select_llm_model_uses_default_for_text() -> None:
    assert select_llm_model(has_image=False) == ""


def test_select_llm_model_uses_vision_and_chat_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        chat_llm_request_module.settings, "MIMO_VISION_MODEL", "vision-model"
    )
    monkeypatch.setattr(
        chat_llm_request_module.settings, "MIMO_CHAT_MODEL", "chat-model"
    )

    assert select_llm_model(has_image=True) == "vision-model"

    monkeypatch.setattr(chat_llm_request_module.settings, "MIMO_VISION_MODEL", "")
    assert select_llm_model(has_image=True) == "chat-model"


@pytest.mark.asyncio
async def test_run_ai_conversation_loop_prepares_messages_and_invokes_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    session = Session(id="session-1", channel="youzan", user_id="buyer-1")
    messages = [{"role": "user", "content": "hello"}]

    async def fake_prepare_ai_conversation_messages(**kwargs: object) -> tuple:
        captured["prepare_kwargs"] = kwargs
        return messages, "prepared history"

    async def fake_complete_llm_tool_conversation(context: LlmToolLoopContext) -> str:
        captured["llm_context"] = context
        return "reply"

    async def fake_alerter(message: str) -> None:
        captured["alert"] = message

    monkeypatch.setattr(
        chat_ai_loop_module,
        "prepare_ai_conversation_messages",
        fake_prepare_ai_conversation_messages,
    )
    monkeypatch.setattr(
        chat_ai_loop_module,
        "complete_llm_tool_conversation",
        fake_complete_llm_tool_conversation,
    )

    reply = await run_ai_conversation_loop(
        AiConversationLoopDependencies(
            session_mgr=object(),
            knowledge=object(),
            transfer_mgr=object(),
            session_repo=object(),
            youzan_client=object(),
            fallback_reply="fallback",
            timeout_reply="timeout",
            failure_alerter=fake_alerter,
        ),
        AiConversationLoopRequest(
            session=session,
            user_query="cake",
            intent=IntentType.PRODUCT_CONSULTATION,
            timing={},
            history=[],
            history_text="old",
            image_base64="image",
        ),
    )

    assert reply == "reply"
    assert captured["prepare_kwargs"]["session"] is session
    llm_context = captured["llm_context"]
    assert isinstance(llm_context, LlmToolLoopContext)
    assert llm_context.messages == messages
    assert llm_context.has_image is True
    assert llm_context.tool_context.history_text == "prepared history"
    assert llm_context.tool_context.session is session


@pytest.mark.asyncio
async def test_request_llm_choice_records_latency_and_uses_selected_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_llm_chat(
        messages: list[dict], tools: list[dict], model: str
    ) -> object:
        captured["messages"] = messages
        captured["tools"] = tools
        captured["model"] = model
        message = SimpleNamespace(content="ok")
        choice = SimpleNamespace(message=message, finish_reason="stop")
        return SimpleNamespace(choices=[choice])

    async def fake_alerter(message: str) -> None:
        captured["alert"] = message

    monkeypatch.setattr(chat_llm_request_module, "llm_chat", fake_llm_chat)
    monkeypatch.setattr(
        chat_llm_request_module.settings, "MIMO_VISION_MODEL", "vision-model"
    )
    timing: dict[str, int] = {}
    messages = [{"role": "user", "content": "hello"}]

    result = await request_llm_choice(
        LlmRequestContext(
            messages=messages,
            timing=timing,
            first_llm_started_at=None,
            has_image=True,
            fallback_reply="fallback",
            failure_alerter=fake_alerter,
        )
    )

    assert captured["messages"] == messages
    assert captured["model"] == "vision-model"
    assert result.message.content == "ok"
    assert result.fallback_reply is None
    assert isinstance(timing["llm_ms"], int)


@pytest.mark.asyncio
async def test_request_llm_choice_returns_fallback_on_llm_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alerts: list[str] = []

    async def fake_llm_chat(*args: object, **kwargs: object) -> object:
        raise LLMError("boom")

    async def fake_alerter(message: str) -> None:
        alerts.append(message)

    monkeypatch.setattr(chat_llm_request_module, "llm_chat", fake_llm_chat)

    result = await request_llm_choice(
        LlmRequestContext(
            messages=[{"role": "user", "content": "hello"}],
            timing={},
            first_llm_started_at=1.0,
            has_image=False,
            fallback_reply="fallback",
            failure_alerter=fake_alerter,
        )
    )

    assert result.choice is None
    assert result.message is None
    assert result.fallback_reply == "fallback"
    assert result.first_llm_started_at == 1.0
    assert alerts == ["LLMError: chat.py handle_message 返回兜底回复"]


@pytest.mark.asyncio
async def test_complete_llm_tool_conversation_runs_tool_round_then_returns_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool_call = SimpleNamespace(
        id="tool-1",
        function=SimpleNamespace(
            name="search_knowledge", arguments='{"query": "cake"}'
        ),
    )
    requested_rounds: list[list[dict]] = []
    processed_tool_calls: list[list] = []

    async def fake_request_llm_choice(context: LlmRequestContext) -> LlmChoiceResult:
        messages = context.messages
        requested_rounds.append(messages)
        if len(requested_rounds) == 1:
            message = SimpleNamespace(content=None, tool_calls=[tool_call])
            choice = SimpleNamespace(message=message, finish_reason="tool_calls")
        else:
            message = SimpleNamespace(content="done", tool_calls=[])
            choice = SimpleNamespace(message=message, finish_reason="stop")
        return LlmChoiceResult(
            choice=choice,
            message=message,
            first_llm_started_at=1.0,
        )

    async def fake_process_tool_calls(
        tool_calls: list,
        messages: list[dict],
        context: ToolExecutionContext,
    ) -> None:
        processed_tool_calls.append(tool_calls)
        messages.append({"role": "tool", "content": "tool result"})

    async def fake_alerter(message: str) -> None:
        raise AssertionError(message)

    monkeypatch.setattr(chat_llm_module, "request_llm_choice", fake_request_llm_choice)
    monkeypatch.setattr(chat_llm_module, "process_tool_calls", fake_process_tool_calls)
    timing: dict[str, int] = {}
    messages = [{"role": "user", "content": "hello"}]

    reply = await complete_llm_tool_conversation(
        LlmToolLoopContext(
            messages=messages,
            timing=timing,
            has_image=False,
            fallback_reply="fallback",
            timeout_reply="timeout",
            failure_alerter=fake_alerter,
            tool_context=ToolExecutionContext(
                session=Session(id="session-1", channel="youzan", user_id="buyer-1"),
                history_text="old",
                transfer_mgr=object(),
                session_repo=object(),
                knowledge=object(),
                youzan_client=object(),
            ),
        )
    )

    assert reply == "done"
    assert len(requested_rounds) == 2
    assert processed_tool_calls == [[tool_call]]
    assert messages[-1] == {"role": "tool", "content": "tool result"}
    assert timing["tool_rounds"] == 1


def test_parse_tool_arguments_rejects_invalid_json() -> None:
    assert parse_tool_arguments("search_knowledge", '{"query": "cake"}') == {
        "query": "cake"
    }
    assert parse_tool_arguments("search_knowledge", "{bad-json") == {}
    assert parse_tool_arguments("search_knowledge", '["not", "object"]') == {}


@pytest.mark.asyncio
async def test_process_tool_calls_handles_transfer_and_appends_result() -> None:
    transfer_mgr = _FakeTransferManager()
    session_repo = _FakeSessionRepo()
    session = Session(id="session-1", channel="youzan", user_id="buyer-1")
    messages: list[dict] = []
    tool_call = SimpleNamespace(
        id="tool-1",
        function=SimpleNamespace(
            name="transfer_to_human",
            arguments='{"reason": "need staff"}',
        ),
    )

    await process_tool_calls(
        [tool_call],
        messages,
        ToolExecutionContext(
            session=session,
            history_text="old dialog " * 100,
            transfer_mgr=transfer_mgr,
            session_repo=session_repo,
            knowledge=object(),
            youzan_client=object(),
        ),
    )

    assert transfer_mgr.calls[0].reason == "need staff"
    assert session_repo.updated == [("session-1", SessionStatus.TRANSFER_PENDING)]
    assert messages[0]["tool_calls"][0]["function"]["name"] == "transfer_to_human"
    assert messages[1]["role"] == "tool"
    assert messages[1]["tool_call_id"] == "tool-1"
    assert '"status": "success"' in messages[1]["content"]


@pytest.mark.asyncio
async def test_request_human_transfer_updates_state_and_truncates_summary() -> None:
    transfer_mgr = _FakeTransferManager()
    session_repo = _FakeSessionRepo()
    session = Session(id="session-1", channel="youzan", user_id="buyer-1")

    created = await request_human_transfer(
        HumanTransferContext(
            session=session,
            user_id="buyer-1",
            reason="need staff",
            history_text="old dialog " * 100,
            transfer_mgr=transfer_mgr,
            session_repo=session_repo,
        )
    )

    assert created is True
    assert transfer_mgr.calls[0].session_id == "session-1"
    assert transfer_mgr.calls[0].user_id == "buyer-1"
    assert transfer_mgr.calls[0].reason == "need staff"
    assert len(transfer_mgr.calls[0].summary) == 200
    assert session_repo.updated == [("session-1", SessionStatus.TRANSFER_PENDING)]
    assert (
        SessionScope.BOT_THEN_HANDOFF_PARTIAL.value in session_repo.extra_updates[0][1]
    )
