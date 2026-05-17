"""
会话数据访问层。

管理会话的 CRUD 操作，包括自动创建新会话、按用户查找活跃会话。
"""

from uuid import uuid4
from datetime import datetime, timezone

import aiosqlite

from app.models.session import Session, SessionCreate, SessionStatus


class SessionRepo:
    """会话仓库：查询、创建、更新会话状态。"""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def get(self, session_id: str) -> Session | None:
        """根据 ID 获取会话，不存在时返回 None。"""
        row = await self._db.execute_fetchall(
            "SELECT id, channel, user_id, staff_id, status, "
            "extra_info, created_at, updated_at "
            "FROM sessions WHERE id = ?",
            (session_id,),
        )
        if not row:
            return None
        return Session(**dict(row[0]))

    async def get_active(self, user_id: str, channel: str) -> Session | None:
        """查找该用户在指定渠道的活跃会话（未 closed）。"""
        row = await self._db.execute_fetchall(
            "SELECT id, channel, user_id, staff_id, status, "
            "extra_info, created_at, updated_at "
            "FROM sessions "
            "WHERE user_id = ? AND channel = ? "
            "AND status IN ('active', 'transfer_pending', 'human_service') "
            "ORDER BY created_at DESC LIMIT 1",
            (user_id, channel),
        )
        if not row:
            return None
        return Session(**dict(row[0]))

    async def get_or_create(self, data: SessionCreate) -> Session:
        """获取活跃会话，不存在则创建新会话。"""
        existing = await self.get_active(data.user_id, data.channel)
        if existing:
            return existing
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        session_id = data.id or str(uuid4())
        await self._db.execute(
            "INSERT INTO sessions (id, channel, user_id, staff_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, data.channel, data.user_id, data.staff_id, now, now),
        )
        await self._db.commit()
        return Session(
            id=session_id,
            channel=data.channel,
            user_id=data.user_id,
            staff_id=data.staff_id,
            created_at=now,
            updated_at=now,
        )

    async def update_status(self, session_id: str, status: SessionStatus) -> None:
        """更新会话状态并记录时间戳。"""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        await self._db.execute(
            "UPDATE sessions SET status = ?, updated_at = ? WHERE id = ?",
            (status.value, now, session_id),
        )
        await self._db.commit()
