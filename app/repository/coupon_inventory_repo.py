"""优惠券库存数据访问层。"""

from app.models.member import CouponInventoryEntry
from app.repository.base import BaseRepository
from app.utils import now_str


class CouponInventoryRepo(BaseRepository):
    """优惠券生命周期记录仓储（coupon_id+status+mobile 组合去重）。"""

    async def get_by_dedup_key(
        self, coupon_id: str, status: str, mobile: str
    ) -> dict | None:
        """按组合去重键读取优惠券记录。"""
        if not coupon_id or not status:
            return None
        rows = await self._db.execute_fetchall(
            "SELECT id, coupon_id, coupon_group_id, customer_id, mobile, status, "
            "order_no, title, value_fen, detail_json, source, occurred_at, created_at "
            "FROM coupon_inventory "
            "WHERE coupon_id = ? AND status = ? AND mobile = ? LIMIT 1",
            (coupon_id, status, mobile),
        )
        return rows[0] if rows else None

    async def insert(self, entry: CouponInventoryEntry) -> None:
        """写入一条优惠券生命周期记录。"""
        await self._db.execute(
            "INSERT INTO coupon_inventory (coupon_id, coupon_group_id, customer_id, "
            "mobile, status, order_no, title, value_fen, detail_json, source, "
            "occurred_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry.coupon_id,
                entry.coupon_group_id,
                entry.customer_id,
                entry.mobile,
                entry.status,
                entry.order_no,
                entry.title,
                entry.value_fen,
                entry.detail_json,
                entry.source,
                entry.occurred_at,
                now_str(),
            ),
        )
        await self._db.commit()
