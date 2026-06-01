"""
商品全量对账服务。

职责：
- 拉取有赞在售商品 ID 集合
- 与本地 is_active=1 的商品对比
- 将有赞已下架但本地仍活跃的商品标记为 is_active=0
- 并发调用 youzan.item.get 逐个获取 sold_num 并批量回写
- 将每条变更写入 content_change_history（source=product_reconcile）
"""

import asyncio
from datetime import datetime

from app.logger import setup_logger
from app.models.content_change_history import ContentChangeHistoryCreate
from app.repository.content_change_history_repo import ContentChangeHistoryRepo
from app.repository.knowledge_product_repo import KnowledgeProductRepo
from app.repository.youzan_repo import YouzanProductRepo
from app.service.youzan.client import YouzanClient
from app.utils import now_str

logger = setup_logger()

# 对账来源标识
RECONCILE_SOURCE = "product_reconcile"
# 并发拉取 sold_num 时的最大并发数（避免触发有赞频率限制）
_SOLD_NUM_CONCURRENCY = 10


class ProductReconcileService:
    """商品全量对账服务，比对有赞在售集合与本地活跃记录，自动补齐下架状态。"""

    def __init__(
        self,
        youzan_client: YouzanClient,
        product_repo: YouzanProductRepo,
        history_repo: ContentChangeHistoryRepo,
        knowledge_product_repo: KnowledgeProductRepo | None = None,
    ) -> None:
        self._client = youzan_client
        self._product_repo = product_repo
        self._history_repo = history_repo
        self._knowledge_product_repo = knowledge_product_repo

    async def run(self) -> dict:
        """
        执行全量对账，返回摘要字典：
        {checked, deactivated, errors, duration_ms}
        """
        start_ts = datetime.now()
        logger.info("商品全量对账任务开始")

        onsale_ids = await self._client.list_onsale_item_ids()
        local_ids = await self._product_repo.list_active_item_ids()

        deactivated: list[int] = []
        errors: list[str] = []

        for item_id in local_ids:
            if item_id not in onsale_ids:
                await self._deactivate_one(item_id, deactivated, errors)

        sold_updated = 0
        all_local_ids = await self._product_repo.list_all_item_ids()
        if all_local_ids:
            sold_num_map = await self._fetch_sold_nums(all_local_ids)
            if sold_num_map:
                try:
                    sold_updated = await self._product_repo.bulk_update_sold_and_no(sold_num_map)
                    logger.info("对账同步商品销量与 item_no：更新 %d 条", sold_updated)
                except Exception as exc:
                    logger.error("对账同步销量失败: %s", exc)

        duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
        logger.info(
            "商品全量对账完成：检查 %d 条，下架 %d 条，销量同步 %d 条（全量 %d 条），错误 %d 条，耗时 %d ms",
            len(local_ids), len(deactivated), sold_updated, len(all_local_ids), len(errors), duration_ms,
        )
        return {
            "checked": len(local_ids),
            "onsale_from_youzan": len(onsale_ids),
            "deactivated": len(deactivated),
            "deactivated_ids": deactivated,
            "sold_num_synced": sold_updated,
            "errors": errors,
            "duration_ms": duration_ms,
        }

    async def _fetch_sold_nums(self, item_ids: list[int]) -> dict[int, tuple[int, str]]:
        """
        并发调用 youzan.item.get 获取每个商品的真实 sold_num 和 item_no。
        使用 Semaphore 控制并发数，避免触发有赞频率限制。
        只返回 sold_num > 0 的条目，防止因接口异常误将有销量商品清零。
        """
        sem = asyncio.Semaphore(_SOLD_NUM_CONCURRENCY)
        result: dict[int, tuple[int, str]] = {}

        async def _fetch_one(iid: int) -> None:
            async with sem:
                try:
                    raw = await self._client.get_product(iid)
                    item = (raw.get("data") or raw.get("response") or {}).get("item") or {}
                    sold_num = int(item.get("sold_num", 0) or 0)
                    item_no = item.get("item_no", "") or ""
                    if sold_num > 0:
                        result[iid] = (sold_num, item_no)
                except Exception as exc:
                    logger.warning("获取商品 sold_num 失败 item_id=%d: %s", iid, exc)

        await asyncio.gather(*[_fetch_one(iid) for iid in item_ids])
        logger.info("并发拉取 sold_num 完成：%d/%d 有销量", len(result), len(item_ids))
        return result

    async def _deactivate_one(
        self,
        item_id: int,
        deactivated: list[int],
        errors: list[str],
    ) -> None:
        """软下架单个商品并写历史记录，异常时记录错误信息不中断整体流程。"""
        event_time = now_str()
        try:
            result = await self._product_repo.delete_product(
                item_id,
                event_time,
                sync_source=RECONCILE_SOURCE,
                sync_ref="daily_reconcile",
            )
            await self._history_repo.add(ContentChangeHistoryCreate(
                entity_type="product",
                entity_key=str(item_id),
                category="product",
                title=f"商品 {item_id}",
                source=RECONCILE_SOURCE,
                source_ref=str(item_id),
                action="deactivate",
                status="success",
                change_summary_json=f'{{"item_id": {item_id}, "result": "{result}", "reason": "youzan_not_onsale"}}',
                occurred_at=event_time,
            ))
            if self._knowledge_product_repo is not None:
                kb_result = await self._knowledge_product_repo.delete_product_knowledge(
                    str(item_id),
                    sync_source=RECONCILE_SOURCE,
                    sync_ref="daily_reconcile",
                )
                logger.info("对账联动下架知识条目: item_id=%d result=%s", item_id, kb_result)
            deactivated.append(item_id)
            logger.info("对账下架商品: item_id=%d result=%s", item_id, result)
        except Exception as exc:
            err_msg = f"item_id={item_id}: {exc}"
            errors.append(err_msg)
            logger.error("对账下架商品失败: %s", err_msg)
