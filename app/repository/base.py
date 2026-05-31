"""Repository 基础基类。

提供 Context-Local 数据库连接的自动路由功能，消除各 Repo 文件中的重复胶水代码。
"""

import aiosqlite


class BaseRepository:
    """所有数据访问层仓库的基类。"""

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
