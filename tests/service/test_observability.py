import json

import pytest

from app.models.content_change_history import (
    ChangeAction,
    ChangeEntityType,
    ChangeStatus,
    ContentChangeHistoryCreate,
    SyncSource,
)
from app.models.youzan_webhook_event import YouzanWebhookEventCreate
from app.repository.content_change_history_repo import ContentChangeHistoryRepo
from app.repository.knowledge_repo import KnowledgeRepo
from app.repository.youzan_repo import YouzanProductRepo
from app.repository.youzan_webhook_event_repo import YouzanWebhookEventRepo
from app.service.observability import ObservabilityService


@pytest.mark.asyncio
async def test_observability_service_lists_current_history_and_webhooks(db) -> None:
    knowledge_repo = KnowledgeRepo(db)
    product_repo = YouzanProductRepo(db)
    history_repo = ContentChangeHistoryRepo(db)
    webhook_repo = YouzanWebhookEventRepo(db)

    await knowledge_repo.insert_entry(
        category="faq",
        title="配送说明",
        content="当天配送",
        keywords="配送",
        priority=5,
        sync_source=SyncSource.SEED_KNOWLEDGE,
    )
    await product_repo.upsert_product(
        item_id=10001,
        title="芒果蛋糕",
        alias="mg001",
        price_fen=9800,
        stock=12,
        image="",
        is_active=1,
        updated_at="2026-05-25 11:00:00",
        desc="新鲜芒果",
        tags="在售, 芒果",
        sync_source=SyncSource.YOUZAN_WEBHOOK,
        sync_ref="10001",
    )
    await history_repo.add(
        ContentChangeHistoryCreate(
            entity_type=ChangeEntityType.PRODUCT,
            entity_key="10001",
            category="product",
            title="芒果蛋糕",
            source=SyncSource.YOUZAN_WEBHOOK,
            source_ref="10001",
            action=ChangeAction.UPSERT,
            status=ChangeStatus.SUCCESS,
            change_summary_json=json.dumps({"price_fen": 9800}, ensure_ascii=False),
            occurred_at="2026-05-25 11:00:00",
        )
    )
    webhook_id = await webhook_repo.create_received(
        YouzanWebhookEventCreate(
            msg_id="msg-10001",
            trace_id="trace-1",
            event_type="ITEM_INFO",
            business_type="item",
            business_key="10001",
            http_status=200,
            payload_hash="hash",
            payload_summary_json=json.dumps({"item_id": 10001}, ensure_ascii=False),
        )
    )
    await webhook_repo.mark_result(
        webhook_id,
        type("Update", (), {
            "status": "failed",
            "process_stage": "item_failed",
            "business_type": "item",
            "business_key": "10001",
            "error_type": "ValueError",
            "error_message": "bad payload",
        })(),
    )

    service = ObservabilityService(
        knowledge_repo=knowledge_repo,
        product_repo=product_repo,
        history_repo=history_repo,
        webhook_repo=webhook_repo,
    )
    current_items, current_total = await service.list_current_content(view="products", keyword="芒果")
    history_items, history_total = await service.get_history(source=SyncSource.YOUZAN_WEBHOOK)
    webhook_items, webhook_total = await service.get_webhooks(status="failed")

    assert current_total == 1
    assert current_items[0]["title"] == "芒果蛋糕"
    assert history_total == 1
    assert history_items[0]["title"] == "芒果蛋糕"
    assert webhook_total == 1
    assert webhook_items[0]["error_message"] == "bad payload"
