"""Repository 基础基类。

提供 Context-Local 数据库连接的自动路由功能，消除各 Repo 文件中的重复胶水代码。
"""

from collections.abc import Sequence
from typing import Any

import aiosqlite


class DatabaseHandle:
    """仓库层所需的数据库连接适配器。"""

    def __init__(self, connection: aiosqlite.Connection) -> None:
        self._connection = connection

    async def execute(self, sql: str, parameters: Sequence[object] = ()) -> Any:
        return await self._connection.execute(sql, parameters)

    async def execute_fetchall(
        self, sql: str, parameters: Sequence[object] = ()
    ) -> list[dict[str, Any]]:
        rows = await self._connection.execute_fetchall(sql, parameters)
        return [dict(row) for row in rows]

    async def commit(self) -> None:
        await self._connection.commit()

    async def rollback(self) -> None:
        await self._connection.rollback()

    async def close(self) -> None:
        await self._connection.close()


class BaseRepository:
    """所有数据访问层仓库的基类。"""

    def __init__(self, db: DatabaseHandle | None = None) -> None:
        self._injected_db = db

    @property
    def _db(self) -> DatabaseHandle:
        if self._injected_db is not None:
            return self._injected_db
        try:
            from app.database import db_conn_var

            return db_conn_var.get()
        except LookupError as exc:
            raise RuntimeError(
                "数据库操作未在 db_session_scope 上下文管理器中执行！"
            ) from exc
