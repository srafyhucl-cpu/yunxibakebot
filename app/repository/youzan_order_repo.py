"""有赞订单交易数据访问层。"""

import aiosqlite

from app.models.order import YouzanOrderData


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
