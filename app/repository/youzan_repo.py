"""
有赞商品与交易订单数据访问层。
"""

import aiosqlite


class YouzanProductRepo:
    """有赞商品与库存大宽表仓库。"""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def get_by_id(self, item_id: int) -> dict | None:
        """根据商品唯一 ID 获取商品数据，不存在返回 None。"""
        rows = await self._db.execute_fetchall(
            "SELECT item_id, title, alias, price_fen, stock, image, is_active, updated_at "
            "FROM youzan_products WHERE item_id = ?",
            (item_id,),
        )
        return dict(rows[0]) if rows else None

    async def get_by_alias(self, alias: str) -> dict | None:
        """根据有赞商品别名获取商品数据，不存在返回 None。"""
        rows = await self._db.execute_fetchall(
            "SELECT item_id, title, alias, price_fen, stock, image, is_active, updated_at "
            "FROM youzan_products WHERE alias = ?",
            (alias,),
        )
        return dict(rows[0]) if rows else None

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
    ) -> None:
        """
        原子化 Upsert 商品及库存数据。
        时序防线：仅当推送的 updated_at 大于库中已记录的 updated_at 时覆写。
        """
        await self._db.execute(
            "INSERT INTO youzan_products (item_id, title, alias, price_fen, stock, image, is_active, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(item_id) DO UPDATE SET "
            "    title = excluded.title, "
            "    alias = excluded.alias, "
            "    price_fen = excluded.price_fen, "
            "    stock = excluded.stock, "
            "    image = excluded.image, "
            "    is_active = excluded.is_active, "
            "    updated_at = excluded.updated_at "
            "WHERE excluded.updated_at > youzan_products.updated_at",
            (item_id, title, alias, price_fen, stock, image, is_active, updated_at),
        )
        await self._db.commit()

    async def delete_product(self, item_id: int, updated_at: str) -> None:
        """根据有赞商品 ID 软下架该商品（乐观锁）。"""
        await self._db.execute(
            "UPDATE youzan_products SET is_active = 0, updated_at = ? WHERE item_id = ? AND ? > updated_at",
            (updated_at, item_id, updated_at),
        )
        await self._db.commit()


class YouzanOrderRepo:
    """有赞订单交易大宽表仓库。"""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def get_by_order_no(self, order_no: str) -> dict | None:
        """根据订单号获取订单宽表数据，不存在返回 None。"""
        rows = await self._db.execute_fetchall(
            "SELECT order_no, buyer_id, status, amount_fen, logistics_no, "
            "logistics_status, product_titles, total_quantity, created_at, updated_at "
            "FROM youzan_orders WHERE order_no = ?",
            (order_no,),
        )
        return dict(rows[0]) if rows else None

    async def upsert_order(
        self,
        order_no: str,
        buyer_id: str,
        status: str,
        amount_fen: int,
        logistics_no: str,
        logistics_status: str,
        product_titles: str,
        total_quantity: int,
        created_at: str,
        updated_at: str,
    ) -> None:
        """
        原子化 Upsert 订单交易数据。
        时序防线：仅当推送的 updated_at 大于库中已记录的 updated_at 时覆写。
        """
        await self._db.execute(
            "INSERT INTO youzan_orders (order_no, buyer_id, status, amount_fen, logistics_no, "
            "logistics_status, product_titles, total_quantity, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(order_no) DO UPDATE SET "
            "    buyer_id = excluded.buyer_id, "
            "    status = excluded.status, "
            "    amount_fen = excluded.amount_fen, "
            "    logistics_no = excluded.logistics_no, "
            "    logistics_status = excluded.logistics_status, "
            "    product_titles = excluded.product_titles, "
            "    total_quantity = excluded.total_quantity, "
            "    updated_at = excluded.updated_at "
            "WHERE excluded.updated_at > youzan_orders.updated_at",
            (
                order_no,
                buyer_id,
                status,
                amount_fen,
                logistics_no,
                logistics_status,
                product_titles,
                total_quantity,
                created_at,
                updated_at,
            ),
        )
        await self._db.commit()
