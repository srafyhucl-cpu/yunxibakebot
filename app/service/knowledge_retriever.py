"""
知识库检索服务。

支持两种模式：
- 语义向量搜索（EmbeddingSearcher）：语义理解，模糊匹配
- 关键词搜索（SQL LIKE）：精确匹配

调用顺序：向量搜索 → 不够时补充关键词结果。
向量搜索通过 asyncio.to_thread 包裹，不阻塞事件循环。
"""

import asyncio

from app.logger import setup_logger
from app.models.config import FEATURED_PRODUCTS_KEY
from app.models.knowledge import KnowledgeCategory, KnowledgeEntry
from app.repository.config_repo import ConfigRepo
from app.repository.knowledge_repo import KnowledgeRepo
from app.service.embedding_search import EmbeddingSearcher

logger = setup_logger()


class KnowledgeRetriever:
    """知识检索器：向量搜索 + 关键词搜索组合，始终注入主推款。"""

    def __init__(
        self,
        repo: KnowledgeRepo,
        vs: EmbeddingSearcher | None = None,
        config_repo: ConfigRepo | None = None,
    ) -> None:
        self._repo = repo
        self._vs = vs
        self._config_repo = config_repo

    async def search(self, query: str, limit: int = 8) -> list[KnowledgeEntry]:
        """
        混合检索：优先向量，不足时补关键词。

        参数：
            query: 用户查询文本
            limit: 返回最大条数
        返回：
            匹配的知识条目列表
        """
        if not query.strip():
            return []

        entries: list[KnowledgeEntry] = []
        if self._vs and self._vs.doc_count > 0:
            vs_results = await asyncio.to_thread(self._vs.search, query, limit)
            if vs_results:
                keys = [k for k, _ in vs_results]
                entries = await self._repo.get_by_titles(keys, limit=len(keys))
                logger.debug("向量检索 '%s' → %d 条", query[:30], len(entries))

        keyword_results = await self._repo.search(query, limit=limit)
        logger.debug("关键词检索 '%s' → %d 条", query[:30], len(keyword_results))
        merged = self._merge_entries(keyword_results, entries, limit)
        results = await self._inject_featured(merged, limit)
        return await self._prepend_live_data(results)

    async def search_keyword_only(self, query: str, limit: int = 8) -> list[KnowledgeEntry]:
        if not query.strip():
            return []
        results = await self._repo.search(query, limit=limit)
        logger.debug("精确关键词检索 '%s' → %d 条", query[:30], len(results))
        featured_results = await self._inject_featured(results, limit)
        return await self._prepend_live_data(featured_results)

    async def _prepend_live_data(self, entries: list[KnowledgeEntry]) -> list[KnowledgeEntry]:
        """对于含有 youzan_item_id 的知识条目，现场秒级反查 products 物理表并动态拼接最新库存与售价。"""
        if not entries:
            return entries

        from app.repository.youzan_repo import YouzanProductRepo
        product_repo = YouzanProductRepo(self._repo._db)

        for entry in entries:
            if entry.youzan_item_id:
                try:
                    product = await product_repo.get_by_id(int(entry.youzan_item_id))
                    if product:
                        price_yuan = product["price_fen"] / 100.0
                        stock = product["stock"]
                        is_active = product["is_active"]

                        # 构造富提示前置前缀，死锁 AI 回复幻觉风险
                        live_prefix = f"【芸熙烘焙小程序实时官方数据 — 当前售价：{price_yuan:.2f}元 | 实时可用库存：{stock}件】\n\n"
                        if is_active == 0:
                            live_prefix = "【芸熙烘焙小程序实时官方数据 — ⚠️商品当前已下架或暂停预定】\n\n"
                        elif stock <= 0:
                            live_prefix = f"【芸熙烘焙小程序实时官方数据 — 当前售价：{price_yuan:.2f}元 | ⚠️商品当前在售但库存已为0，暂无现货，需要提前预约】\n\n"

                        entry.content = live_prefix + entry.content
                except Exception as exc:
                    logger.warning("现场反查商品库存（ID: %s）发生非致命异常: %s", entry.youzan_item_id, exc)

        return entries

    def _merge_entries(
        self,
        preferred_entries: list[KnowledgeEntry],
        fallback_entries: list[KnowledgeEntry],
        limit: int,
    ) -> list[KnowledgeEntry]:
        results: list[KnowledgeEntry] = []
        seen_titles: set[str] = set()
        for entry in [*preferred_entries, *fallback_entries]:
            if entry.title in seen_titles:
                continue
            results.append(entry)
            seen_titles.add(entry.title)
            if len(results) >= limit:
                break
        return results

    async def _inject_featured(self, results: list[KnowledgeEntry], limit: int) -> list[KnowledgeEntry]:
        """始终在检索结果首位插入主推款合成条目。"""
        if not self._config_repo:
            return results
        products = await self._config_repo.get_list(FEATURED_PRODUCTS_KEY)
        if not products:
            return results
        featured = KnowledgeEntry(
            category=KnowledgeCategory.STORE_INFO,
            title="近期主推款",
            content="近期重点推荐款式（顾客询问推荐时优先介绍）：" + "、".join(products),
            keywords="推荐,主推,好吃,热门,人气",
            priority=100,
        )
        deduped = [e for e in results if e.title != "近期主推款"]
        return [featured, *deduped[:limit - 1]]
