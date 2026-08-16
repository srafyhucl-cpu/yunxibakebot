"""支付尝试（payment_attempt）数据访问层（D1-A）。

支付尝试是结算命令的事实源与幂等源：mock / 余额订单结算先创建尝试
（subject-slot 部分唯一索引保证单主体单活跃尝试），状态迁移一律条件更新
（WHERE status AND state_version），双连接并发恰一次结算由 CAS 兜底。
账务仓储零自提交（B3.5 合同），提交边界由调用方统一 UoW 持有。
"""

from app.repository.base import BaseRepository
from app.utils import now_str

ATTEMPT_STATUS_ACTIVE = (
    "draft",
    "prepay_requested",
    "prepay_unknown",
    "prepay_ready",
    "settling",
    "settling_retry",
    "manual_review",
)

ATTEMPT_SETTLE_FROM = ("prepay_ready", "settling_retry")


class PaymentAttemptRepo(BaseRepository):
    """支付尝试仓储。"""

    async def create_active(
        self,
        *,
        subject_type: str,
        subject_id: str,
        provider: str,
        merchant_order_no: str,
        snapshot_json: str,
        snapshot_hash: str,
        member_balance_id: int | None,
    ) -> dict | None:
        """创建活跃尝试（prepay_ready）；subject-slot 冲突（并发）返回 None。"""
        timestamp = now_str()
        cursor = await self._db.execute(
            "INSERT OR IGNORE INTO payment_attempt "
            "(subject_type, subject_id, provider, merchant_order_no, "
            "payment_snapshot_json, snapshot_hash, member_balance_id, status, "
            "active_command_type, state_version, prepay_started_at, created_at, "
            "updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'prepay_ready', '', 1, ?, ?, ?)",
            (
                subject_type,
                subject_id,
                provider,
                merchant_order_no,
                snapshot_json,
                snapshot_hash,
                member_balance_id,
                timestamp,
                timestamp,
                timestamp,
            ),
        )
        if int(cursor.rowcount or 0) != 1:
            return None
        return await self.get_active(subject_type, subject_id)

    async def get_active(self, subject_type: str, subject_id: str) -> dict | None:
        """按 subject-slot 读取活跃尝试（最多一条）。"""
        # IN 占位符数量动态化（状态枚举长度），仅拼接 ? 序列，SQL 文本静态
        placeholders = ",".join("?" for _ in ATTEMPT_STATUS_ACTIVE)
        rows = await self._db.execute_fetchall(
            "SELECT id, subject_type, subject_id, provider, merchant_order_no, "
            "payment_snapshot_json, snapshot_hash, member_balance_id, status, "
            "active_command_type, lease_token, lease_until, state_version, "
            "prepay_started_at, settled_at, last_error, created_at, updated_at "
            "FROM payment_attempt WHERE subject_type = ? AND subject_id = ? "
            "AND status IN (" + placeholders + ") ORDER BY id DESC LIMIT 1",
            (subject_type, subject_id, *ATTEMPT_STATUS_ACTIVE),
        )
        return rows[0] if rows else None

    async def get_latest(self, subject_type: str, subject_id: str) -> dict | None:
        """按 subject 读取最近一条尝试（含终态，D1-A 幂等重放判定用）。"""
        rows = await self._db.execute_fetchall(
            "SELECT id, subject_type, subject_id, provider, merchant_order_no, "
            "payment_snapshot_json, snapshot_hash, member_balance_id, status, "
            "active_command_type, lease_token, lease_until, state_version, "
            "prepay_started_at, settled_at, last_error, created_at, updated_at "
            "FROM payment_attempt WHERE subject_type = ? AND subject_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (subject_type, subject_id),
        )
        return rows[0] if rows else None

    async def get_by_id(self, attempt_id: int) -> dict | None:
        """按主键读取尝试。"""
        rows = await self._db.execute_fetchall(
            "SELECT id, subject_type, subject_id, provider, merchant_order_no, "
            "payment_snapshot_json, snapshot_hash, member_balance_id, status, "
            "active_command_type, lease_token, lease_until, state_version, "
            "prepay_started_at, settled_at, last_error, created_at, updated_at "
            "FROM payment_attempt WHERE id = ? LIMIT 1",
            (attempt_id,),
        )
        return rows[0] if rows else None

    async def begin_settle(self, attempt_id: int, expected_version: int) -> bool:
        """CAS：prepay_ready / settling_retry → settling（双连接恰一次）。"""
        cursor = await self._db.execute(
            "UPDATE payment_attempt SET status = 'settling', updated_at = ?, "
            "state_version = state_version + 1, last_error = '' "
            "WHERE id = ? AND status IN ('prepay_ready', 'settling_retry') "
            "AND state_version = ?",
            (now_str(), attempt_id, expected_version),
        )
        return int(cursor.rowcount or 0) == 1

    async def complete_settle(self, attempt_id: int, expected_version: int) -> bool:
        """CAS：settling → succeeded（settled_at 落定）。"""
        timestamp = now_str()
        cursor = await self._db.execute(
            "UPDATE payment_attempt SET status = 'succeeded', settled_at = ?, "
            "updated_at = ?, state_version = state_version + 1, last_error = '' "
            "WHERE id = ? AND status = 'settling' AND state_version = ?",
            (timestamp, timestamp, attempt_id, expected_version),
        )
        return int(cursor.rowcount or 0) == 1

    async def mark_retry(
        self, attempt_id: int, expected_version: int, error: str
    ) -> bool:
        """CAS：未进入终态的活跃尝试（prepay_ready / settling_retry）→
        settling_retry（结算失败保持预占，可重放）。

        结算 UoW 回滚后状态已复原（回到 begin_settle 前），调用方须先重读
        尝试取回滚后的当前版本再传 expected_version。
        """
        cursor = await self._db.execute(
            "UPDATE payment_attempt SET status = 'settling_retry', updated_at = ?, "
            "state_version = state_version + 1, last_error = ? "
            "WHERE id = ? AND status IN ('prepay_ready', 'settling_retry') "
            "AND state_version = ?",
            (now_str(), error[:500], attempt_id, expected_version),
        )
        return int(cursor.rowcount or 0) == 1

    async def release(
        self,
        attempt_id: int,
        expected_version: int,
        to_status: str,
        reason: str,
    ) -> bool:
        """CAS：未结算尝试（prepay_ready / settling_retry / 无副作用的
        manual_review）→ cancelled / expired。

        服务层按状态矩阵裁决（D1-A 复核 P5）：订单未置 paid 的 manual_review
        可释放；已产生资产副作用的仅可人工结案，不调用本方法。
        """
        cursor = await self._db.execute(
            "UPDATE payment_attempt SET status = ?, updated_at = ?, "
            "state_version = state_version + 1, last_error = ? "
            "WHERE id = ? AND status IN "
            "('prepay_ready', 'settling_retry', 'manual_review') "
            "AND state_version = ?",
            (to_status, now_str(), reason[:500], attempt_id, expected_version),
        )
        return int(cursor.rowcount or 0) == 1

    async def mark_failed_preclaim(
        self,
        attempt_id: int,
        expected_version: int,
        error: str,
    ) -> bool:
        """CAS：prepay_ready → failed（未进入结算的前置失败，如预占不足，B3.5 合同）。"""
        cursor = await self._db.execute(
            "UPDATE payment_attempt SET status = 'failed', updated_at = ?, "
            "state_version = state_version + 1, last_error = ? "
            "WHERE id = ? AND status = 'prepay_ready' AND state_version = ?",
            (now_str(), error[:500], attempt_id, expected_version),
        )
        return int(cursor.rowcount or 0) == 1

    async def upsert_leg(
        self,
        attempt_id: int,
        asset_type: str,
        amount_fen: int,
    ) -> None:
        """写入尝试腿（预占额明细）；同 (attempt_id, asset_type) 幂等。"""
        cursor = await self._db.execute(
            "INSERT OR IGNORE INTO payment_attempt_leg "
            "(payment_attempt_id, asset_type, amount_fen, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'reserved', ?, ?)",
            (attempt_id, asset_type, amount_fen, now_str(), now_str()),
        )
        if int(cursor.rowcount or 0) == 0:
            return
        await self._db.execute(
            "UPDATE payment_attempt_leg SET amount_fen = ?, updated_at = ? "
            "WHERE payment_attempt_id = ? AND asset_type = ?",
            (amount_fen, now_str(), attempt_id, asset_type),
        )

    async def mark_legs_consumed(self, attempt_id: int) -> int:
        """结算消费：全部 reserved 腿 → consumed。"""
        cursor = await self._db.execute(
            "UPDATE payment_attempt_leg SET status = 'consumed', updated_at = ? "
            "WHERE payment_attempt_id = ? AND status = 'reserved'",
            (now_str(), attempt_id),
        )
        return int(cursor.rowcount or 0)

    async def mark_legs_released(self, attempt_id: int) -> int:
        """取消/超时释放：全部 reserved 腿 → released。"""
        cursor = await self._db.execute(
            "UPDATE payment_attempt_leg SET status = 'released', updated_at = ? "
            "WHERE payment_attempt_id = ? AND status = 'reserved'",
            (now_str(), attempt_id),
        )
        return int(cursor.rowcount or 0)

    async def list_legs(self, attempt_id: int) -> list[dict]:
        """读取尝试全部腿。"""
        return await self._db.execute_fetchall(
            "SELECT id, payment_attempt_id, asset_type, amount_fen, status, "
            "created_at, updated_at FROM payment_attempt_leg "
            "WHERE payment_attempt_id = ? ORDER BY id ASC",
            (attempt_id,),
        )

    async def mark_manual_review(
        self, attempt_id: int, expected_version: int, reason: str
    ) -> bool:
        """CAS：→ manual_review（账户缺失等阻断，未解除前禁止同主体新尝试）。"""
        cursor = await self._db.execute(
            "UPDATE payment_attempt SET status = 'manual_review', updated_at = ?, "
            "state_version = state_version + 1, last_error = ? "
            "WHERE id = ? AND status IN ('prepay_ready', 'settling', 'settling_retry') "
            "AND state_version = ?",
            (now_str(), reason[:500], attempt_id, expected_version),
        )
        return int(cursor.rowcount or 0) == 1


__all__ = [
    "ATTEMPT_STATUS_ACTIVE",
    "ATTEMPT_SETTLE_FROM",
    "PaymentAttemptRepo",
]
