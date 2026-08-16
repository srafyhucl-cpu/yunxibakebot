"""账务出站事件（accounting_outbox）数据访问层（D1-A）。

order.settled / order.released 等账务事实的出站投递队列，D1-C 由 provider
工单（预下单 / 关单 / 退款）消费。claim / complete / fail 一律条件更新
（lease_token / attempt CAS）；depends_on_operation_key 非空时前置行必须
存在且 succeeded 才允许投递（B3.5 合同）。账务仓储零自提交（B3.5 合同）。
"""

from app.repository.base import BaseRepository
from app.utils import now_str

OUTBOX_STATUSES = ("pending", "processing", "succeeded", "failed", "dead_letter")


class AccountingOutboxRepo(BaseRepository):
    """账务出站事件仓储（operation_key 幂等）。"""

    async def enqueue(
        self,
        *,
        operation_key: str,
        operation_type: str,
        subject_type: str,
        subject_id: str,
        payload_json: str,
        depends_on_operation_key: str = "",
    ) -> bool:
        """写入一条出站事件；同 operation_key 幂等，返回是否新增。"""
        timestamp = now_str()
        cursor = await self._db.execute(
            "INSERT OR IGNORE INTO accounting_outbox "
            "(operation_key, operation_type, subject_type, subject_id, payload_json, "
            "status, attempt_count, depends_on_operation_key, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?)",
            (
                operation_key,
                operation_type,
                subject_type,
                subject_id,
                payload_json,
                depends_on_operation_key,
                timestamp,
                timestamp,
            ),
        )
        return int(cursor.rowcount or 0) > 0

    async def get_by_operation_key(self, operation_key: str) -> dict | None:
        """按幂等键读取出站事件。"""
        rows = await self._db.execute_fetchall(
            "SELECT id, operation_key, operation_type, subject_type, subject_id, "
            "payload_json, status, attempt_count, lease_token, lease_until, "
            "depends_on_operation_key, last_error, created_at, updated_at "
            "FROM accounting_outbox WHERE operation_key = ? LIMIT 1",
            (operation_key,),
        )
        return rows[0] if rows else None

    async def claim(self, operation_key: str) -> bool:
        """CAS：pending → processing（写租约，D1-C 投递工单使用）。"""
        timestamp = now_str()
        cursor = await self._db.execute(
            "UPDATE accounting_outbox SET status = 'processing', "
            "attempt_count = attempt_count + 1, lease_token = ?, lease_until = ?, "
            "updated_at = ? WHERE operation_key = ? AND status = 'pending'",
            (operation_key, timestamp, timestamp, operation_key),
        )
        return int(cursor.rowcount or 0) == 1

    async def mark_succeeded(
        self, operation_key: str, expected_token: str = ""
    ) -> bool:
        """CAS：处理成功 → succeeded（陈旧 worker 拒绝覆盖）。"""
        if expected_token:
            cursor = await self._db.execute(
                "UPDATE accounting_outbox SET status = 'succeeded', "
                "lease_token = '', lease_until = NULL, updated_at = ? "
                "WHERE operation_key = ? AND status = 'processing' "
                "AND lease_token = ?",
                (now_str(), operation_key, expected_token),
            )
        else:
            cursor = await self._db.execute(
                "UPDATE accounting_outbox SET status = 'succeeded', "
                "lease_token = '', lease_until = NULL, updated_at = ? "
                "WHERE operation_key = ? AND status IN ('pending', 'processing')",
                (now_str(), operation_key),
            )
        return int(cursor.rowcount or 0) == 1

    async def mark_failed(
        self, operation_key: str, error: str, expected_token: str = ""
    ) -> bool:
        """CAS：处理失败 → failed（保留重试；陈旧 worker 拒绝覆盖）。"""
        if expected_token:
            cursor = await self._db.execute(
                "UPDATE accounting_outbox SET status = 'failed', "
                "lease_token = '', lease_until = NULL, last_error = ?, updated_at = ? "
                "WHERE operation_key = ? AND status = 'processing' AND lease_token = ?",
                (error[:500], now_str(), operation_key, expected_token),
            )
        else:
            cursor = await self._db.execute(
                "UPDATE accounting_outbox SET status = 'failed', "
                "lease_token = '', lease_until = NULL, last_error = ?, updated_at = ? "
                "WHERE operation_key = ? AND status IN ('pending', 'processing')",
                (error[:500], now_str(), operation_key),
            )
        return int(cursor.rowcount or 0) == 1

    async def dependency_satisfied(self, operation_key: str) -> bool:
        """前置依赖检查：依赖行必须存在且 succeeded（B3.5 fail-closed 合同）。"""
        if not operation_key:
            return True
        row = await self.get_by_operation_key(operation_key)
        return row is not None and row["status"] == "succeeded"

    async def list_by_status(self, status: str) -> list[dict]:
        """按状态读取出站事件（投递扫描）。"""
        return await self._db.execute_fetchall(
            "SELECT id, operation_key, operation_type, subject_type, subject_id, "
            "payload_json, status, attempt_count, lease_token, lease_until, "
            "depends_on_operation_key, last_error, created_at, updated_at "
            "FROM accounting_outbox WHERE status = ? ORDER BY id ASC",
            (status,),
        )


__all__ = ["OUTBOX_STATUSES", "AccountingOutboxRepo"]
