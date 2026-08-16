"""奖励积分扣回欠账（refund_shortfall_debt）数据访问层（B3.5，评审问题 3）。

已结算退款收回奖励积分时余额不足（clawback 扣减返回 None），不得静默跳过：
写入欠账（operation_key 幂等，与退款操作事实关联），补偿未终结前
保留事实快照供重试；人工补足后由对账工序结清（status open→settled）。

D1-A（评审问题 3 闭环）：欠账支持**部分偿还**（remaining 单调递减，version
CAS 条件更新，重复偿还幂等）与 **open→settled 条件结案**；后续积分入账
按 min(入账额, remaining) 原子优先偿债（见 PointsPaymentService）。
"""

from app.repository.base import BaseRepository
from app.utils import now_str


class RefundShortfallDebtRepo(BaseRepository):
    """奖励积分扣回欠账仓储（只追加，operation_key 幂等）。"""

    async def append(
        self,
        *,
        order_id: str,
        mobile: str,
        member_balance_id: int | None,
        operation_key: str,
        amount: int,
        note: str = "",
    ) -> bool:
        """追加一条欠账；同 operation_key 幂等，返回是否新增。"""
        timestamp = now_str()
        cursor = await self._db.execute(
            "INSERT OR IGNORE INTO refund_shortfall_debt "
            "(order_id, mobile, member_balance_id, operation_key, amount, remaining, "
            "status, note, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?)",
            (
                order_id,
                mobile,
                member_balance_id,
                operation_key,
                amount,
                amount,
                note,
                timestamp,
                timestamp,
            ),
        )
        return int(cursor.rowcount or 0) > 0

    async def get_by_operation_key(self, operation_key: str) -> dict | None:
        """按操作幂等键读取欠账。"""
        rows = await self._db.execute_fetchall(
            "SELECT id, order_id, mobile, member_balance_id, operation_key, amount, "
            "remaining, status, version, note, created_at, updated_at "
            "FROM refund_shortfall_debt WHERE operation_key = ? LIMIT 1",
            (operation_key,),
        )
        return rows[0] if rows else None

    async def list_open_by_order(self, order_id: str) -> list[dict]:
        """读取某订单未结清的欠账。"""
        return await self._db.execute_fetchall(
            "SELECT id, order_id, mobile, member_balance_id, operation_key, amount, "
            "remaining, status, version, note, created_at, updated_at "
            "FROM refund_shortfall_debt WHERE order_id = ? AND status = 'open' "
            "ORDER BY id ASC",
            (order_id,),
        )

    async def list_open_by_member_balance_id(
        self, member_balance_id: int
    ) -> list[dict]:
        """读取某账户未结清的欠账（入账优先偿债扫描，D1-A）。"""
        return await self._db.execute_fetchall(
            "SELECT id, order_id, mobile, member_balance_id, operation_key, amount, "
            "remaining, status, version, note, created_at, updated_at "
            "FROM refund_shortfall_debt WHERE member_balance_id = ? "
            "AND status = 'open' AND remaining > 0 ORDER BY id ASC",
            (member_balance_id,),
        )

    async def repay(
        self,
        debt_id: int,
        expected_version: int,
        amount: int,
    ) -> bool:
        """部分偿还：remaining 单调递减（version CAS，重复偿还幂等失败）。"""
        cursor = await self._db.execute(
            "UPDATE refund_shortfall_debt SET remaining = remaining - ?, "
            "version = version + 1, updated_at = ? "
            "WHERE id = ? AND status = 'open' AND version = ? AND remaining >= ?",
            (amount, now_str(), debt_id, expected_version, amount),
        )
        return int(cursor.rowcount or 0) == 1

    async def settle_if_fully_repaid(
        self,
        debt_id: int,
        expected_version: int,
    ) -> bool:
        """结案：remaining 归零后 open→settled（version CAS）。"""
        cursor = await self._db.execute(
            "UPDATE refund_shortfall_debt SET status = 'settled', remaining = 0, "
            "version = version + 1, updated_at = ? "
            "WHERE id = ? AND status = 'open' AND version = ? AND remaining = 0",
            (now_str(), debt_id, expected_version),
        )
        return int(cursor.rowcount or 0) == 1


__all__ = ["RefundShortfallDebtRepo"]
