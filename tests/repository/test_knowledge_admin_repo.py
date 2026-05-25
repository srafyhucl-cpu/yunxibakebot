import pytest

from app.repository.knowledge_repo import KnowledgeRepo


@pytest.mark.asyncio
async def test_create_admin_entry_defaults_vector_pending(db) -> None:
    repo = KnowledgeRepo(db)
    entry_id = await repo.create_admin_entry(
        category="faq",
        content_type="faq",
        title="配送怎么收费",
        content="满额包邮，偏远地区另算。",
        keywords="配送 运费",
        priority=50,
        is_active=True,
        content_origin="admin_console",
        created_by="admin",
        updated_by="admin",
        suggested_category="faq",
        suggest_reason="疑问句更像 FAQ",
        sync_source="admin_manual",
    )

    entry = await repo.get_by_id(entry_id)
    assert entry is not None
    assert entry.content_type == "faq"
    assert entry.vector_sync_status == "pending"
    assert entry.content_origin == "admin_console"


@pytest.mark.asyncio
async def test_mark_vector_sync_status_updates_error_and_retry(db) -> None:
    repo = KnowledgeRepo(db)
    entry_id = await repo.create_admin_entry(
        category="policy",
        content_type="rule",
        title="改期规则",
        content="需提前一天联系门店。",
        keywords="改期",
        priority=40,
        is_active=True,
        content_origin="admin_console",
        created_by="admin",
        updated_by="admin",
        suggested_category="rule",
        suggest_reason="规则类说明",
        sync_source="admin_manual",
    )

    await repo.mark_vector_sync_status(
        entry_id,
        status="failed",
        error_message="向量服务不可用",
        retry_increment=True,
    )
    entry = await repo.get_by_id(entry_id)
    assert entry is not None
    assert entry.vector_sync_status == "failed"
    assert entry.vector_sync_error == "向量服务不可用"
    assert entry.vector_sync_retry_count == 1
