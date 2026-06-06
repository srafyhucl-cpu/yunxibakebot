"""
数据库初始化与管理。

职责：
- 启动时创建所有表与索引（WAL 模式）
- 数据库 Schema 定义存放在 app/migrations/schema.py
- 运行时微创迁移逻辑在本文件维护
- 提供连接生命周期管理
- 所有 repository 层共用同一个连接
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar

import aiosqlite

from app.config import settings
from app.logger import setup_logger
from app.migrations.schema import SCHEMA_STATEMENTS, PRAGMA_STATEMENTS

logger = setup_logger()


async def init_db(db_path: str) -> aiosqlite.Connection:
    """初始化数据库：建表 + 索引 + 版本化迁移。"""
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    for pragma in PRAGMA_STATEMENTS:
        await conn.execute(pragma)
    for stmt in SCHEMA_STATEMENTS:
        await conn.execute(stmt)
    await conn.commit()

    # 执行版本化增量迁移（含动态迁移逻辑）
    from app.migrations.runner import run_migrations

    await run_migrations(conn)

    logger.info("Database initialized at %s", db_path)
    return conn


async def close_db(conn: aiosqlite.Connection) -> None:
    await conn.close()
    logger.info("Database connection closed")


@asynccontextmanager
async def get_connection(db_path: str) -> AsyncGenerator[aiosqlite.Connection, None]:
    conn = await init_db(db_path)
    try:
        yield conn
    finally:
        await close_db(conn)


# Context-Local 数据库连接上下文变量
db_conn_var: ContextVar[aiosqlite.Connection] = ContextVar("db_connection")


@asynccontextmanager
async def db_session_scope(
    db_path: str = None,
) -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    异步上下文管理器：生命周期内绑定一个独立的 aiosqlite.Connection 并绑定到 ContextVar 中。
    自动处理事务提交与回滚。
    """
    path = db_path or settings.DB_PATH
    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row
    for pragma in PRAGMA_STATEMENTS:
        await conn.execute(pragma)

    token = db_conn_var.set(conn)
    try:
        yield conn
        await conn.commit()
    except Exception as exc:
        await conn.rollback()
        logger.error("数据库事务出错，已回滚: %s", exc)
        raise
    finally:
        db_conn_var.reset(token)
        await conn.close()


async def get_db_session() -> AsyncGenerator[aiosqlite.Connection, None]:
    """FastAPI 依赖注入项，为单个 HTTP 请求获取并隔离数据库连接。"""
    async with db_session_scope() as conn:
        yield conn
