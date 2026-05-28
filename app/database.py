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
        content_type TEXT NOT NULL DEFAULT 'faq',
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        keywords TEXT DEFAULT '',
        priority INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        last_sync_source TEXT DEFAULT 'admin_manual',
        last_sync_ref TEXT DEFAULT '',
        content_origin TEXT DEFAULT 'admin_manual',
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT '',
        suggested_category TEXT DEFAULT '',
        suggest_reason TEXT DEFAULT '',
        vector_sync_status TEXT DEFAULT 'pending',
        vector_synced_at TEXT DEFAULT '',
        vector_sync_error TEXT DEFAULT '',
        vector_sync_retry_count INTEGER DEFAULT 0,
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
        last_sync_source TEXT DEFAULT 'product_reconcile',
        last_sync_ref TEXT DEFAULT '',
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
        pay_time TEXT DEFAULT '',
        consign_time TEXT DEFAULT '',
        pay_type_str TEXT DEFAULT '',
        express_type INTEGER DEFAULT 0,
        refund_state INTEGER DEFAULT 0,
        post_fee_fen INTEGER DEFAULT 0,
        discount_fen INTEGER DEFAULT 0,
        delivery_province TEXT DEFAULT '',
        delivery_city TEXT DEFAULT '',
        delivery_district TEXT DEFAULT '',
        delivery_time TEXT DEFAULT '',
        outer_user_id TEXT DEFAULT '',
        order_items_json TEXT DEFAULT '[]',
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
    # youzan_webhook_events
    """CREATE TABLE IF NOT EXISTS youzan_webhook_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        msg_id TEXT NOT NULL UNIQUE,
        trace_id TEXT DEFAULT '',
        event_type TEXT DEFAULT '',
        business_type TEXT NOT NULL
            CHECK(business_type IN ('trade','item','chat','unknown')),
        business_key TEXT DEFAULT '',
        status TEXT NOT NULL
            CHECK(status IN ('received','processing','processed','skipped','failed','duplicate')),
        http_status INTEGER DEFAULT 200,
        process_stage TEXT DEFAULT '',
        error_type TEXT DEFAULT '',
        error_message TEXT DEFAULT '',
        payload_hash TEXT DEFAULT '',
        payload_summary_json TEXT DEFAULT '{}',
        received_at TEXT NOT NULL,
        process_started_at TEXT,
        process_finished_at TEXT,
        duration_ms INTEGER,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_ywe_received ON youzan_webhook_events(received_at)",
    "CREATE INDEX IF NOT EXISTS idx_ywe_status ON youzan_webhook_events(status)",
    "CREATE INDEX IF NOT EXISTS idx_ywe_event_type ON youzan_webhook_events(event_type)",
    "CREATE INDEX IF NOT EXISTS idx_ywe_business_key ON youzan_webhook_events(business_key)",
    # content_change_history（内容变更历史）
    """CREATE TABLE IF NOT EXISTS content_change_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT NOT NULL
            CHECK(entity_type IN ('product','knowledge')),
        entity_key TEXT NOT NULL,
        category TEXT DEFAULT '',
        title TEXT DEFAULT '',
        source TEXT NOT NULL,
        source_ref TEXT DEFAULT '',
        session_id TEXT DEFAULT '',
        webhook_msg_id TEXT DEFAULT '',
        action TEXT DEFAULT '',
        status TEXT NOT NULL
            CHECK(status IN ('success','failed')),
        change_summary_json TEXT DEFAULT '{}',
        error_type TEXT DEFAULT '',
        error_message TEXT DEFAULT '',
        occurred_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_cch_occurred ON content_change_history(occurred_at)",
    "CREATE INDEX IF NOT EXISTS idx_cch_source ON content_change_history(source)",
    "CREATE INDEX IF NOT EXISTS idx_cch_status ON content_change_history(status)",
    "CREATE INDEX IF NOT EXISTS idx_cch_entity ON content_change_history(entity_type, entity_key)",
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
        if "last_sync_source" not in columns:
            await conn.execute("ALTER TABLE knowledge_base ADD COLUMN last_sync_source TEXT DEFAULT 'admin_manual'")
            await conn.execute(
                "UPDATE knowledge_base SET last_sync_source = 'admin_manual' "
                "WHERE last_sync_source IS NULL OR last_sync_source = ''"
            )
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 knowledge_base 新增 last_sync_source 列")
        if "last_sync_ref" not in columns:
            await conn.execute("ALTER TABLE knowledge_base ADD COLUMN last_sync_ref TEXT DEFAULT ''")
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 knowledge_base 新增 last_sync_ref 列")
        if "content_type" not in columns:
            await conn.execute("ALTER TABLE knowledge_base ADD COLUMN content_type TEXT DEFAULT 'faq'")
            await conn.execute(
                "UPDATE knowledge_base SET content_type = CASE "
                "WHEN category = 'product' THEN 'product' "
                "WHEN category = 'faq' THEN 'faq' "
                "ELSE 'rule' END "
                "WHERE content_type IS NULL OR content_type = ''"
            )
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 knowledge_base 新增 content_type 列")
        if "content_origin" not in columns:
            await conn.execute("ALTER TABLE knowledge_base ADD COLUMN content_origin TEXT DEFAULT 'admin_manual'")
            await conn.execute(
                "UPDATE knowledge_base SET content_origin = 'admin_manual' "
                "WHERE content_origin IS NULL OR content_origin = ''"
            )
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 knowledge_base 新增 content_origin 列")
        if "created_by" not in columns:
            await conn.execute("ALTER TABLE knowledge_base ADD COLUMN created_by TEXT DEFAULT ''")
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 knowledge_base 新增 created_by 列")
        if "updated_by" not in columns:
            await conn.execute("ALTER TABLE knowledge_base ADD COLUMN updated_by TEXT DEFAULT ''")
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 knowledge_base 新增 updated_by 列")
        if "suggested_category" not in columns:
            await conn.execute("ALTER TABLE knowledge_base ADD COLUMN suggested_category TEXT DEFAULT ''")
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 knowledge_base 新增 suggested_category 列")
        if "suggest_reason" not in columns:
            await conn.execute("ALTER TABLE knowledge_base ADD COLUMN suggest_reason TEXT DEFAULT ''")
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 knowledge_base 新增 suggest_reason 列")
        if "vector_sync_status" not in columns:
            await conn.execute("ALTER TABLE knowledge_base ADD COLUMN vector_sync_status TEXT DEFAULT 'pending'")
            await conn.execute(
                "UPDATE knowledge_base SET vector_sync_status = CASE "
                "WHEN is_active = 1 THEN 'success' "
                "ELSE 'pending' END "
                "WHERE vector_sync_status IS NULL OR vector_sync_status = ''"
            )
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 knowledge_base 新增 vector_sync_status 列")
        if "vector_synced_at" not in columns:
            await conn.execute("ALTER TABLE knowledge_base ADD COLUMN vector_synced_at TEXT DEFAULT ''")
            await conn.execute(
                "UPDATE knowledge_base SET vector_synced_at = updated_at "
                "WHERE is_active = 1 AND (vector_synced_at IS NULL OR vector_synced_at = '')"
            )
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 knowledge_base 新增 vector_synced_at 列")
        if "vector_sync_error" not in columns:
            await conn.execute("ALTER TABLE knowledge_base ADD COLUMN vector_sync_error TEXT DEFAULT ''")
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 knowledge_base 新增 vector_sync_error 列")
        if "vector_sync_retry_count" not in columns:
            await conn.execute("ALTER TABLE knowledge_base ADD COLUMN vector_sync_retry_count INTEGER DEFAULT 0")
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 knowledge_base 新增 vector_sync_retry_count 列")
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
        if "last_sync_source" not in yp_columns:
            await conn.execute("ALTER TABLE youzan_products ADD COLUMN last_sync_source TEXT DEFAULT 'product_reconcile'")
            await conn.execute(
                "UPDATE youzan_products SET last_sync_source = 'product_reconcile' "
                "WHERE last_sync_source IS NULL OR last_sync_source = ''"
            )
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 youzan_products 表新增 last_sync_source 列")
        if "last_sync_ref" not in yp_columns:
            await conn.execute("ALTER TABLE youzan_products ADD COLUMN last_sync_ref TEXT DEFAULT ''")
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 youzan_products 表新增 last_sync_ref 列")
        if "sold_num" not in yp_columns:
            await conn.execute("ALTER TABLE youzan_products ADD COLUMN sold_num INTEGER DEFAULT 0")
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 youzan_products 表新增 sold_num 列")
    except Exception as exc:
        logger.warning("动态校准 youzan_products 表字段发生异常：%s", exc)

    # 动态微创迁移：为现存 youzan_orders 表补充扩展字段
    _YO_EXTRA_COLUMNS: list[tuple[str, str]] = [
        ("pay_time", "ALTER TABLE youzan_orders ADD COLUMN pay_time TEXT DEFAULT ''"),
        ("consign_time", "ALTER TABLE youzan_orders ADD COLUMN consign_time TEXT DEFAULT ''"),
        ("pay_type_str", "ALTER TABLE youzan_orders ADD COLUMN pay_type_str TEXT DEFAULT ''"),
        ("express_type", "ALTER TABLE youzan_orders ADD COLUMN express_type INTEGER DEFAULT 0"),
        ("refund_state", "ALTER TABLE youzan_orders ADD COLUMN refund_state INTEGER DEFAULT 0"),
        ("post_fee_fen", "ALTER TABLE youzan_orders ADD COLUMN post_fee_fen INTEGER DEFAULT 0"),
        ("discount_fen", "ALTER TABLE youzan_orders ADD COLUMN discount_fen INTEGER DEFAULT 0"),
        ("delivery_province", "ALTER TABLE youzan_orders ADD COLUMN delivery_province TEXT DEFAULT ''"),
        ("delivery_city", "ALTER TABLE youzan_orders ADD COLUMN delivery_city TEXT DEFAULT ''"),
        ("delivery_district", "ALTER TABLE youzan_orders ADD COLUMN delivery_district TEXT DEFAULT ''"),
        ("delivery_time", "ALTER TABLE youzan_orders ADD COLUMN delivery_time TEXT DEFAULT ''"),
        ("outer_user_id", "ALTER TABLE youzan_orders ADD COLUMN outer_user_id TEXT DEFAULT ''"),
        ("order_items_json", "ALTER TABLE youzan_orders ADD COLUMN order_items_json TEXT DEFAULT '[]'"),
    ]
    try:
        async with conn.execute("PRAGMA table_info(youzan_orders)") as cursor:
            yo_cols = {row["name"] for row in await cursor.fetchall()}
        added: list[str] = []
        for col_name, alter_sql in _YO_EXTRA_COLUMNS:
            if col_name not in yo_cols:
                await conn.execute(alter_sql)
                added.append(col_name)
        if added:
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：youzan_orders 新增列 %s", added)
    except Exception as exc:
        logger.warning("动态校准 youzan_orders 表字段发生异常：%s", exc)

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
