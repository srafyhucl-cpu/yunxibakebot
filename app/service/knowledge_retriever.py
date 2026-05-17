"""
知识库检索服务。

支持两种模式：
- 向量搜索（TF-IDF n-gram cosine）：语义理解，模糊匹配
- 关键词搜索（SQL LIKE）：精确匹配

调用顺序：向量搜索 → 不够时补充关键词结果。
"""

from app.logger import setup_logger
from app.models.knowledge import KnowledgeEntry
from app.repository.knowledge_repo import KnowledgeRepo
from app.service.vector_search import VectorSearcher

logger = setup_logger()


class KnowledgeRetriever:
    """知识检索器：向量搜索 + 关键词搜索组合。"""

    def __init__(self, repo: KnowledgeRepo, vs: VectorSearcher | None = None) -> None:
        self._repo = repo
        self._vs = vs

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

        # 1. 尝试向量搜索
        if self._vs and self._vs.doc_count > 0:
            vs_results = self._vs.search(query, limit=limit)
            if vs_results:
                keys = [k for k, _ in vs_results]
                entries = await self._repo.get_by_titles(keys, limit=len(keys))
                logger.debug("向量检索 '%s' → %d 条", query[:30], len(entries))
                return entries

        # 2. 回退关键词搜索
        results = await self._repo.search(query, limit=limit)
        logger.debug("关键词检索 '%s' → %d 条", query[:30], len(results))
        return results
