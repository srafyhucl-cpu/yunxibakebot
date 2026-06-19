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
_ITEM_BASE_BATCH_SIZE = 10


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

        onsale_items = await self._client.list_onsale_items()
        onsale_ids = self._extract_onsale_ids(onsale_items)
        local_ids = await self._product_repo.list_active_item_ids()

        deactivated: list[int] = []
        errors: list[str] = []

        for item_id in local_ids:
            if item_id not in onsale_ids:
                await self._deactivate_one(item_id, deactivated, errors)

        sold_updated = 0
        category_synced = 0
        all_local_ids = await self._product_repo.list_all_item_ids()
        if all_local_ids:
            product_tags = await self._client.list_product_tags()
            classification_titles = await self._fetch_classification_titles()
            item_base_categories = await self._fetch_item_base_categories(all_local_ids)
            category_synced = await self._sync_product_categories(
                onsale_items, product_tags
            )
            category_synced += await self._sync_item_base_categories(
                item_base_categories,
                classification_titles,
            )
            sold_num_map = await self._fetch_sold_nums(all_local_ids)
            if sold_num_map:
                try:
                    sold_updated = await self._product_repo.bulk_update_sold_and_no(
                        sold_num_map
                    )
                    logger.info("对账同步商品销量与 item_no：更新 %d 条", sold_updated)
                except Exception as exc:
                    logger.error("对账同步销量失败: %s", exc)

        duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
        logger.info(
            "商品全量对账完成：检查 %d 条，下架 %d 条，销量同步 %d 条，分类同步 %d 条（全量 %d 条），错误 %d 条，耗时 %d ms",
            len(local_ids),
            len(deactivated),
            sold_updated,
            category_synced,
            len(all_local_ids),
            len(errors),
            duration_ms,
        )
        return {
            "checked": len(local_ids),
            "onsale_from_youzan": len(onsale_ids),
            "deactivated": len(deactivated),
            "deactivated_ids": deactivated,
            "sold_num_synced": sold_updated,
            "category_synced": category_synced,
            "errors": errors,
            "duration_ms": duration_ms,
        }

    def _extract_onsale_ids(self, items: list[dict]) -> set[int]:
        """从有赞在售列表提取商品 ID。"""
        item_ids: set[int] = set()
        for item in items:
            try:
                item_ids.add(int(item["item_id"]))
            except (KeyError, ValueError, TypeError):
                continue
        return item_ids

    async def _sync_product_categories(
        self, items: list[dict], tags: list[dict]
    ) -> int:
        """同步有赞商品分组 tag id 到本地商品宽表和分类表。"""
        tag_ids_map: dict[int, list[str]] = {}
        tag_counts: dict[str, int] = {}
        tag_titles = self._build_tag_title_map(tags)
        for item in items:
            try:
                item_id = int(item["item_id"])
            except (KeyError, ValueError, TypeError):
                continue
            tag_ids = [
                str(tag_id) for tag_id in item.get("tag_ids", []) if str(tag_id).strip()
            ]
            if not tag_ids:
                continue
            tag_ids_map[item_id] = tag_ids
            for tag_id in tag_ids:
                tag_counts[tag_id] = tag_counts.get(tag_id, 0) + 1

        for index, (tag_id, product_count) in enumerate(sorted(tag_counts.items())):
            title = tag_titles.get(tag_id, f"有赞分组 {tag_id}")
            await self._product_repo.upsert_category(
                tag_id=tag_id,
                title=title,
                sort=index * 10,
                product_count=product_count,
                is_public=0 if title.startswith("有赞分组 ") else 1,
            )
        updated = await self._product_repo.bulk_update_tag_ids(tag_ids_map)
        logger.info(
            "同步有赞商品分类 tag_ids：商品 %d 条，分组 %d 个", updated, len(tag_counts)
        )
        return updated

    def _build_tag_title_map(self, tags: list[dict]) -> dict[str, str]:
        """从有赞商品分组列表构建 tag id 到分组名的映射。"""
        result: dict[str, str] = {}
        for tag in tags:
            tag_id = str(tag.get("id", "")).strip()
            title = str(tag.get("name", "")).strip()
            if tag_id and title:
                result[tag_id] = title
        return result

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
                    item = (raw.get("data") or raw.get("response") or {}).get(
                        "item"
                    ) or {}
                    sold_num = int(item.get("sold_num", 0) or 0)
                    item_no = item.get("item_no", "") or ""
                    if sold_num > 0:
                        result[iid] = (sold_num, item_no)
                except Exception as exc:
                    logger.warning("获取商品 sold_num 失败 item_id=%d: %s", iid, exc)

        await asyncio.gather(*[_fetch_one(iid) for iid in item_ids])
        logger.info("并发拉取 sold_num 完成：%d/%d 有销量", len(result), len(item_ids))
        return result

    async def _fetch_item_base_categories(
        self, item_ids: list[int]
    ) -> dict[int, dict[str, list[str]]]:
        """批量拉取 ITEM_INFO 分类字段，按 item_id 返回稳定分类 ID。"""
        if not hasattr(self._client, "search_item_base"):
            return {}
        result: dict[int, dict[str, list[str]]] = {}
        for start in range(0, len(item_ids), _ITEM_BASE_BATCH_SIZE):
            batch = item_ids[start : start + _ITEM_BASE_BATCH_SIZE]
            try:
                items = await self._client.search_item_base(batch)
            except Exception as exc:
                logger.warning("批量获取 ITEM_INFO 分类失败 batch=%s: %s", batch, exc)
                continue
            for item in items:
                item_id = self._extract_item_base_item_id(item)
                if item_id <= 0:
                    continue
                categories = {
                    "classification_ids": self._extract_id_list(
                        item.get("classification_ids"),
                        item.get("classification_id"),
                    ),
                    "group_ids": self._extract_id_list(item.get("group_ids")),
                    "second_group_ids": self._extract_id_list(
                        item.get("second_group_ids")
                    ),
                    "leaf_category_ids": self._extract_id_list(
                        item.get("leaf_category_ids"),
                        item.get("leaf_category_id"),
                    ),
                }
                if any(categories.values()):
                    result[item_id] = categories
        logger.info(
            "批量获取 ITEM_INFO 分类完成：%d/%d 条有分类", len(result), len(item_ids)
        )
        return result

    async def _sync_item_base_categories(
        self,
        item_base_categories: dict[int, dict[str, list[str]]],
        classification_titles: dict[str, str] | None = None,
    ) -> int:
        """将 ITEM_INFO 分类字段写入宽表，并把 classification_ids 建为公开分类。"""
        classification_titles = classification_titles or {}
        classification_counts: dict[str, int] = {}
        for categories in item_base_categories.values():
            for classification_id in categories.get("classification_ids", []):
                classification_counts[classification_id] = (
                    classification_counts.get(classification_id, 0) + 1
                )
        for index, (classification_id, product_count) in enumerate(
            sorted(classification_counts.items())
        ):
            await self._product_repo.upsert_category(
                tag_id=f"classification-{classification_id}",
                title=classification_titles.get(
                    classification_id, f"有赞分类 {classification_id}"
                ),
                sort=1000 + index * 10,
                product_count=product_count,
                is_public=1,
            )
        updated = await self._product_repo.bulk_update_item_base_categories(
            item_base_categories
        )
        logger.info(
            "同步 ITEM_INFO 商品分类：商品 %d 条，公开分类 %d 个",
            updated,
            len(classification_counts),
        )
        return updated

    async def _fetch_classification_titles(self) -> dict[str, str]:
        """拉取有赞商品分类中文名，返回 classification_id 到 name 的映射。"""
        if not hasattr(self._client, "search_item_classifications"):
            return {}
        try:
            classifications = await self._client.search_item_classifications()
        except Exception as exc:
            logger.warning("获取有赞商品分类名称失败: %s", exc)
            return {}
        result: dict[str, str] = {}
        for classification in classifications:
            classification_id = str(classification.get("classification_id", "")).strip()
            title = str(classification.get("name", "")).strip()
            if classification_id and title:
                result[classification_id] = title
        logger.info("有赞商品分类名称映射完成：%d 个", len(result))
        return result

    def _extract_item_base_item_id(self, item: dict) -> int:
        """从 ITEM_INFO 响应中提取商品 ID。"""
        for key in ("item_id", "id", "itemId"):
            try:
                value = int(item.get(key, 0) or 0)
            except (TypeError, ValueError):
                value = 0
            if value > 0:
                return value
        return 0

    def _extract_id_list(self, value: object, single_value: object = None) -> list[str]:
        """将有赞返回的 ID 字段标准化为字符串列表。"""
        if not isinstance(value, list):
            token = str(single_value or "").strip()
            return [token] if token and token != "0" else []
        if not value:
            token = str(single_value or "").strip()
            return [token] if token and token != "0" else []
        result: list[str] = []
        for item in value:
            token = str(item).strip()
            if token and token != "0":
                result.append(token)
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
            await self._history_repo.add(
                ContentChangeHistoryCreate(
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
                )
            )
            if self._knowledge_product_repo is not None:
                kb_result = await self._knowledge_product_repo.delete_product_knowledge(
                    str(item_id),
                    sync_source=RECONCILE_SOURCE,
                    sync_ref="daily_reconcile",
                )
                logger.info(
                    "对账联动下架知识条目: item_id=%d result=%s", item_id, kb_result
                )
            deactivated.append(item_id)
            logger.info("对账下架商品: item_id=%d result=%s", item_id, result)
        except Exception as exc:
            err_msg = f"item_id={item_id}: {exc}"
            errors.append(err_msg)
            logger.error("对账下架商品失败: %s", err_msg)
