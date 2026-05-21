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
    # youzan_products (有赞商品与实时库存大宽表)
    """CREATE TABLE IF NOT EXISTS youzan_products (
        item_id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        alias TEXT NOT NULL UNIQUE,
        price_fen INTEGER NOT NULL,
        stock INTEGER NOT NULL,
        image TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        skus_json TEXT DEFAULT '[]',
        item_props_json TEXT DEFAULT '[]',
        desc TEXT DEFAULT '',
        tags TEXT DEFAULT '',
        updated_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_yp_title ON youzan_products(title)",
    "CREATE INDEX IF NOT EXISTS idx_yp_alias ON youzan_products(alias)",
    # youzan_orders (有赞交易订单大宽表)
    """CREATE TABLE IF NOT EXISTS youzan_orders (
        order_no TEXT PRIMARY KEY,
        buyer_id TEXT NOT NULL,
        status TEXT NOT NULL,
        amount_fen INTEGER NOT NULL,
        logistics_no TEXT DEFAULT '',
        logistics_status TEXT DEFAULT '',
        product_titles TEXT NOT NULL,
        total_quantity INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_yo_status ON youzan_orders(status)",
    "CREATE INDEX IF NOT EXISTS idx_yo_buyer ON youzan_orders(buyer_id)",
    # analytics_events (分析埋点日志物理大宽表)
    """CREATE TABLE IF NOT EXISTS analytics_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        buyer_id TEXT,
        event_type TEXT NOT NULL,
        event_source TEXT NOT NULL,
        ref_id TEXT,
        meta_data TEXT DEFAULT '{}',
        created_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_ae_type ON analytics_events(event_type)",
    "CREATE INDEX IF NOT EXISTS idx_ae_session ON analytics_events(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_ae_buyer ON analytics_events(buyer_id)",
    "CREATE INDEX IF NOT EXISTS idx_ae_created ON analytics_events(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_events_attribution_flow ON analytics_events(buyer_id, event_type, created_at)",
]

PRAGMA_STATEMENTS: list[str] = [
    "PRAGMA journal_mode = WAL",
    "PRAGMA busy_timeout = 5000",
    "PRAGMA foreign_keys = ON",
    "PRAGMA auto_vacuum = INCREMENTAL",
]


async def init_db(db_path: str) -> aiosqlite.Connection:
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    for pragma in PRAGMA_STATEMENTS:
        await conn.execute(pragma)
    for stmt in SCHEMA_STATEMENTS:
        await conn.execute(stmt)
    await conn.commit()

    # 动态微创迁移：为现存 knowledge_base 表注入 youzan_item_id 唯一索引用以支撑原子级 ON CONFLICT 写入
    try:
        async with conn.execute("PRAGMA table_info(knowledge_base)") as cursor:
            columns = [row["name"] for row in await cursor.fetchall()]
        if "youzan_item_id" not in columns:
            await conn.execute("ALTER TABLE knowledge_base ADD COLUMN youzan_item_id TEXT DEFAULT NULL")
            await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_kb_youzan_item_id ON knowledge_base(youzan_item_id)")
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 knowledge_base 新增 youzan_item_id 唯一约束列")
    except Exception as exc:
        logger.warning("动态校准 RAG 知识库表字段发生异常（可能已被成功迁移或表尚为空）：%s", exc)

    # 动态微创迁移：为现存 youzan_products 表注入 skus_json, desc, tags 丰富商品画像
    try:
        async with conn.execute("PRAGMA table_info(youzan_products)") as cursor:
            yp_columns = [row["name"] for row in await cursor.fetchall()]
        if "skus_json" not in yp_columns:
            await conn.execute("ALTER TABLE youzan_products ADD COLUMN skus_json TEXT DEFAULT '[]'")
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 youzan_products 表新增 skus_json 列")
        if "desc" not in yp_columns:
            await conn.execute("ALTER TABLE youzan_products ADD COLUMN desc TEXT DEFAULT ''")
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 youzan_products 表新增 desc 列")
        if "tags" not in yp_columns:
            await conn.execute("ALTER TABLE youzan_products ADD COLUMN tags TEXT DEFAULT ''")
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 youzan_products 表新增 tags 列")
        if "item_props_json" not in yp_columns:
            await conn.execute("ALTER TABLE youzan_products ADD COLUMN item_props_json TEXT DEFAULT '[]'")
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 youzan_products 表新增 item_props_json 列")
    except Exception as exc:
        logger.warning("动态校准 youzan_products 表字段发生异常：%s", exc)

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
