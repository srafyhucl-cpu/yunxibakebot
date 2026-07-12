"""持久 inbox 状态机测试。"""

import pytest

from app.repository.inbox_repo import InboxRepo, MAX_INBOX_ATTEMPTS


@pytest.mark.asyncio
async def test_inbox_claim_and_processed_are_idempotent(db) -> None:
    repo = InboxRepo(db)

    assert await repo.enqueue("wecom", "wecom:msg-1", '{"content":"hello"}') is True
    assert await repo.enqueue("wecom", "wecom:msg-1", '{"content":"replay"}') is False
    claimed = await repo.claim("wecom")
    assert claimed is not None
    assert claimed["message_key"] == "wecom:msg-1"
    assert claimed["attempt_count"] == 1

    await repo.mark_processed("wecom:msg-1")
    assert await repo.claim("wecom") is None
    assert await repo.count_pending("wecom") == 0


@pytest.mark.asyncio
async def test_inbox_expired_processing_lease_can_be_reclaimed(db) -> None:
    repo = InboxRepo(db)
    await repo.enqueue("wecom", "wecom:lease-1", "{}")
    first = await repo.claim("wecom", lease_seconds=-60)
    second = await repo.claim("wecom", lease_seconds=60)

    assert first is not None
    assert second is not None
    assert second["message_key"] == "wecom:lease-1"
    assert second["attempt_count"] == 2


@pytest.mark.asyncio
async def test_inbox_counts_expired_processing_as_stuck(db) -> None:
    repo = InboxRepo(db)
    await repo.enqueue("wecom", "wecom:stuck-1", "{}")
    await repo.claim("wecom", lease_seconds=-60)

    assert await repo.count_stuck("wecom") == 1


@pytest.mark.asyncio
async def test_inbox_moves_to_dead_letter_after_bounded_failures(db) -> None:
    repo = InboxRepo(db)
    await repo.enqueue("wecom", "wecom:failed-1", "{}")

    for attempt in range(MAX_INBOX_ATTEMPTS):
        claimed = await repo.claim("wecom")
        assert claimed is not None
        await repo.mark_failed("wecom:failed-1", f"failure-{attempt}")
        await db.execute(
            "UPDATE inbox_events SET next_attempt_at = '2000-01-01 00:00:00' "
            "WHERE message_key = ?",
            ("wecom:failed-1",),
        )
        await db.commit()

    assert await repo.claim("wecom") is None
    rows = await db.execute_fetchall(
        "SELECT status, attempt_count, last_error FROM inbox_events "
        "WHERE message_key = ?",
        ("wecom:failed-1",),
    )
    assert dict(rows[0]) == {
        "status": "dead_letter",
        "attempt_count": MAX_INBOX_ATTEMPTS,
        "last_error": "failure-4",
    }
