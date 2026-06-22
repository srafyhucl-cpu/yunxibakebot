"""Agent 化 P2 离线质检测试。"""

import asyncio
import json
from types import SimpleNamespace

import aiosqlite
import pytest

from app.exceptions import LLMError
from app.models.conversation_review import ConversationReview
from app.models.message import Message, MessageRole
from app.models.session_scope import SessionScope, mark_handoff_started
from app.repository.conversation_review_repo import ConversationReviewRepo
from app.repository.customer_profile_repo import CustomerProfileRepo
from app.repository.knowledge_gap_repo import KnowledgeGapRepo
from app.repository.message_repo import MessageRepo
from app.repository.offline_session_repo import OfflineSessionRepo
from app.repository.session_repo import SessionRepo
from app.service.offline import agent_qa_review as qa_review_module
from app.service.offline import agent_knowledge_gap as knowledge_gap_module
from app.service.offline import agent_memory as memory_module
from app.service.offline import scheduler as scheduler_module
from app.service.offline.agent_knowledge_gap import KnowledgeGapAgent
from app.service.offline.agent_memory import MemoryAgent
from app.service.offline.agent_qa_review import QaReviewAgent
from app.service.offline.orchestrator import OfflineReviewOrchestrator
from app.service.offline.scheduler import OfflineReviewScheduler, _is_night_window


async def test_session_repo_lists_unreviewed_closed_and_transfer_sessions(
    db: aiosqlite.Connection,
) -> None:
    """候选会话只包含未质检的已结束或转人工会话。"""
    await _insert_session(db, "active-1", "active")
    await _insert_session(db, "closed-1", "closed")
    await _insert_session(db, "transfer-1", "transfer_pending")
    await _insert_session(db, "reviewed-1", "closed")
    await db.execute(
        "INSERT INTO conversation_reviews "
        "(session_id, quality_score, issues_json, reviewer_model, reviewed_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("reviewed-1", 90, "[]", "mimo", "2026-06-09 10:00:00"),
    )
    await db.commit()

    sessions = await SessionRepo(db).list_review_candidates()

    assert {session.id for session in sessions} == {"closed-1", "transfer-1"}


