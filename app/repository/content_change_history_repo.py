"""Repository for observability content change history."""

import aiosqlite

from app.models.content_change_history import (
    ContentChangeHistoryCreate,
    ContentChangeHistoryEntry,
)


class ContentChangeHistoryRepo:
    """Stores append-only content change records."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def add(self, entry: ContentChangeHistoryCreate) -> int:
        cursor = await self._db.execute(
            "INSERT INTO content_change_history ("
            "entity_type, entity_key, category, title, source, source_ref, "
            "session_id, webhook_msg_id, action, status, change_summary_json, "
            "error_type, error_message, occurred_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry.entity_type,
                entry.entity_key,
                entry.category,
                entry.title,
                entry.source,
                entry.source_ref,
                entry.session_id,
                entry.webhook_msg_id,
                entry.action,
                entry.status,
                entry.change_summary_json,
                entry.error_type,
                entry.error_message,
                entry.occurred_at,
            ),
        )
        await self._db.commit()
        return int(cursor.lastrowid)

    async def list_entries(
        self,
        *,
        date_from: str = "",
        date_to: str = "",
        source: str = "",
        status: str = "",
        entity_type: str = "",
        keyword: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> list[ContentChangeHistoryEntry]:
        clauses = ["1 = 1"]
        params: list[object] = []
        if date_from:
            clauses.append("occurred_at >= ?")
            params.append(f"{date_from} 00:00:00")
        if date_to:
            clauses.append("occurred_at <= ?")
            params.append(f"{date_to} 23:59:59")
        if source:
            clauses.append("source = ?")
            params.append(source)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if entity_type:
            clauses.append("entity_type = ?")
            params.append(entity_type)
        if keyword:
            like = f"%{keyword}%"
            clauses.append("(title LIKE ? OR entity_key LIKE ? OR change_summary_json LIKE ?)")
            params.extend([like, like, like])
        rows = await self._db.execute_fetchall(
            "SELECT id, entity_type, entity_key, category, title, source, source_ref, "
            "session_id, webhook_msg_id, action, status, change_summary_json, "
            "error_type, error_message, occurred_at "
            "FROM content_change_history "
            f"WHERE {' AND '.join(clauses)} "
            "ORDER BY occurred_at DESC, id DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
        return [ContentChangeHistoryEntry(**dict(row)) for row in rows]

    async def count_entries(
        self,
        *,
        date_from: str = "",
        date_to: str = "",
        source: str = "",
        status: str = "",
        entity_type: str = "",
        keyword: str = "",
    ) -> int:
        clauses = ["1 = 1"]
        params: list[object] = []
        if date_from:
            clauses.append("occurred_at >= ?")
            params.append(f"{date_from} 00:00:00")
        if date_to:
            clauses.append("occurred_at <= ?")
            params.append(f"{date_to} 23:59:59")
        if source:
            clauses.append("source = ?")
            params.append(source)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if entity_type:
            clauses.append("entity_type = ?")
            params.append(entity_type)
        if keyword:
            like = f"%{keyword}%"
            clauses.append("(title LIKE ? OR entity_key LIKE ? OR change_summary_json LIKE ?)")
            params.extend([like, like, like])
        rows = await self._db.execute_fetchall(
            "SELECT COUNT(*) AS c FROM content_change_history "
            f"WHERE {' AND '.join(clauses)}",
            tuple(params),
        )
        return int(rows[0]["c"]) if rows else 0

    async def get_by_id(self, entry_id: int) -> ContentChangeHistoryEntry | None:
        rows = await self._db.execute_fetchall(
            "SELECT id, entity_type, entity_key, category, title, source, source_ref, "
            "session_id, webhook_msg_id, action, status, change_summary_json, "
            "error_type, error_message, occurred_at "
            "FROM content_change_history WHERE id = ?",
            (entry_id,),
        )
        return ContentChangeHistoryEntry(**dict(rows[0])) if rows else None

    async def list_for_entity(
        self,
        *,
        entity_type: str,
        entity_key: str,
        limit: int = 20,
    ) -> list[ContentChangeHistoryEntry]:
        rows = await self._db.execute_fetchall(
            "SELECT id, entity_type, entity_key, category, title, source, source_ref, "
            "session_id, webhook_msg_id, action, status, change_summary_json, "
            "error_type, error_message, occurred_at "
            "FROM content_change_history "
            "WHERE entity_type = ? AND entity_key = ? "
            "ORDER BY occurred_at DESC, id DESC LIMIT ?",
            (entity_type, entity_key, limit),
        )
        return [ContentChangeHistoryEntry(**dict(row)) for row in rows]
