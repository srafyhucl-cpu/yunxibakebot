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

        # 1. 尝试向量搜索（asyncio.to_thread 避免同步推理阻塞事件循环）
        if self._vs and self._vs.doc_count > 0:
            vs_results = await asyncio.to_thread(self._vs.search, query, limit)
            if vs_results:
                keys = [k for k, _ in vs_results]
                entries = await self._repo.get_by_titles(keys, limit=len(keys))
                logger.debug("向量检索 '%s' → %d 条", query[:30], len(entries))
                return await self._inject_featured(entries, limit)

        # 2. 回退关键词搜索
        results = await self._repo.search(query, limit=limit)
        logger.debug("关键词检索 '%s' → %d 条", query[:30], len(results))
        return await self._inject_featured(results, limit)

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
