"""
商品全量对账服务。

职责：
- 拉取有赞在售商品 ID 集合
- 与本地 is_active=1 的商品对比
- 将有赞已下架但本地仍活跃的商品标记为 is_active=0
- 将每条变更写入 content_change_history（source=product_reconcile）
"""

from datetime import datetime, timezone

from app.logger import setup_logger
from app.models.content_change_history import ContentChangeHistoryCreate
from app.repository.content_change_history_repo import ContentChangeHistoryRepo
from app.repository.youzan_repo import YouzanProductRepo
from app.service.youzan.client import YouzanClient

logger = setup_logger()

# 对账来源标识
RECONCILE_SOURCE = "product_reconcile"


class ProductReconcileService:
    """商品全量对账服务，比对有赞在售集合与本地活跃记录，自动补齐下架状态。"""

    def __init__(
        self,
        youzan_client: YouzanClient,
        product_repo: YouzanProductRepo,
        history_repo: ContentChangeHistoryRepo,
    ) -> None:
        self._client = youzan_client
        self._product_repo = product_repo
        self._history_repo = history_repo

    async def run(self) -> dict:
        """
        执行全量对账，返回摘要字典：
        {checked, deactivated, errors, duration_ms}
        """
        start_ts = datetime.now(tz=timezone.utc)
        logger.info("商品全量对账任务开始")

        onsale_ids = await self._client.list_onsale_item_ids()
        local_ids = await self._product_repo.list_active_item_ids()

        deactivated: list[int] = []
        errors: list[str] = []

        for item_id in local_ids:
            if item_id not in onsale_ids:
                await self._deactivate_one(item_id, deactivated, errors)

        duration_ms = int((datetime.now(tz=timezone.utc) - start_ts).total_seconds() * 1000)
        logger.info(
            "商品全量对账完成：检查 %d 条，下架 %d 条，错误 %d 条，耗时 %d ms",
            len(local_ids), len(deactivated), len(errors), duration_ms,
        )
        return {
            "checked": len(local_ids),
            "onsale_from_youzan": len(onsale_ids),
            "deactivated": len(deactivated),
            "deactivated_ids": deactivated,
            "errors": errors,
            "duration_ms": duration_ms,
        }

    async def _deactivate_one(
        self,
        item_id: int,
        deactivated: list[int],
        errors: list[str],
    ) -> None:
        """软下架单个商品并写历史记录，异常时记录错误信息不中断整体流程。"""
        now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        try:
            result = await self._product_repo.delete_product(
                item_id,
                now_str,
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
                occurred_at=now_str,
            ))
            deactivated.append(item_id)
            logger.info("对账下架商品: item_id=%d result=%s", item_id, result)
        except Exception as exc:
            err_msg = f"item_id={item_id}: {exc}"
            errors.append(err_msg)
            logger.error("对账下架商品失败: %s", err_msg)
