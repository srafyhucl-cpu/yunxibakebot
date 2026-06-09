"""Agent 化 P2 离线质检测试。"""

import asyncio
from types import SimpleNamespace

import aiosqlite
import pytest

from app.exceptions import LLMError
from app.models.message import Message, MessageRole
from app.repository.conversation_review_repo import ConversationReviewRepo
from app.repository.message_repo import MessageRepo
from app.repository.session_repo import SessionRepo
from app.service.offline import agent_qa_review as qa_review_module
from app.service.offline.agent_qa_review import QaReviewAgent
from app.service.offline.orchestrator import OfflineReviewOrchestrator
from app.service.offline.scheduler import OfflineReviewScheduler


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


async def test_scheduler_runs_and_stops() -> None:
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

    scheduler.start()
    await asyncio.sleep(0.01)
    await scheduler.stop()

    assert orchestrator.calls >= 1


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
