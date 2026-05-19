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

    async def get_by_titles(self, titles: list[str], limit: int = 8) -> list[KnowledgeEntry]:
        """根据标题列表批量获取知识条目。"""
        if not titles:
            return []
        placeholders = ",".join("?" * len(titles))
        rows = await self._db.execute_fetchall(
            f"SELECT id, category, title, content, keywords, priority, "
            f"is_active, created_at, updated_at FROM knowledge_base "
            f"WHERE title IN ({placeholders}) AND is_active = 1 "
            f"ORDER BY priority DESC LIMIT ?",
            (*titles, limit),
        )
        return [KnowledgeEntry(**dict(r)) for r in rows]

    async def get_all_titles(self) -> list[tuple[str, str]]:
        """获取所有知识条目（title, content）用于构建向量索引。"""
        rows = await self._db.execute_fetchall(
            "SELECT title, content FROM knowledge_base WHERE is_active = 1"
        )
        return [(r["title"], r["content"]) for r in rows]

    async def count_all(self) -> int:
        """返回知识库总条目数。"""
        row = await self._db.execute_fetchall("SELECT COUNT(*) as c FROM knowledge_base")
        return row[0]["c"] if row else 0

    async def get_all_products(
        self, search: str = "", limit: int = 50, offset: int = 0,
    ) -> list[KnowledgeEntry]:
        """分页获取所有知识条目（含下架），用于后台管理。"""
        keyword = f"%{search}%"
        rows = await self._db.execute_fetchall(
            "SELECT id, category, title, content, keywords, priority, "
            "is_active, created_at, updated_at "
            "FROM knowledge_base "
            "WHERE title LIKE ? OR content LIKE ? OR keywords LIKE ? "
            "ORDER BY category, priority DESC, title LIMIT ? OFFSET ?",
            (keyword, keyword, keyword, limit, offset),
        )
        return [KnowledgeEntry(**dict(r)) for r in rows]

    async def count_products(self, search: str = "") -> int:
        """返回管理列表总条目数。"""
        keyword = f"%{search}%"
        rows = await self._db.execute_fetchall(
            "SELECT COUNT(*) as c FROM knowledge_base "
            "WHERE title LIKE ? OR content LIKE ? OR keywords LIKE ?",
            (keyword, keyword, keyword),
        )
        return rows[0]["c"] if rows else 0

    async def get_by_id(self, entry_id: int) -> KnowledgeEntry | None:
        """按 ID 获取单条知识记录（忽略 is_active）。"""
        rows = await self._db.execute_fetchall(
            "SELECT id, category, title, content, keywords, priority, "
            "is_active, created_at, updated_at "
            "FROM knowledge_base WHERE id = ?",
            (entry_id,),
        )
        return KnowledgeEntry(**dict(rows[0])) if rows else None

    async def update_active(self, entry_id: int, is_active: bool) -> None:
        """上架或下架一条知识条目。"""
        await self._db.execute(
            "UPDATE knowledge_base SET is_active = ?, updated_at = datetime('now') WHERE id = ?",
            (1 if is_active else 0, entry_id),
        )
        await self._db.commit()
