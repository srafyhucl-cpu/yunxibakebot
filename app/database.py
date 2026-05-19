"""
数据库初始化与管理。

职责：
- 启动时创建所有表与索引（WAL 模式）
- 提供连接生命周期管理
- 所有 repository 层共用同一个连接
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aiosqlite

from app.logger import setup_logger

logger = setup_logger()

SCHEMA_STATEMENTS: list[str] = [
    # sessions
    """CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        channel TEXT NOT NULL,
        user_id TEXT NOT NULL,
        staff_id TEXT DEFAULT '',
        status TEXT DEFAULT 'active'
            CHECK(status IN ('active','transfer_pending','human_service','closed')),
        extra_info TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)",
    # messages
    """CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES sessions(id),
        role TEXT NOT NULL CHECK(role IN ('user','assistant','system','tool')),
        content TEXT NOT NULL DEFAULT '',
        channel_msg_id TEXT DEFAULT '',
        estimated_tokens INTEGER DEFAULT 0,
        tool_calls TEXT DEFAULT '[]',
        tool_name TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_messages_ymid ON messages(channel_msg_id)",
    # knowledge_base
    """CREATE TABLE IF NOT EXISTS knowledge_base (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL
            CHECK(category IN ('store_info','product','policy','faq','after_sales')),
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        keywords TEXT DEFAULT '',
        priority INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_kb_category ON knowledge_base(category)",
    # human_transfers
    """CREATE TABLE IF NOT EXISTS human_transfers (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES sessions(id),
        user_id TEXT NOT NULL,
        staff_id TEXT DEFAULT '',
        reason TEXT DEFAULT '',
        status TEXT DEFAULT 'pending'
            CHECK(status IN ('pending','accepted','rejected','closed')),
        conversation_summary TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now')),
        accepted_at TEXT,
        closed_at TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS idx_transfers_session ON human_transfers(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_transfers_status ON human_transfers(status)",
    # orders
    """CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES sessions(id),
        channel TEXT NOT NULL,
        user_id TEXT NOT NULL,
        products TEXT NOT NULL,
        total_amount REAL DEFAULT 0,
        delivery TEXT DEFAULT '{}',
        status TEXT DEFAULT 'pending'
            CHECK(status IN ('pending','confirmed','making','delivering','done','cancelled')),
        remark TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_orders_session ON orders(session_id)",
    # shop_config
    """CREATE TABLE IF NOT EXISTS shop_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT DEFAULT (datetime('now'))
    )""",
]

PRAGMA_STATEMENTS: list[str] = [
    "PRAGMA journal_mode = WAL",
    "PRAGMA busy_timeout = 5000",
    "PRAGMA foreign_keys = ON",
]


async def init_db(db_path: str) -> aiosqlite.Connection:
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    for pragma in PRAGMA_STATEMENTS:
        await conn.execute(pragma)
    for stmt in SCHEMA_STATEMENTS:
        await conn.execute(stmt)
    await conn.commit()
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
