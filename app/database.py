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
    """初始化数据库：建表 + 索引 + 动态微创迁移。"""
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    for pragma in PRAGMA_STATEMENTS:
        await conn.execute(pragma)
    for stmt in SCHEMA_STATEMENTS:
        await conn.execute(stmt)
    await conn.commit()

    # 动态微创迁移：为现存 knowledge_base 表注入 youzan_item_id 唯一索引
    try:
        async with conn.execute("PRAGMA table_info(knowledge_base)") as cursor:
            columns = [row["name"] for row in await cursor.fetchall()]
        if "youzan_item_id" not in columns:
            await conn.execute(
                "ALTER TABLE knowledge_base ADD COLUMN youzan_item_id TEXT DEFAULT NULL"
            )
            await conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_kb_youzan_item_id ON knowledge_base(youzan_item_id)"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 knowledge_base 新增 youzan_item_id 唯一约束列"
            )
        if "last_sync_source" not in columns:
            await conn.execute(
                "ALTER TABLE knowledge_base ADD COLUMN last_sync_source TEXT DEFAULT 'admin_manual'"
            )
            await conn.execute(
                "UPDATE knowledge_base SET last_sync_source = 'admin_manual' "
                "WHERE last_sync_source IS NULL OR last_sync_source = ''"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 knowledge_base 新增 last_sync_source 列"
            )
        if "last_sync_ref" not in columns:
            await conn.execute(
                "ALTER TABLE knowledge_base ADD COLUMN last_sync_ref TEXT DEFAULT ''"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 knowledge_base 新增 last_sync_ref 列"
            )
        if "content_type" not in columns:
            await conn.execute(
                "ALTER TABLE knowledge_base ADD COLUMN content_type TEXT DEFAULT 'faq'"
            )
            await conn.execute(
                "UPDATE knowledge_base SET content_type = CASE "
                "WHEN category = 'product' THEN 'product' "
                "WHEN category = 'faq' THEN 'faq' "
                "ELSE 'rule' END "
                "WHERE content_type IS NULL OR content_type = ''"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 knowledge_base 新增 content_type 列"
            )
        if "content_origin" not in columns:
            await conn.execute(
                "ALTER TABLE knowledge_base ADD COLUMN content_origin TEXT DEFAULT 'admin_manual'"
            )
            await conn.execute(
                "UPDATE knowledge_base SET content_origin = 'admin_manual' "
                "WHERE content_origin IS NULL OR content_origin = ''"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 knowledge_base 新增 content_origin 列"
            )
        if "created_by" not in columns:
            await conn.execute(
                "ALTER TABLE knowledge_base ADD COLUMN created_by TEXT DEFAULT ''"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 knowledge_base 新增 created_by 列"
            )
        if "updated_by" not in columns:
            await conn.execute(
                "ALTER TABLE knowledge_base ADD COLUMN updated_by TEXT DEFAULT ''"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 knowledge_base 新增 updated_by 列"
            )
        if "suggested_category" not in columns:
            await conn.execute(
                "ALTER TABLE knowledge_base ADD COLUMN suggested_category TEXT DEFAULT ''"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 knowledge_base 新增 suggested_category 列"
            )
        if "suggest_reason" not in columns:
            await conn.execute(
                "ALTER TABLE knowledge_base ADD COLUMN suggest_reason TEXT DEFAULT ''"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 knowledge_base 新增 suggest_reason 列"
            )
        if "vector_sync_status" not in columns:
            await conn.execute(
                "ALTER TABLE knowledge_base ADD COLUMN vector_sync_status TEXT DEFAULT 'pending'"
            )
            await conn.execute(
                "UPDATE knowledge_base SET vector_sync_status = CASE "
                "WHEN is_active = 1 THEN 'success' "
                "ELSE 'pending' END "
                "WHERE vector_sync_status IS NULL OR vector_sync_status = ''"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 knowledge_base 新增 vector_sync_status 列"
            )
        if "vector_synced_at" not in columns:
            await conn.execute(
                "ALTER TABLE knowledge_base ADD COLUMN vector_synced_at TEXT DEFAULT ''"
            )
            await conn.execute(
                "UPDATE knowledge_base SET vector_synced_at = updated_at "
                "WHERE is_active = 1 AND (vector_synced_at IS NULL OR vector_synced_at = '')"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 knowledge_base 新增 vector_synced_at 列"
            )
        if "vector_sync_error" not in columns:
            await conn.execute(
                "ALTER TABLE knowledge_base ADD COLUMN vector_sync_error TEXT DEFAULT ''"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 knowledge_base 新增 vector_sync_error 列"
            )
        if "vector_sync_retry_count" not in columns:
            await conn.execute(
                "ALTER TABLE knowledge_base ADD COLUMN vector_sync_retry_count INTEGER DEFAULT 0"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 knowledge_base 新增 vector_sync_retry_count 列"
            )
    except Exception as exc:
        logger.warning(
            "动态校准 RAG 知识库表字段发生异常（可能已被成功迁移或表尚为空）：%s", exc
        )

    # 动态微创迁移：为现存 youzan_products 表注入扩展列
    try:
        async with conn.execute("PRAGMA table_info(youzan_products)") as cursor:
            yp_columns = [row["name"] for row in await cursor.fetchall()]
        if "skus_json" not in yp_columns:
            await conn.execute(
                "ALTER TABLE youzan_products ADD COLUMN skus_json TEXT DEFAULT '[]'"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 youzan_products 表新增 skus_json 列"
            )
        if "desc" not in yp_columns:
            await conn.execute(
                "ALTER TABLE youzan_products ADD COLUMN desc TEXT DEFAULT ''"
            )
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 youzan_products 表新增 desc 列")
        if "tags" not in yp_columns:
            await conn.execute(
                "ALTER TABLE youzan_products ADD COLUMN tags TEXT DEFAULT ''"
            )
            await conn.commit()
            logger.info("已完成 SQLite 微创迁移：成功为 youzan_products 表新增 tags 列")
        if "item_props_json" not in yp_columns:
            await conn.execute(
                "ALTER TABLE youzan_products ADD COLUMN item_props_json TEXT DEFAULT '[]'"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 youzan_products 表新增 item_props_json 列"
            )
        if "last_sync_source" not in yp_columns:
            await conn.execute(
                "ALTER TABLE youzan_products ADD COLUMN last_sync_source TEXT DEFAULT 'product_reconcile'"
            )
            await conn.execute(
                "UPDATE youzan_products SET last_sync_source = 'product_reconcile' "
                "WHERE last_sync_source IS NULL OR last_sync_source = ''"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 youzan_products 表新增 last_sync_source 列"
            )
        if "last_sync_ref" not in yp_columns:
            await conn.execute(
                "ALTER TABLE youzan_products ADD COLUMN last_sync_ref TEXT DEFAULT ''"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 youzan_products 表新增 last_sync_ref 列"
            )
        if "sold_num" not in yp_columns:
            await conn.execute(
                "ALTER TABLE youzan_products ADD COLUMN sold_num INTEGER DEFAULT 0"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 youzan_products 表新增 sold_num 列"
            )
        if "item_no" not in yp_columns:
            await conn.execute(
                "ALTER TABLE youzan_products ADD COLUMN item_no TEXT DEFAULT ''"
            )
            await conn.commit()
            logger.info(
                "已完成 SQLite 微创迁移：成功为 youzan_products 表新增 item_no 列"
            )
    except Exception as exc:
        logger.warning("动态校准 youzan_products 表字段发生异常：%s", exc)

    # 动态微创迁移：为现存 youzan_orders 表补充扩展字段
    _YO_EXTRA_COLUMNS: list[tuple[str, str]] = [
        ("pay_time", "ALTER TABLE youzan_orders ADD COLUMN pay_time TEXT DEFAULT ''"),
        (
            "consign_time",
            "ALTER TABLE youzan_orders ADD COLUMN consign_time TEXT DEFAULT ''",
        ),
        (
            "pay_type_str",
            "ALTER TABLE youzan_orders ADD COLUMN pay_type_str TEXT DEFAULT ''",
        ),
        (
            "express_type",
            "ALTER TABLE youzan_orders ADD COLUMN express_type INTEGER DEFAULT 0",
        ),
        (
            "refund_state",
            "ALTER TABLE youzan_orders ADD COLUMN refund_state INTEGER DEFAULT 0",
        ),
        (
            "post_fee_fen",
            "ALTER TABLE youzan_orders ADD COLUMN post_fee_fen INTEGER DEFAULT 0",
        ),
        (
            "discount_fen",
            "ALTER TABLE youzan_orders ADD COLUMN discount_fen INTEGER DEFAULT 0",
        ),
        (
            "delivery_province",
            "ALTER TABLE youzan_orders ADD COLUMN delivery_province TEXT DEFAULT ''",
        ),
        (
            "delivery_city",
            "ALTER TABLE youzan_orders ADD COLUMN delivery_city TEXT DEFAULT ''",
        ),
        (
            "delivery_district",
            "ALTER TABLE youzan_orders ADD COLUMN delivery_district TEXT DEFAULT ''",
        ),
        (
            "delivery_time",
            "ALTER TABLE youzan_orders ADD COLUMN delivery_time TEXT DEFAULT ''",
        ),
        (
            "outer_user_id",
            "ALTER TABLE youzan_orders ADD COLUMN outer_user_id TEXT DEFAULT ''",
        ),
        (
            "order_items_json",
            "ALTER TABLE youzan_orders ADD COLUMN order_items_json TEXT DEFAULT '[]'",
        ),
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

    # 执行版本化增量迁移
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
