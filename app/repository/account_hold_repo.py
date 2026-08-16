"""资金/积分预占（account_hold）数据访问层（D1-A）。

预占绑定不可变 member_balance_id；结算消费（active→consumed）、
取消/超时释放（active→released）均按尝试整体推进，条件更新保证
双连接并发不重复消费/释放。账务仓储零自提交（B3.5 合同）。
"""

from app.repository.base import BaseRepository
from app.utils import now_str


class AccountHoldRepo(BaseRepository):
    """预占仓储（hold_key 幂等）。"""

    async def reserve(
        self,
        *,
        hold_key: str,
        subject_type: str,
        subject_id: str,
        payment_attempt_id: int,
        asset_type: str,
        amount_fen: int,
        member_balance_id: int | None,
        expires_at: str | None = None,
    ) -> bool:
        """写入一条预占；同 hold_key 幂等，返回是否新增。"""
        timestamp = now_str()
        cursor = await self._db.execute(
            "INSERT OR IGNORE INTO account_hold "
            "(hold_key, subject_type, subject_id, payment_attempt_id, asset_type, "
            "amount_fen, member_balance_id, status, expires_at, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)",
            (
                hold_key,
                subject_type,
                subject_id,
                payment_attempt_id,
                asset_type,
                amount_fen,
                member_balance_id,
                expires_at,
                timestamp,
                timestamp,
            ),
        )
        return int(cursor.rowcount or 0) > 0

    async def list_active_by_attempt(self, payment_attempt_id: int) -> list[dict]:
        """读取尝试的活跃预占。"""
        return await self._db.execute_fetchall(
            "SELECT id, hold_key, subject_type, subject_id, payment_attempt_id, "
            "asset_type, amount_fen, member_balance_id, status, expires_at, "
            "created_at, updated_at FROM account_hold "
            "WHERE payment_attempt_id = ? AND status = 'active' ORDER BY id ASC",
            (payment_attempt_id,),
        )

    async def consume_by_attempt(self, payment_attempt_id: int) -> int:
        """结算消费：全部 active 预占 → consumed；返回消费条数。"""
        cursor = await self._db.execute(
            "UPDATE account_hold SET status = 'consumed', updated_at = ? "
            "WHERE payment_attempt_id = ? AND status = 'active'",
            (now_str(), payment_attempt_id),
        )
        return int(cursor.rowcount or 0)

    async def release_by_attempt(self, payment_attempt_id: int) -> int:
        """取消/超时释放：全部 active 预占 → released；返回释放条数。"""
        cursor = await self._db.execute(
            "UPDATE account_hold SET status = 'released', updated_at = ? "
            "WHERE payment_attempt_id = ? AND status = 'active'",
            (now_str(), payment_attempt_id),
        )
        return int(cursor.rowcount or 0)

    async def list_by_attempt(self, payment_attempt_id: int) -> list[dict]:
        """读取尝试的全部预占（含已消费/已释放）。"""
        return await self._db.execute_fetchall(
            "SELECT id, hold_key, subject_type, subject_id, payment_attempt_id, "
            "asset_type, amount_fen, member_balance_id, status, expires_at, "
            "created_at, updated_at FROM account_hold "
            "WHERE payment_attempt_id = ? ORDER BY id ASC",
            (payment_attempt_id,),
        )


__all__ = ["AccountHoldRepo"]
