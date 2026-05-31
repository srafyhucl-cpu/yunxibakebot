"""
会话数据访问层。

管理会话的 CRUD 操作，包括自动创建新会话、按用户查找活跃会话。
"""

from uuid import uuid4
from datetime import datetime

import aiosqlite

from app.models.session import Session, SessionCreate, SessionStatus


class SessionRepo:
    """会话仓库：查询、创建、更新会话状态。"""

    def __init__(self, db: aiosqlite.Connection = None) -> None:
        self._injected_db = db

    @property
    def _db(self) -> aiosqlite.Connection:
        if self._injected_db is not None:
            return self._injected_db
        try:
            from app.database import db_conn_var
            return db_conn_var.get()
        except LookupError as exc:
            raise RuntimeError("数据库操作未在 db_session_scope 上下文管理器中执行！") from exc

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
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        val = status.value
        await self._db.execute(
            "UPDATE sessions SET status = ?, updated_at = ? WHERE id = ?",
            (val, now, session_id),
        )
        await self._db.commit()

    async def get_all_active(self) -> list[Session]:
        """获取所有活跃会话。"""
        rows = await self._db.execute_fetchall(
            "SELECT id, channel, user_id, staff_id, status, extra_info, created_at, updated_at "
            "FROM sessions WHERE status IN ('active', 'transfer_pending', 'human_service') "
            "ORDER BY updated_at DESC",
        )
        return [Session(**dict(r)) for r in rows]

    async def get_recent(self, limit: int = 10) -> list[Session]:
        """获取最近创建的会话。"""
        rows = await self._db.execute_fetchall(
            "SELECT id, channel, user_id, staff_id, status, extra_info, created_at, updated_at "
            "FROM sessions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [Session(**dict(r)) for r in rows]

    async def update_extra(self, session_id: str, extra_info: str) -> None:
        """更新会话的 extra_info 字段。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await self._db.execute(
            "UPDATE sessions SET extra_info = ?, updated_at = ? WHERE id = ?",
            (extra_info, now, session_id),
        )
        await self._db.commit()

    async def get_all_by_channel(self, channel: str, limit: int = 100) -> list[Session]:
        """获取指定渠道所有未关闭的会话，按更新时间降序排列。"""
        rows = await self._db.execute_fetchall(
            "SELECT id, channel, user_id, staff_id, status, extra_info, created_at, updated_at "
            "FROM sessions WHERE channel = ? AND status != 'closed' "
            "ORDER BY updated_at DESC LIMIT ?",
            (channel, limit),
        )
        return [Session(**dict(r)) for r in rows]

    async def get_named(self, channel: str = "", limit: int = 50) -> list[Session]:
        """获取有自定义名称的活跃会话（用于列表展示，已丢弃的不显示）。"""
        rows = await self._db.execute_fetchall(
            "SELECT id, channel, user_id, staff_id, status, extra_info, created_at, updated_at "
            "FROM sessions WHERE extra_info LIKE '%\"name\"%' AND status != 'closed' "
            "AND (? = '' OR channel = ?) "
            "ORDER BY updated_at DESC LIMIT ?",
            (channel, channel, limit),
        )
        return [Session(**dict(r)) for r in rows]
