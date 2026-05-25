import pytest

from app.models.content_change_history import ChangeStatus
from app.repository.content_change_history_repo import ContentChangeHistoryRepo
from app.repository.knowledge_repo import KnowledgeRepo
from app.service.knowledge_admin import KnowledgeAdminService
from app.service.knowledge_sync import KnowledgeSyncService
from app.models.knowledge_admin import KnowledgeAdminDraft


class _FakeModel:
    def encode(self, texts, normalize_embeddings=True):  # noqa: ARG002
        return [[0.1, 0.2, 0.3] for _ in texts]


class _FakeEmbeddingSearcher:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.upserted: list[str] = []
        self.deleted: list[str] = []

    def _get_model(self):
        return _FakeModel()

    async def upsert_one(self, key: str, vector: list[float]) -> None:  # noqa: ARG002
        if self.should_fail:
            raise RuntimeError("向量服务不可用")
        self.upserted.append(key)

    async def delete_one(self, key: str) -> None:
        if self.should_fail:
            raise RuntimeError("向量服务不可用")
        self.deleted.append(key)


@pytest.mark.asyncio
async def test_create_entry_syncs_vector_and_writes_history(db) -> None:
    repo = KnowledgeRepo(db)
    history_repo = ContentChangeHistoryRepo(db)
    embedding = _FakeEmbeddingSearcher()
    service = KnowledgeAdminService(
        knowledge_repo=repo,
        history_repo=history_repo,
        sync_service=KnowledgeSyncService(repo, history_repo, embedding),
    )

    entry = await service.create_entry(
        KnowledgeAdminDraft(
            title="配送多久能到",
            content="主城区当日配送，偏远地区以客服确认时间为准。",
            content_type="faq",
            keywords="配送 到达",
            priority=60,
            is_active=True,
        ),
        operator="admin",
    )

    assert entry.vector_sync_status == "success"
    assert embedding.upserted == [f"kb_{entry.id}"]
    history = await history_repo.list_for_entity(entity_type="knowledge", entity_key=f"kb_{entry.id}")
    assert len(history) == 1
    assert history[0].status == ChangeStatus.SUCCESS


@pytest.mark.asyncio
async def test_create_entry_marks_failed_when_vector_sync_errors(db) -> None:
    repo = KnowledgeRepo(db)
    history_repo = ContentChangeHistoryRepo(db)
    embedding = _FakeEmbeddingSearcher(should_fail=True)
    service = KnowledgeAdminService(
        knowledge_repo=repo,
        history_repo=history_repo,
        sync_service=KnowledgeSyncService(repo, history_repo, embedding),
    )

    entry = await service.create_entry(
        KnowledgeAdminDraft(
            title="改期规则",
            content="至少提前一天联系门店处理。",
            content_type="rule",
            keywords="改期",
            priority=50,
            is_active=True,
        ),
        operator="admin",
    )

    assert entry.vector_sync_status == "failed"
    assert entry.vector_sync_error == "向量服务不可用"
    history = await history_repo.list_for_entity(entity_type="knowledge", entity_key=f"kb_{entry.id}")
    assert len(history) == 1
    assert history[0].status == ChangeStatus.FAILED
