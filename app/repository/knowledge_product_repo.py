"""知识库商品知识数据访问层。

职责：商品知识条目的 upsert、软下架和管理后台分页查询。
"""

import aiosqlite

from app.models.content_change_history import WriteResult
from app.repository.knowledge_repo import ENTRY_COLUMNS, ENTRY_SELECT_SQL

PRODUCT_CATEGORY = "product"


class KnowledgeProductRepo:
    """商品知识仓库：负责商品类知识的写操作和管理后台查询。"""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    @staticmethod
    def _build_product_where(
        search: str,
        is_active: int | None,
        sync_source: str,
        vector_sync_status: str,
        featured_titles: list[str] | None,
        youzan_item_id_filter: str,
        keyword_filter: str,
    ) -> tuple[list[str], list] | None:
        """构建商品筛选 WHERE 子句与参数列表；featured_titles 为空列表时返回 None 表示结果必为空。"""
        keyword = f"%{search}%"
        clauses: list[str] = [
            "category = 'product'",
            "(title LIKE ? OR content LIKE ? OR keywords LIKE ?)",
        ]
        params: list = [keyword, keyword, keyword]
        if is_active is not None:
            clauses.append("is_active = ?")
            params.append(is_active)
        if sync_source:
            clauses.append("last_sync_source = ?")
            params.append(sync_source)
        if vector_sync_status:
            clauses.append("vector_sync_status = ?")
            params.append(vector_sync_status)
        if featured_titles is not None:
            if not featured_titles:
                return None
            placeholders = ",".join("?" * len(featured_titles))
            clauses.append("title IN (" + placeholders + ")")
            params.extend(featured_titles)
        if youzan_item_id_filter:
            clauses.append("youzan_item_id = ?")
            params.append(youzan_item_id_filter)
        if keyword_filter:
            clauses.append("keywords LIKE ?")
            params.append(f"%{keyword_filter}%")
        return clauses, params

    async def get_all_products(
        self,
        search: str = "",
        limit: int = 50,
        offset: int = 0,
        is_active: int | None = None,
        sync_source: str = "",
        vector_sync_status: str = "",
        featured_titles: list[str] | None = None,
        youzan_item_id_filter: str = "",
        keyword_filter: str = "",
    ) -> list:
        """分页获取商品类知识条目（仅 category=product），支持关键词、状态、来源、AI同步状态筛选。"""
        from app.models.knowledge import KnowledgeEntry
        result = self._build_product_where(
            search, is_active, sync_source, vector_sync_status,
            featured_titles, youzan_item_id_filter, keyword_filter,
        )
        if result is None:
            return []
        clauses, params = result
        where = " AND ".join(clauses)
        params.extend([limit, offset])
        rows = await self._db.execute_fetchall(
            ENTRY_SELECT_SQL + f"WHERE {where} ORDER BY updated_at DESC, priority DESC LIMIT ? OFFSET ?",
            tuple(params),
        )
        return [KnowledgeEntry(**dict(row)) for row in rows]

    async def count_products(
        self,
        search: str = "",
        is_active: int | None = None,
        sync_source: str = "",
        vector_sync_status: str = "",
        featured_titles: list[str] | None = None,
        youzan_item_id_filter: str = "",
        keyword_filter: str = "",
    ) -> int:
        """返回商品类知识条目总数（仅 category=product），支持筛选。"""
        result = self._build_product_where(
            search, is_active, sync_source, vector_sync_status,
            featured_titles, youzan_item_id_filter, keyword_filter,
        )
        if result is None:
            return 0
        clauses, params = result
        where = " AND ".join(clauses)
        rows = await self._db.execute_fetchall(
            "SELECT COUNT(*) AS c FROM knowledge_base WHERE " + where,
            tuple(params),
        )
        return int(rows[0]["c"]) if rows else 0

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