async def test_qa_review_agent_writes_conversation_review(
    db: aiosqlite.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """质检 Agent 应调用 LLM 并把结构化结果落库。"""
    await _insert_session(db, "session-1", "closed")
    await MessageRepo(db).save(
        Message(
            id="msg-1",
            session_id="session-1",
            role=MessageRole.USER,
            content="草莓蛋糕多少钱？",
        )
    )

    async def fake_llm_chat(*_args: object, **_kwargs: object) -> object:
        message = SimpleNamespace(
            content='{"quality_score": 82, "issues": ["价格回答需核对"]}'
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(qa_review_module, "llm_chat", fake_llm_chat)
    agent = _build_agent(db)

    reviews = await agent.run()
    stored = await ConversationReviewRepo(db).list_by_session("session-1")

    assert [review.quality_score for review in reviews] == [82]
    assert stored[0].issues_json == '["价格回答需核对"]'


async def test_qa_review_agent_isolates_single_session_llm_error(
    db: aiosqlite.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """单个会话质检失败时不应写入脏数据，也不影响整轮返回。"""
    await _insert_session(db, "session-err", "closed")
    await MessageRepo(db).save(
        Message(
            id="msg-err",
            session_id="session-err",
            role=MessageRole.USER,
            content="这个能不能吃？",
        )
    )

    async def fake_llm_chat(*_args: object, **_kwargs: object) -> object:
        raise LLMError("boom")

    monkeypatch.setattr(qa_review_module, "llm_chat", fake_llm_chat)
    agent = _build_agent(db)

    reviews = await agent.run()
    stored = await ConversationReviewRepo(db).list_by_session("session-err")

    assert reviews == []
    assert stored == []


async def test_orchestrator_isolates_agent_failure() -> None:
    """编排器应捕获单 Agent 异常并返回空结果。"""

    class BrokenAgent:
        async def run(self) -> list:
            raise RuntimeError("failed")

    orchestrator = OfflineReviewOrchestrator(BrokenAgent())  # type: ignore[arg-type]

    assert await orchestrator.run_once() == []


async def test_knowledge_gap_agent_upserts_open_gap_without_duplicate_session(
    db: aiosqlite.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """知识缺口 Agent 应写入 open 建议，同一来源会话重复运行不重复计数。"""
    await _insert_session(db, "gap-session-1", "closed")
    await MessageRepo(db).save(
        Message(
            id="gap-msg-1",
            session_id="gap-session-1",
            role=MessageRole.USER,
            content="生日蜡烛收费吗？",
        )
    )

    async def fake_llm_chat(*_args: object, **_kwargs: object) -> object:
        message = SimpleNamespace(
            content='{"question_norm":"生日蜡烛收费吗","proposed_answer":"需人工审核后补充收费规则。"}'
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(knowledge_gap_module, "llm_chat", fake_llm_chat)
    agent = KnowledgeGapAgent(MessageRepo(db), KnowledgeGapRepo(db))
    reviews = [
        ConversationReview(
            id=1,
            session_id="gap-session-1",
            quality_score=30,
            issues_json='["答漏"]',
        )
    ]

    first = await agent.run(reviews)
    second = await agent.run(reviews)
    open_gaps = await KnowledgeGapRepo(db).list_open_top()

    assert first[0].question_norm == "生日蜡烛收费吗"
    assert second[0].frequency == 1
    assert open_gaps[0].frequency == 1
    assert json.loads(open_gaps[0].related_sessions_json) == ["gap-session-1"]


async def test_memory_agent_upserts_profile_and_skips_current_profile(
    db: aiosqlite.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """记忆固化 Agent 应写入画像，画像时间追上会话后不再重复处理。"""
    await _insert_session(db, "memory-session-1", "closed")
    await db.execute(
        "UPDATE sessions SET updated_at = ? WHERE id = ?",
        ("2026-06-09 12:00:00", "memory-session-1"),
    )
    await db.commit()
    await MessageRepo(db).save(
        Message(
            id="memory-msg-1",
            session_id="memory-session-1",
            role=MessageRole.USER,
            content="我叫小林，喜欢少糖，坚果过敏。",
        )
    )

    async def fake_llm_chat(*_args: object, **_kwargs: object) -> object:
        message = SimpleNamespace(
            content=(
                '{"display_name":"小林","preferences":{"sweetness":"less"},'
                '"order_summary":{},"allergens":["坚果"],"consent_status":"unknown"}'
            )
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(memory_module, "llm_chat", fake_llm_chat)
    agent = MemoryAgent(
        OfflineSessionRepo(db), MessageRepo(db), CustomerProfileRepo(db)
    )

    profiles = await agent.run()
    second_run = await agent.run()
    profile = await CustomerProfileRepo(db).get("youzan", "user-memory-session-1")

    assert len(profiles) == 1
    assert second_run == []
    assert profile is not None
    assert profile.display_name == "小林"
    assert profile.preferences_json == '{"sweetness": "less"}'
    assert profile.allergens_json == '["坚果"]'


async def test_orchestrator_runs_p3_agents_after_qa() -> None:
    """编排器应在质检后串联知识缺口与记忆固化 Agent。"""

    class QaAgent:
        async def run(self) -> list[ConversationReview]:
            return [ConversationReview(id=1, session_id="s1", quality_score=20)]

    class GapAgent:
        def __init__(self) -> None:
            self.received: list[ConversationReview] = []

        async def run(self, reviews: list[ConversationReview]) -> list:
            self.received = reviews
            return []

    class MemoryAgentStub:
        def __init__(self) -> None:
            self.called = False

        async def run(self) -> list:
            self.called = True
            return []

    gap_agent = GapAgent()
    memory_agent = MemoryAgentStub()
    orchestrator = OfflineReviewOrchestrator(
        QaAgent(),  # type: ignore[arg-type]
        gap_agent,  # type: ignore[arg-type]
        memory_agent,  # type: ignore[arg-type]
    )

    reviews = await orchestrator.run_once()

    assert reviews[0].session_id == "s1"
    assert gap_agent.received == reviews
    assert memory_agent.called is True


async def test_scheduler_runs_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """调度器应能启动、触发一轮并优雅停止。"""

    class FakeOrchestrator:
        def __init__(self) -> None:
            self.calls = 0

        async def run_once(self) -> list:
            self.calls += 1
            return []

    orchestrator = FakeOrchestrator()
    scheduler = OfflineReviewScheduler(
        orchestrator,
        interval_hours=0.01,
    )

    monkeypatch.setattr(
        scheduler_module, "_is_night_window", lambda *_args, **_kwargs: True
    )
    scheduler.start()
    await asyncio.sleep(0.01)
    await scheduler.stop()

    assert scheduler.get_last_summary().ran is True
    assert orchestrator.calls >= 1


def test_night_window_wraps_across_midnight() -> None:
    assert _is_night_window(22, 6, now_hour=23) is True
    assert _is_night_window(22, 6, now_hour=2) is True
    assert _is_night_window(22, 6, now_hour=12) is False
    assert _is_night_window(8, 18, now_hour=9) is True
    assert _is_night_window(8, 18, now_hour=20) is False


async def test_memory_agent_records_partial_handoff_scope(
    db: aiosqlite.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """转人工但人工消息不可见时，画像证据应标记为 partial。"""
    await _insert_session(db, "memory-scope-1", "closed")
    await db.execute(
        "UPDATE sessions SET updated_at = ?, extra_info = ? WHERE id = ?",
        (
            "2026-06-09 13:00:00",
            mark_handoff_started("{}"),
            "memory-scope-1",
        ),
    )
    await db.commit()
    await MessageRepo(db).save(
        Message(
            id="memory-scope-msg-1",
            session_id="memory-scope-1",
            role=MessageRole.USER,
            content="想看看草莓蛋糕。",
        )
    )

    captured: dict[str, object] = {}

    async def fake_llm_chat(*args: object, **_kwargs: object) -> object:
        captured["messages"] = args[0]
        message = SimpleNamespace(
            content=(
                '{"display_name":"","preferences":{},'
                '"order_summary":{},"allergens":[],"consent_status":"unknown"}'
            )
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(memory_module, "llm_chat", fake_llm_chat)
    agent = MemoryAgent(
        OfflineSessionRepo(db), MessageRepo(db), CustomerProfileRepo(db)
    )

    profiles = await agent.run()
    profile = await CustomerProfileRepo(db).get("youzan", "user-memory-scope-1")

    assert len(profiles) == 1
    assert profile is not None
    assert SessionScope.BOT_THEN_HANDOFF_PARTIAL.value in str(captured["messages"])
    evidence = json.loads(profile.source_evidence_json)
    assert evidence["session_scope"] == SessionScope.BOT_THEN_HANDOFF_PARTIAL.value
    assert evidence["handoff_occurred"] is True
    assert evidence["human_messages_available"] is False


def _build_agent(db: aiosqlite.Connection) -> QaReviewAgent:
    return QaReviewAgent(
        session_repo=SessionRepo(db),
        message_repo=MessageRepo(db),
        review_repo=ConversationReviewRepo(db),
        max_sessions=10,
        reviewer_model="mimo-test",
    )


async def _insert_session(
    db: aiosqlite.Connection,
    session_id: str,
    status: str,
) -> None:
    await db.execute(
        "INSERT INTO sessions (id, channel, user_id, status) VALUES (?, ?, ?, ?)",
        (session_id, "youzan", f"user-{session_id}", status),
    )
    await db.commit()
