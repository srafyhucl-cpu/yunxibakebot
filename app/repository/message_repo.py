"""
消息数据访问层。

按会话查询消息（用于 LLM 上下文构建）、按 channel_msg_id 去重。
"""

from uuid import uuid4
from datetime import datetime

import aiosqlite

from app.models.message import Message

MAX_MESSAGES_PER_SESSION = 50


class MessageRepo:
    """消息仓库：保存、去重检查、按会话查询。"""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def exists(self, channel_msg_id: str) -> bool:
        """根据渠道原始消息 ID 检查是否已处理（幂等去重）。"""
        if not channel_msg_id:
            return False
        row = await self._db.execute_fetchall(
            "SELECT 1 FROM messages WHERE channel_msg_id = ? LIMIT 1",
            (channel_msg_id,),
        )
        return bool(row)

    async def has_processed(self, channel_msg_id: str) -> bool:
        """检查渠道原始消息 ID 是否已经处理（别名，用于 Webhook 秒回防御）。"""
        return await self.exists(channel_msg_id)

    async def save(self, message: Message) -> None:
        """保存一条消息到数据库。"""
        msg_id = message.id or str(uuid4())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await self._db.execute(
            "INSERT INTO messages "
            "(id, session_id, role, content, channel_msg_id, "
            " estimated_tokens, tool_calls, tool_name, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (msg_id, message.session_id, message.role.value,
             message.content, message.channel_msg_id,
             message.estimated_tokens, message.tool_calls,
             message.tool_name, now),
        )
        await self._db.commit()

    async def get_by_session(self, session_id: str, limit: int = MAX_MESSAGES_PER_SESSION) -> list[Message]:
        """查询某会话的所有消息，按时间正序返回。"""
        rows = await self._db.execute_fetchall(
            "SELECT id, session_id, role, content, channel_msg_id, "
            "estimated_tokens, tool_calls, tool_name, created_at "
            "FROM messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
            (session_id, limit),
        )
        return [Message(**dict(r)) for r in rows]
