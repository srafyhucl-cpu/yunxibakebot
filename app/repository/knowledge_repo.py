"""
知识库数据访问层。

支持按关键词模糊搜索和按分类查询，供 LLM 上下文注入使用。
"""

import aiosqlite

from app.models.knowledge import KnowledgeEntry


class KnowledgeRepo:
    """知识库仓库：标题/正文/关键词模糊搜索。"""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def search(self, query: str, limit: int = 5) -> list[KnowledgeEntry]:
        """按关键词搜索标题、正文、关键字字段，按优先级排序。"""
        keyword = f"%{query}%"
        rows = await self._db.execute_fetchall(
            "SELECT id, category, title, content, keywords, priority, "
            "is_active, created_at, updated_at "
            "FROM knowledge_base "
            "WHERE is_active = 1 AND (title LIKE ? OR content LIKE ? OR keywords LIKE ?) "
            "ORDER BY priority DESC LIMIT ?",
            (keyword, keyword, keyword, limit),
        )
        return [KnowledgeEntry(**dict(r)) for r in rows]

    async def get_by_category(self, category: str) -> list[KnowledgeEntry]:
        """按分类获取所有启用的知识条目。"""
        rows = await self._db.execute_fetchall(
            "SELECT id, category, title, content, keywords, priority, "
            "is_active, created_at, updated_at "
            "FROM knowledge_base WHERE category = ? AND is_active = 1 "
            "ORDER BY priority DESC",
            (category,),
        )
        return [KnowledgeEntry(**dict(r)) for r in rows]

    async def count_all(self) -> int:
        """返回知识库总条目数。"""
        row = await self._db.execute_fetchall("SELECT COUNT(*) as c FROM knowledge_base")
        return row[0]["c"] if row else 0
