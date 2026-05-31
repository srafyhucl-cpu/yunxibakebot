"""知识库 RAG 检索、通用查询与向量同步数据访问层。"""

import aiosqlite

from app.models.content_change_history import WriteResult
from app.models.knowledge import KnowledgeEntry, VectorSyncStatus

ENTRY_COLUMNS = (
    "id, category, content_type, title, content, keywords, priority, is_active, "
    "youzan_item_id, last_sync_source, last_sync_ref, content_origin, created_by, "
    "updated_by, suggested_category, suggest_reason, vector_sync_status, "
    "vector_synced_at, vector_sync_error, vector_sync_retry_count, created_at, updated_at"
)
ENTRY_SELECT_SQL = "SELECT " + ENTRY_COLUMNS + " FROM knowledge_base "


class KnowledgeRepo:
    """知识库仓库：提供检索、管理和商品知识回写能力。"""

    def __init__(self, db: aiosqlite.Connection = None) -> None:
        self._injected_db = db

    @property
    def _db(self) -> aiosqlite.Connection:
        if self._injected_db is not None:
            return self._injected_db
        try:
            from app.database import db_conn_var
            return db_conn_var.get()
        except LookupError as exc:
            raise RuntimeError("数据库操作未在 db_session_scope 上下文管理器中执行！") from exc

    async def search(self, query: str, limit: int = 5) -> list[KnowledgeEntry]:
        """按关键词搜索启用中的知识条目。"""
        keyword = f"%{query}%"
        rows = await self._db.execute_fetchall(
            ENTRY_SELECT_SQL
            + "WHERE is_active = 1 AND (title LIKE ? OR content LIKE ? OR keywords LIKE ?) "
            + "ORDER BY priority DESC LIMIT ?",
            (keyword, keyword, keyword, limit),
        )
        return [KnowledgeEntry(**dict(row)) for row in rows]

    async def get_by_category(self, category: str) -> list[KnowledgeEntry]:
        """按检索分类获取启用中的知识条目。"""
        rows = await self._db.execute_fetchall(
            ENTRY_SELECT_SQL + "WHERE category = ? AND is_active = 1 " + "ORDER BY priority DESC",
            (category,),
        )
        return [KnowledgeEntry(**dict(row)) for row in rows]

    async def get_by_titles(self, titles: list[str], limit: int = 8) -> list[KnowledgeEntry]:
        """根据标题批量获取知识条目。"""
        if not titles:
            return []
        placeholders = ",".join("?" * len(titles))
        rows = await self._db.execute_fetchall(
            ENTRY_SELECT_SQL
            + f"WHERE title IN ({placeholders}) AND is_active = 1 "
            + "ORDER BY priority DESC LIMIT ?",
            (*titles, limit),
        )
        return [KnowledgeEntry(**dict(row)) for row in rows]

    async def get_by_youzan_item_ids(self, keys: list[str], limit: int = 8) -> list[KnowledgeEntry]:
        """根据有赞商品 ID 或本地知识 ID 批量获取知识条目。"""
        if not keys:
            return []

        youzan_ids: list[str] = []
        knowledge_ids: list[int] = []
        for key in keys:
            if key.startswith("kb_"):
                try:
                    knowledge_ids.append(int(key[3:]))
                except ValueError:
                    continue
            else:
                youzan_ids.append(key)

        clauses: list[str] = []
        params: list[object] = []
        if youzan_ids:
            placeholders = ",".join("?" * len(youzan_ids))
            clauses.append(f"youzan_item_id IN ({placeholders})")
            params.extend(youzan_ids)
        if knowledge_ids:
            placeholders = ",".join("?" * len(knowledge_ids))
            clauses.append(f"id IN ({placeholders})")
            params.extend(knowledge_ids)
        if not clauses:
            return []

        rows = await self._db.execute_fetchall(
            ENTRY_SELECT_SQL
            + f"WHERE ({' OR '.join(clauses)}) AND is_active = 1 "
            + "ORDER BY priority DESC LIMIT ?",
            (*params, limit),
        )
        return [KnowledgeEntry(**dict(row)) for row in rows]

    async def get_all_titles(self) -> list[tuple[str, str]]:
        """获取全部启用知识的标题与正文。"""
        rows = await self._db.execute_fetchall(
            "SELECT title, content FROM knowledge_base WHERE is_active = 1"
        )
        return [(row["title"], row["content"]) for row in rows]

    async def get_all_titles_with_keys(self) -> list[tuple[str, str, str]]:
        """获取全部启用知识，供向量索引构建使用。"""
        rows = await self._db.execute_fetchall(
            "SELECT id, youzan_item_id, title, content FROM knowledge_base WHERE is_active = 1"
        )
        return [
            (
                row["youzan_item_id"] if row["youzan_item_id"] else f"kb_{row['id']}",
                row["title"],
                row["content"],
            )
            for row in rows
        ]

    async def count_all(self) -> int:
        """返回知识库总条目数。"""
        rows = await self._db.execute_fetchall("SELECT COUNT(*) AS c FROM knowledge_base")
        return int(rows[0]["c"]) if rows else 0

    async def list_current_entries(
        self,
        *,
        category: str = "",
        keyword: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> list[KnowledgeEntry]:
        """分页获取当前知识内容，供观察台使用。"""
        clauses = ["1 = 1"]
        params: list[object] = []
        if category:
            clauses.append("category = ?")
            params.append(category)
        if keyword:
            like = f"%{keyword}%"
            clauses.append("(title LIKE ? OR content LIKE ? OR keywords LIKE ?)")
            params.extend([like, like, like])
        rows = await self._db.execute_fetchall(
            ENTRY_SELECT_SQL
            + f"WHERE {' AND '.join(clauses)} "
            + "ORDER BY updated_at DESC, priority DESC, id DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
        return [KnowledgeEntry(**dict(row)) for row in rows]

    async def count_current_entries(self, *, category: str = "", keyword: str = "") -> int:
        """返回观察台当前知识总数。"""
        clauses = ["1 = 1"]
        params: list[object] = []
        if category:
            clauses.append("category = ?")
            params.append(category)
        if keyword:
            like = f"%{keyword}%"
            clauses.append("(title LIKE ? OR content LIKE ? OR keywords LIKE ?)")
            params.extend([like, like, like])
        rows = await self._db.execute_fetchall(
            "SELECT COUNT(*) AS c FROM knowledge_base "
            f"WHERE {' AND '.join(clauses)}",
            tuple(params),
        )
        return int(rows[0]["c"]) if rows else 0

    async def get_by_id(self, entry_id: int) -> KnowledgeEntry | None:
        """按 ID 获取单条知识记录。"""
        rows = await self._db.execute_fetchall(
            ENTRY_SELECT_SQL + "WHERE id = ?",
            (entry_id,),
        )
        return KnowledgeEntry(**dict(rows[0])) if rows else None

    async def mark_vector_sync_status(
        self,
        entry_id: int,
        *,
        status: str,
        error_message: str = "",
        synced_at: str = "",
        retry_increment: bool = False,
    ) -> str:
        """更新向量同步状态。"""
        cursor = await self._db.execute(
            "UPDATE knowledge_base SET "
            "vector_sync_status = ?, "
            "vector_synced_at = ?, "
            "vector_sync_error = ?, "
            "vector_sync_retry_count = vector_sync_retry_count + ?, "
            "updated_at = datetime('now') "
            "WHERE id = ?",
            (
                status,
                synced_at,
                error_message,
                1 if retry_increment else 0,
                entry_id,
            ),
        )
        await self._db.commit()
        return WriteResult.APPLIED if cursor.rowcount else WriteResult.SKIPPED

    async def insert_entry(
        self,
        *,
        category: str,
        title: str,
        content: str,
        keywords: str,
        priority: int,
        sync_source: str,
        sync_ref: str = "",
        content_type: str = "faq",
        content_origin: str = "seed_knowledge",
        created_by: str = "",
        updated_by: str = "",
        suggested_category: str = "",
        suggest_reason: str = "",
        vector_sync_status: str = VectorSyncStatus.SUCCESS,
        vector_synced_at: str = "",
    ) -> int:
        """插入一条非商品知识记录。"""
        cursor = await self._db.execute(
            "INSERT INTO knowledge_base ("
            "category, content_type, title, content, keywords, priority, is_active, "
            "last_sync_source, last_sync_ref, content_origin, created_by, updated_by, "
            "suggested_category, suggest_reason, vector_sync_status, vector_synced_at"
            ") VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                category,
                content_type,
                title,
                content,
                keywords,
                priority,
                sync_source,
                sync_ref,
                content_origin,
                created_by,
                updated_by,
                suggested_category,
                suggest_reason,
                vector_sync_status,
                vector_synced_at,
            ),
        )
        await self._db.commit()
        return int(cursor.lastrowid)

    async def get_pending_sync_entries(self, limit: int = 500) -> list[KnowledgeEntry]:
        """获取所有待同步（pending/failed）的知识条目，跨所有分类和类型。"""
        rows = await self._db.execute_fetchall(
            ENTRY_SELECT_SQL
            + "WHERE vector_sync_status IN ('pending', 'failed') "
            "ORDER BY updated_at ASC LIMIT ?",
            (limit,),
        )
        return [KnowledgeEntry(**dict(row)) for row in rows]
