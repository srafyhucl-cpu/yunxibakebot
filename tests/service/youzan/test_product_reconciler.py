from __future__ import annotations

from typing import Any

from app.models.content_change_history import ContentChangeHistoryCreate
from app.service.youzan.product_reconciler import ProductReconcileService


class FakeYouzanClient:
    def __init__(
        self,
        onsale_ids: set[int],
        product_payloads: dict[int, dict[str, Any]] | None = None,
    ) -> None:
        self._onsale_ids = onsale_ids
        self._product_payloads = product_payloads or {}
        self.requested_product_ids: list[int] = []

    async def list_onsale_item_ids(self) -> set[int]:
        return self._onsale_ids

    async def get_product(self, item_id: int) -> dict[str, Any]:
        self.requested_product_ids.append(item_id)
        if item_id not in self._product_payloads:
            raise RuntimeError("product missing")
        return self._product_payloads[item_id]


class FakeProductRepo:
    def __init__(self, active_ids: list[int], all_ids: list[int]) -> None:
        self._active_ids = active_ids
        self._all_ids = all_ids
        self.deleted: list[tuple[int, str, str, str]] = []
        self.sold_updates: dict[int, tuple[int, str]] = {}

    async def list_active_item_ids(self) -> list[int]:
        return self._active_ids

    async def list_all_item_ids(self) -> list[int]:
        return self._all_ids

    async def delete_product(
        self,
        item_id: int,
        event_time: str,
        *,
        sync_source: str,
        sync_ref: str,
    ) -> str:
        self.deleted.append((item_id, event_time, sync_source, sync_ref))
        return "deactivated"

    async def bulk_update_sold_and_no(
        self,
        sold_num_map: dict[int, tuple[int, str]],
    ) -> int:
        self.sold_updates = sold_num_map
        return len(sold_num_map)


class FakeHistoryRepo:
    def __init__(self) -> None:
        self.records: list[ContentChangeHistoryCreate] = []

    async def add(self, record: ContentChangeHistoryCreate) -> None:
        self.records.append(record)


class FakeKnowledgeProductRepo:
    def __init__(self) -> None:
        self.deleted_item_ids: list[str] = []

    async def delete_product_knowledge(
        self,
        item_id: str,
        *,
        sync_source: str,
        sync_ref: str,
    ) -> str:
        self.deleted_item_ids.append(item_id)
        return f"{sync_source}:{sync_ref}"


async def test_product_reconcile_deactivates_missing_items_and_syncs_sold_num() -> None:
    product_payloads = {
        101: {"response": {"item": {"sold_num": 7, "item_no": "SKU-101"}}},
        202: {"data": {"item": {"sold_num": 0, "item_no": "SKU-202"}}},
        303: {"data": {"item": {"sold_num": 2, "item_no": "SKU-303"}}},
    }
    youzan_client = FakeYouzanClient({101, 303}, product_payloads)
    product_repo = FakeProductRepo(active_ids=[101, 202, 303], all_ids=[101, 202, 303])
    history_repo = FakeHistoryRepo()
    knowledge_repo = FakeKnowledgeProductRepo()
    service = ProductReconcileService(
        youzan_client=youzan_client,  # type: ignore[arg-type]
        product_repo=product_repo,  # type: ignore[arg-type]
        history_repo=history_repo,  # type: ignore[arg-type]
        knowledge_product_repo=knowledge_repo,  # type: ignore[arg-type]
    )

    summary = await service.run()

    assert summary["checked"] == 3
    assert summary["onsale_from_youzan"] == 2
    assert summary["deactivated"] == 1
    assert summary["deactivated_ids"] == [202]
    assert summary["sold_num_synced"] == 2
    assert summary["errors"] == []
    assert product_repo.deleted[0][0] == 202
    assert product_repo.deleted[0][2:] == ("product_reconcile", "daily_reconcile")
    assert knowledge_repo.deleted_item_ids == ["202"]
    assert product_repo.sold_updates == {101: (7, "SKU-101"), 303: (2, "SKU-303")}
    assert len(history_repo.records) == 1
    assert history_repo.records[0].action == "deactivate"
    assert history_repo.records[0].status == "success"


async def test_product_reconcile_keeps_running_when_deactivate_fails() -> None:
    class FailingProductRepo(FakeProductRepo):
        async def delete_product(
            self,
            item_id: int,
            event_time: str,
            *,
            sync_source: str,
            sync_ref: str,
        ) -> str:
            raise RuntimeError("database locked")

    youzan_client = FakeYouzanClient({101}, {101: {"data": {"item": {"sold_num": 1}}}})
    product_repo = FailingProductRepo(active_ids=[101, 202], all_ids=[101])
    history_repo = FakeHistoryRepo()
    service = ProductReconcileService(
        youzan_client=youzan_client,  # type: ignore[arg-type]
        product_repo=product_repo,  # type: ignore[arg-type]
        history_repo=history_repo,  # type: ignore[arg-type]
    )

    summary = await service.run()

    assert summary["checked"] == 2
    assert summary["deactivated"] == 0
    assert summary["deactivated_ids"] == []
    assert summary["sold_num_synced"] == 1
    assert summary["errors"] == ["item_id=202: database locked"]
    assert history_repo.records == []


async def test_fetch_sold_nums_ignores_api_errors_and_zero_sales() -> None:
    youzan_client = FakeYouzanClient(
        set(),
        {
            1: {"data": {"item": {"sold_num": 0, "item_no": "ZERO"}}},
            2: {"response": {"item": {"sold_num": 5, "item_no": "SKU-2"}}},
        },
    )
    service = ProductReconcileService(
        youzan_client=youzan_client,  # type: ignore[arg-type]
        product_repo=FakeProductRepo([], []),  # type: ignore[arg-type]
        history_repo=FakeHistoryRepo(),  # type: ignore[arg-type]
    )

    sold_nums = await service._fetch_sold_nums([1, 2, 3])  # noqa: SLF001

    assert sold_nums == {2: (5, "SKU-2")}
    assert sorted(youzan_client.requested_product_ids) == [1, 2, 3]
