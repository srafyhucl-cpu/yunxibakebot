"""积分退款对账修正清单数据访问层（只追加）。"""

from app.repository.base import BaseRepository
from app.utils import now_str


class PointsRefundReconcileRepo(BaseRepository):
    """积分退款异常对账清单仓储（append-only，幂等追加）。"""

    async def append(
        self,
        *,
        order_id: str,
        mobile: str,
        unique_id: str,
        reason: str,
        amount: int,
        note: str,
    ) -> bool:
        """追加一条异常记录；同订单同原因幂等，返回是否新增。"""
        timestamp = now_str()
        cursor = await self._db.execute(
            "INSERT OR IGNORE INTO points_refund_reconcile "
            "(order_id, mobile, unique_id, reason, amount, status, note, "
            "created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?)",
            (order_id, mobile, unique_id, reason, amount, note, timestamp, timestamp),
        )
        rowcount = int(cursor.rowcount or 0)
        return rowcount > 0

    async def list_open(self, *, limit: int = 100) -> list[dict]:
        """读取待处理异常记录（status='open'），按 id 升序。"""
        return await self._db.execute_fetchall(
            "SELECT id, order_id, mobile, unique_id, reason, amount, status, note, "
            "created_at, updated_at "
            "FROM points_refund_reconcile WHERE status = 'open' "
            "ORDER BY id ASC LIMIT ?",
            (limit,),
        )

    async def close_open(self, *, order_id: str, reason: str) -> bool:
        """人工核对后关闭指定原因的对账案件（open→closed，幂等）。

        B3.4（评审问题 2）：案件必须可关闭、可审计——事实字段只追加不修改，
        仅 status 允许 open→closed 生命周期流转。
        """
        cursor = await self._db.execute(
            "UPDATE points_refund_reconcile SET status = 'closed', updated_at = ? "
            "WHERE order_id = ? AND reason = ? AND status = 'open'",
            (now_str(), order_id, reason),
        )
        rowcount = int(cursor.rowcount or 0)
        return rowcount > 0


__all__ = ["PointsRefundReconcileRepo"]
