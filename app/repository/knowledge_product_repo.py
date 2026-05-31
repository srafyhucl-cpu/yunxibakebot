"""知识库商品知识数据访问层。

职责：商品知识条目的 upsert、软下架和管理后台分页查询。
"""

import aiosqlite

from app.models.content_change_history import WriteResult
from app.repository.knowledge_repo import ENTRY_COLUMNS, ENTRY_SELECT_SQL

PRODUCT_CATEGORY = "product"


from app.repository.base import BaseRepository


class KnowledgeProductRepo(BaseRepository):
    """商品知识仓库：负责商品类知识的写操作和管理后台查询。"""


    @staticmethod
    def _build_product_where(
        search: str,
        is_active: int | None,
        sync_source: str,
        vector_sync_status: str,
        featured_titles: list[str] | None,
        youzan_item_id_filter: str,
        keyword_filter: str,
        item_no_filter: str = "",
    ) -> tuple[list[str], list] | None:
        """构建商品筛选 WHERE 子句与参数列表；每个字段显式加上 kb. 前缀防止联合查询中字段歧义。"""
        keyword = f"%{search}%"
        clauses: list[str] = [
            "kb.category = 'product'",
            "(kb.title LIKE ? OR kb.content LIKE ? OR kb.keywords LIKE ?)",
        ]
        params: list = [keyword, keyword, keyword]
        if is_active is not None:
            clauses.append("kb.is_active = ?")
            params.append(is_active)
        if sync_source:
            clauses.append("kb.last_sync_source = ?")
            params.append(sync_source)
        if vector_sync_status:
            clauses.append("kb.vector_sync_status = ?")
            params.append(vector_sync_status)
        if featured_titles is not None:
            if not featured_titles:
                return None
            placeholders = ",".join("?" * len(featured_titles))
            clauses.append("kb.title IN (" + placeholders + ")")
            params.extend(featured_titles)
        if youzan_item_id_filter:
            clauses.append("kb.youzan_item_id = ?")
            params.append(youzan_item_id_filter)
        if item_no_filter:
            clauses.append(
                "kb.youzan_item_id IN (SELECT CAST(item_id AS TEXT) FROM youzan_products WHERE item_no LIKE ?)"
            )
            params.append(f"%{item_no_filter}%")
        if keyword_filter:
            clauses.append("kb.keywords LIKE ?")
            params.append(f"%{keyword_filter}%")
        return clauses, params

    @staticmethod
    def _build_sort_order(sort_by: str, sort_order: str) -> str:
        """根据传入的排序参数构建 ORDER BY 子句。"""
        SORT_FIELD_MAP = {
            "title": "kb.title",
            "priority": "kb.priority",
            "is_active": "kb.is_active",
            "vector_sync_status": "kb.vector_sync_status",
            "updated_at": "kb.updated_at",
            "priceFen": "yp.price_fen",
            "stock": "yp.stock",
            "soldNum": "yp.sold_num",
            "itemNo": "yp.item_no",
        }
        db_sort_field = SORT_FIELD_MAP.get(sort_by)
        db_sort_order = "ASC" if sort_order.lower() == "asc" else "DESC"

        if db_sort_field:
            return f"ORDER BY {db_sort_field} {db_sort_order}, kb.updated_at DESC, kb.priority DESC"
        return "ORDER BY kb.updated_at DESC, kb.priority DESC"

    @staticmethod
    def _row_to_product_entry(row: dict, entry_class) -> object:
        """将联合查询出的单行数据转换为带动态挂载字段的 KnowledgeEntry。"""
        row_dict = dict(row)
        price_fen = row_dict.pop("price_fen", None)
        stock = row_dict.pop("stock", None)
        sold_num = row_dict.pop("sold_num", 0)
        item_no = row_dict.pop("item_no", "")

        entry = entry_class(**row_dict)
        # 动态挂载 youzan_products 特有字段，用以支持 API 层自愈读取
        setattr(entry, "price_fen", price_fen)
        setattr(entry, "stock", stock)
        setattr(entry, "sold_num", sold_num)
        setattr(entry, "item_no", item_no)
        return entry

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
        item_no_filter: str = "",
        sort_by: str = "",
        sort_order: str = "desc",
    ) -> list:
        """分页获取商品知识，支持多维度过滤，并通过与 youzan_products 做 LEFT JOIN 实现安全的全局排序。"""
        from app.models.knowledge import KnowledgeEntry
        result = self._build_product_where(
            search, is_active, sync_source, vector_sync_status,
            featured_titles, youzan_item_id_filter, keyword_filter,
            item_no_filter,
        )
        if result is None:
            return []
        clauses, params = result
        where = " AND ".join(clauses)
        order_clause = self._build_sort_order(sort_by, sort_order)

        sql = (
            "SELECT "
            "kb.id, kb.category, kb.content_type, kb.title, kb.content, kb.keywords, kb.priority, "
            "kb.is_active, kb.youzan_item_id, kb.last_sync_source, kb.last_sync_ref, "
            "kb.vector_sync_status, kb.updated_at, "
            "yp.price_fen, yp.stock, yp.sold_num, yp.item_no "
            "FROM knowledge_base kb "
            "LEFT JOIN youzan_products yp ON kb.youzan_item_id = CAST(yp.item_id AS TEXT) "
            f"WHERE {where} {order_clause} LIMIT ? OFFSET ?"
        )

        params.extend([limit, offset])
        rows = await self._db.execute_fetchall(sql, tuple(params))
        return [self._row_to_product_entry(r, KnowledgeEntry) for r in rows]

    async def count_products(
        self,
        search: str = "",
        is_active: int | None = None,
        sync_source: str = "",
        vector_sync_status: str = "",
        featured_titles: list[str] | None = None,
        youzan_item_id_filter: str = "",
        keyword_filter: str = "",
        item_no_filter: str = "",
    ) -> int:
        """返回商品类知识条目总数，显式加上 kb 前缀支持联合过滤。"""
        result = self._build_product_where(
            search, is_active, sync_source, vector_sync_status,
            featured_titles, youzan_item_id_filter, keyword_filter,
            item_no_filter,
        )
        if result is None:
            return 0
        clauses, params = result
        where = " AND ".join(clauses)
        rows = await self._db.execute_fetchall(
            "SELECT COUNT(*) AS c FROM knowledge_base kb WHERE " + where,
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
