"""
知识库检索服务。

根据用户问题关键词搜索知识库，返回相关条目供 LLM 注入上下文。
"""

from app.logger import setup_logger
from app.models.knowledge import KnowledgeEntry
from app.repository.knowledge_repo import KnowledgeRepo

logger = setup_logger()


class KnowledgeRetriever:
    """知识检索器：搜索和按分类获取知识条目。"""

    def __init__(self, repo: KnowledgeRepo) -> None:
        self._repo = repo

    async def search(self, query: str, limit: int = 5) -> list[KnowledgeEntry]:
        """根据关键词搜索知识库，返回匹配的知识条目。"""
        if not query.strip():
            return []
        results = await self._repo.search(query, limit=limit)
        logger.debug("知识库检索 '%s' 返回 %d 条结果", query, len(results))
        return results

    async def get_by_category(self, category: str) -> list[KnowledgeEntry]:
        """按分类获取所有知识条目。"""
        return await self._repo.get_by_category(category)
