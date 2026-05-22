"""
共享测试夹具。

提供内存 SQLite 连接，每个测试函数独享一个完整 schema 的干净数据库
（包含动态迁移列），测试结束后自动关闭，互不干扰。
"""

from collections.abc import AsyncGenerator

import aiosqlite
import pytest

from app.database import close_db, init_db


@pytest.fixture
async def db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """每个测试独享的内存 SQLite 连接，通过 init_db 完整初始化（含动态迁移）。"""
    conn = await init_db(":memory:")
    yield conn
    await close_db(conn)
