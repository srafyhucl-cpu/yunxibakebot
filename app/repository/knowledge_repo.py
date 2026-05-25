"""知识库数据访问层。"""

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

ADMIN_LIST_CONTENT_TYPES = ("faq", "rule", "script")


class KnowledgeRepo:
    """知识库仓库：提供检索、管理和商品知识回写能力。"""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

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

    async def get_all_products(
        self,
        search: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> list[KnowledgeEntry]:
        """分页获取全部知识条目，供旧商品管理页使用。"""
        keyword = f"%{search}%"
        rows = await self._db.execute_fetchall(
            ENTRY_SELECT_SQL
            + "WHERE title LIKE ? OR content LIKE ? OR keywords LIKE ? "
            + "ORDER BY category, priority DESC, title LIMIT ? OFFSET ?",
            (keyword, keyword, keyword, limit, offset),
        )
        return [KnowledgeEntry(**dict(row)) for row in rows]

    async def count_products(self, search: str = "") -> int:
        """返回旧商品管理列表总数。"""
        keyword = f"%{search}%"
        rows = await self._db.execute_fetchall(
            "SELECT COUNT(*) AS c FROM knowledge_base "
            "WHERE title LIKE ? OR content LIKE ? OR keywords LIKE ?",
            (keyword, keyword, keyword),
        )
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

    async def list_admin_entries(
        self,
        *,
        content_type: str = "",
        keyword: str = "",
        is_active: str = "",
        vector_status: str = "",
        limit: int = 30,
        offset: int = 0,
    ) -> list[KnowledgeEntry]:
        """分页获取后台知识配置列表。"""
        clauses = ["content_type IN (?, ?, ?)"]
        params: list[object] = list(ADMIN_LIST_CONTENT_TYPES)
        if content_type:
            clauses.append("content_type = ?")
            params.append(content_type)
        if keyword:
            like = f"%{keyword}%"
            clauses.append("(title LIKE ? OR content LIKE ? OR keywords LIKE ? OR vector_sync_error LIKE ?)")
            params.extend([like, like, like, like])
        if is_active in {"0", "1"}:
            clauses.append("is_active = ?")
            params.append(int(is_active))
        if vector_status:
            clauses.append("vector_sync_status = ?")
            params.append(vector_status)
        rows = await self._db.execute_fetchall(
            ENTRY_SELECT_SQL
            + f"WHERE {' AND '.join(clauses)} "
            + "ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
        return [KnowledgeEntry(**dict(row)) for row in rows]

    async def count_admin_entries(
        self,
        *,
        content_type: str = "",
        keyword: str = "",
        is_active: str = "",
        vector_status: str = "",
    ) -> int:
        """返回后台知识配置列表总数。"""
        clauses = ["content_type IN (?, ?, ?)"]
        params: list[object] = list(ADMIN_LIST_CONTENT_TYPES)
        if content_type:
            clauses.append("content_type = ?")
            params.append(content_type)
        if keyword:
            like = f"%{keyword}%"
            clauses.append("(title LIKE ? OR content LIKE ? OR keywords LIKE ? OR vector_sync_error LIKE ?)")
            params.extend([like, like, like, like])
        if is_active in {"0", "1"}:
            clauses.append("is_active = ?")
            params.append(int(is_active))
        if vector_status:
            clauses.append("vector_sync_status = ?")
            params.append(vector_status)
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

    async def create_admin_entry(
        self,
        *,
        category: str,
        content_type: str,
        title: str,
        content: str,
        keywords: str,
        priority: int,
        is_active: bool,
        content_origin: str,
        created_by: str,
        updated_by: str,
        suggested_category: str,
        suggest_reason: str,
        sync_source: str,
        sync_ref: str = "",
        vector_sync_status: str = VectorSyncStatus.PENDING,
    ) -> int:
        """插入一条后台知识配置记录。"""
        cursor = await self._db.execute(
            "INSERT INTO knowledge_base ("
            "category, content_type, title, content, keywords, priority, is_active, "
            "last_sync_source, last_sync_ref, content_origin, created_by, updated_by, "
            "suggested_category, suggest_reason, vector_sync_status, vector_sync_error, "
            "vector_synced_at, vector_sync_retry_count"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', 0)",
            (
                category,
                content_type,
                title,
                content,
                keywords,
                priority,
                1 if is_active else 0,
                sync_source,
                sync_ref,
                content_origin,
                created_by,
                updated_by,
                suggested_category,
                suggest_reason,
                vector_sync_status,
            ),
        )
        await self._db.commit()
        return int(cursor.lastrowid)

    async def update_admin_entry(
        self,
        entry_id: int,
        *,
        category: str,
        content_type: str,
        title: str,
        content: str,
        keywords: str,
        priority: int,
        is_active: bool,
        updated_by: str,
        suggested_category: str,
        suggest_reason: str,
        sync_source: str,
        sync_ref: str = "",
        vector_sync_status: str = VectorSyncStatus.PENDING,
    ) -> str:
        """更新后台知识配置记录。"""
        cursor = await self._db.execute(
            "UPDATE knowledge_base SET "
            "category = ?, content_type = ?, title = ?, content = ?, keywords = ?, priority = ?, "
            "is_active = ?, updated_by = ?, suggested_category = ?, suggest_reason = ?, "
            "last_sync_source = ?, last_sync_ref = ?, vector_sync_status = ?, "
            "vector_sync_error = '', vector_synced_at = '', updated_at = datetime('now') "
            "WHERE id = ?",
            (
                category,
                content_type,
                title,
                content,
                keywords,
                priority,
                1 if is_active else 0,
                updated_by,
                suggested_category,
                suggest_reason,
                sync_source,
                sync_ref,
                vector_sync_status,
                entry_id,
            ),
        )
        await self._db.commit()
        return WriteResult.APPLIED if cursor.rowcount else WriteResult.SKIPPED

    async def update_active(
        self,
        entry_id: int,
        is_active: bool,
        *,
        sync_source: str = "",
        sync_ref: str = "",
    ) -> str:
        """更新条目启用状态，并记录最后修改来源。"""
        cursor = await self._db.execute(
            "UPDATE knowledge_base SET is_active = ?, "
            "last_sync_source = CASE WHEN ? != '' THEN ? ELSE last_sync_source END, "
            "last_sync_ref = CASE WHEN ? != '' THEN ? ELSE last_sync_ref END, "
            "updated_at = datetime('now') WHERE id = ?",
            (
                1 if is_active else 0,
                sync_source,
                sync_source,
                sync_ref,
                sync_ref,
                entry_id,
            ),
        )
        await self._db.commit()
        return WriteResult.APPLIED if cursor.rowcount else WriteResult.SKIPPED

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

    async def upsert_product_knowledge(
        self,
        youzan_item_id: str,
        title: str,
        content: str,
        keywords: str,
        priority: int,
        updated_at: str,
        *,
        sync_source: str = "",
        sync_ref: str = "",
    ) -> str:
        """原子 upsert 商品知识，并返回是否真实写入。"""
        try:
            cursor = await self._db.execute(
                "INSERT INTO knowledge_base ("
                "category, content_type, title, content, keywords, priority, youzan_item_id, "
                "is_active, last_sync_source, last_sync_ref, content_origin, "
                "vector_sync_status, vector_synced_at, updated_at"
                ") VALUES ('product', 'product', ?, ?, ?, ?, ?, 1, ?, ?, 'youzan_runtime', 'success', ?, ?) "
                "ON CONFLICT(youzan_item_id) DO UPDATE SET "
                "title = excluded.title, "
                "content = excluded.content, "
                "keywords = excluded.keywords, "
                "priority = excluded.priority, "
                "is_active = 1, "
                "last_sync_source = excluded.last_sync_source, "
                "last_sync_ref = excluded.last_sync_ref, "
                "content_type = excluded.content_type, "
                "content_origin = excluded.content_origin, "
                "vector_sync_status = excluded.vector_sync_status, "
                "vector_synced_at = excluded.vector_synced_at, "
                "vector_sync_error = '', "
                "updated_at = excluded.updated_at "
                "WHERE excluded.updated_at > knowledge_base.updated_at",
                (
                    title,
                    content,
                    keywords,
                    priority,
                    youzan_item_id,
                    sync_source,
                    sync_ref,
                    updated_at,
                    updated_at,
                ),
            )
            await self._db.commit()
            return WriteResult.APPLIED if cursor.rowcount else WriteResult.SKIPPED
        except Exception:
            return WriteResult.FAILED

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

    async def delete_product_knowledge(
        self,
        youzan_item_id: str,
        *,
        sync_source: str = "",
        sync_ref: str = "",
    ) -> str:
        """软下架商品知识，并记录最后修改来源。"""
        cursor = await self._db.execute(
            "UPDATE knowledge_base SET is_active = 0, "
            "last_sync_source = CASE WHEN ? != '' THEN ? ELSE last_sync_source END, "
            "last_sync_ref = CASE WHEN ? != '' THEN ? ELSE last_sync_ref END, "
            "vector_sync_status = 'success', "
            "vector_synced_at = datetime('now'), "
            "vector_sync_error = '', "
            "updated_at = datetime('now') WHERE youzan_item_id = ?",
            (sync_source, sync_source, sync_ref, sync_ref, youzan_item_id),
        )
        await self._db.commit()
        return WriteResult.APPLIED if cursor.rowcount else WriteResult.SKIPPED
