"""有赞商品与交易订单数据访问层。"""

import aiosqlite

from app.models.content_change_history import WriteResult
from app.models.order import YouzanOrderData


class YouzanProductRepo:
    """有赞商品与库存大宽表仓库。"""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def get_by_id(self, item_id: int) -> dict | None:
        """根据商品唯一 ID 获取商品数据。"""
        rows = await self._db.execute_fetchall(
            "SELECT item_id, title, alias, price_fen, stock, image, is_active, "
            "skus_json, item_props_json, desc, tags, last_sync_source, last_sync_ref, updated_at "
            "FROM youzan_products WHERE item_id = ?",
            (item_id,),
        )
        return dict(rows[0]) if rows else None

    async def get_by_alias(self, alias: str) -> dict | None:
        """根据有赞商品别名获取商品数据。"""
        rows = await self._db.execute_fetchall(
            "SELECT item_id, title, alias, price_fen, stock, image, is_active, "
            "skus_json, item_props_json, desc, tags, last_sync_source, last_sync_ref, updated_at "
            "FROM youzan_products WHERE alias = ?",
            (alias,),
        )
        return dict(rows[0]) if rows else None

    async def list_current_products(
        self,
        *,
        keyword: str = "",
        is_active: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """分页获取当前商品宽表内容。"""
        clauses = ["1 = 1"]
        params: list[object] = []
        if keyword:
            like = f"%{keyword}%"
            clauses.append("(title LIKE ? OR alias LIKE ? OR tags LIKE ?)")
            params.extend([like, like, like])
        if is_active in {"0", "1"}:
            clauses.append("is_active = ?")
            params.append(int(is_active))
        rows = await self._db.execute_fetchall(
            "SELECT item_id, title, alias, price_fen, stock, image, is_active, "
            "skus_json, item_props_json, desc, tags, last_sync_source, last_sync_ref, updated_at "
            "FROM youzan_products "
            f"WHERE {' AND '.join(clauses)} "
            "ORDER BY updated_at DESC, item_id DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
        return [dict(row) for row in rows]

    async def count_current_products(self, *, keyword: str = "", is_active: str = "") -> int:
        """返回当前商品宽表筛选后的总数。"""
        clauses = ["1 = 1"]
        params: list[object] = []
        if keyword:
            like = f"%{keyword}%"
            clauses.append("(title LIKE ? OR alias LIKE ? OR tags LIKE ?)")
            params.extend([like, like, like])
        if is_active in {"0", "1"}:
            clauses.append("is_active = ?")
            params.append(int(is_active))
        rows = await self._db.execute_fetchall(
            "SELECT COUNT(*) AS c FROM youzan_products "
            f"WHERE {' AND '.join(clauses)}",
            tuple(params),
        )
        return int(rows[0]["c"]) if rows else 0

    async def upsert_product(
        self,
        item_id: int,
        title: str,
        alias: str,
        price_fen: int,
        stock: int,
        image: str,
        is_active: int,
        updated_at: str,
        skus_json: str = "[]",
        item_props_json: str = "[]",
        desc: str = "",
        tags: str = "",
        *,
        sync_source: str = "",
        sync_ref: str = "",
    ) -> str:
        """原子化 upsert 商品数据，并返回是否真实写入。"""
        try:
            cursor = await self._db.execute(
                "INSERT INTO youzan_products ("
                "item_id, title, alias, price_fen, stock, image, is_active, "
                "skus_json, item_props_json, desc, tags, last_sync_source, last_sync_ref, updated_at"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(item_id) DO UPDATE SET "
                "title = excluded.title, "
                "alias = excluded.alias, "
                "price_fen = excluded.price_fen, "
                "stock = excluded.stock, "
                "image = excluded.image, "
                "is_active = excluded.is_active, "
                "skus_json = excluded.skus_json, "
                "item_props_json = excluded.item_props_json, "
                "desc = excluded.desc, "
                "tags = excluded.tags, "
                "last_sync_source = excluded.last_sync_source, "
                "last_sync_ref = excluded.last_sync_ref, "
                "updated_at = excluded.updated_at "
                "WHERE excluded.updated_at > youzan_products.updated_at",
                (
                    item_id,
                    title,
                    alias,
                    price_fen,
                    stock,
                    image,
                    is_active,
                    skus_json,
                    item_props_json,
                    desc,
                    tags,
                    sync_source,
                    sync_ref,
                    updated_at,
                ),
            )
            await self._db.commit()
            return WriteResult.APPLIED if cursor.rowcount else WriteResult.SKIPPED
        except Exception:
            return WriteResult.FAILED

    async def delete_product(
        self,
        item_id: int,
        updated_at: str,
        *,
        sync_source: str = "",
        sync_ref: str = "",
    ) -> str:
        """根据有赞商品 ID 软下架商品，并记录最后修改来源。"""
        cursor = await self._db.execute(
            "UPDATE youzan_products SET is_active = 0, "
            "last_sync_source = CASE WHEN ? != '' THEN ? ELSE last_sync_source END, "
            "last_sync_ref = CASE WHEN ? != '' THEN ? ELSE last_sync_ref END, "
            "updated_at = ? WHERE item_id = ? AND ? > updated_at",
            (sync_source, sync_source, sync_ref, sync_ref, updated_at, item_id, updated_at),
        )
        await self._db.commit()
        return WriteResult.APPLIED if cursor.rowcount else WriteResult.SKIPPED


class YouzanOrderRepo:
    """有赞订单交易大宽表仓库。"""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def get_by_order_no(self, order_no: str) -> dict | None:
        """根据订单号获取订单宽表数据。"""
        rows = await self._db.execute_fetchall(
            "SELECT order_no, buyer_id, status, amount_fen, logistics_no, "
            "logistics_status, product_titles, total_quantity, "
            "pay_time, consign_time, pay_type_str, express_type, refund_state, "
            "post_fee_fen, discount_fen, delivery_province, delivery_city, "
            "delivery_district, delivery_time, outer_user_id, order_items_json, "
            "created_at, updated_at "
            "FROM youzan_orders WHERE order_no = ?",
            (order_no,),
        )
        return dict(rows[0]) if rows else None

    async def upsert_order(self, data: YouzanOrderData) -> None:
        """原子化 upsert 订单交易数据。"""
        await self._db.execute(
            "INSERT INTO youzan_orders ("
            "order_no, buyer_id, status, amount_fen, logistics_no, logistics_status, "
            "product_titles, total_quantity, pay_time, consign_time, pay_type_str, "
            "express_type, refund_state, post_fee_fen, discount_fen, "
            "delivery_province, delivery_city, delivery_district, delivery_time, "
            "outer_user_id, order_items_json, created_at, updated_at"
            ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(order_no) DO UPDATE SET "
            "buyer_id = excluded.buyer_id, "
            "status = excluded.status, "
            "amount_fen = excluded.amount_fen, "
            "logistics_no = excluded.logistics_no, "
            "logistics_status = excluded.logistics_status, "
            "product_titles = excluded.product_titles, "
            "total_quantity = excluded.total_quantity, "
            "pay_time = excluded.pay_time, "
            "consign_time = excluded.consign_time, "
            "pay_type_str = excluded.pay_type_str, "
            "express_type = excluded.express_type, "
            "refund_state = excluded.refund_state, "
            "post_fee_fen = excluded.post_fee_fen, "
            "discount_fen = excluded.discount_fen, "
            "delivery_province = excluded.delivery_province, "
            "delivery_city = excluded.delivery_city, "
            "delivery_district = excluded.delivery_district, "
            "delivery_time = excluded.delivery_time, "
            "outer_user_id = excluded.outer_user_id, "
            "order_items_json = excluded.order_items_json, "
            "updated_at = excluded.updated_at "
            "WHERE excluded.updated_at > youzan_orders.updated_at",
            (
                data.order_no,
                data.buyer_id,
                data.status,
                data.amount_fen,
                data.logistics_no,
                data.logistics_status,
                data.product_titles,
                data.total_quantity,
                data.pay_time,
                data.consign_time,
                data.pay_type_str,
                data.express_type,
                data.refund_state,
                data.post_fee_fen,
                data.discount_fen,
                data.delivery_province,
                data.delivery_city,
                data.delivery_district,
                data.delivery_time,
                data.outer_user_id,
                data.order_items_json,
                data.created_at,
                data.updated_at,
            ),
        )
        await self._db.commit()
