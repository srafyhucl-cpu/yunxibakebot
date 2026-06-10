"""
数据库表结构定义。

所有 CREATE TABLE / CREATE INDEX 语句集中管理于此。
连接管理与迁移执行器在 app/database.py 中。
"""

SCHEMA_STATEMENTS: list[str] = [
    # 会话表
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
    # 消息表
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
    # 知识库表
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
    # 人工转接表
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
    # 订单表
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
    # 店铺配置表
    """CREATE TABLE IF NOT EXISTS shop_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT DEFAULT (datetime('now'))
    )""",
    # 有赞商品与实时库存大宽表
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
        item_no TEXT DEFAULT '',
        last_sync_source TEXT DEFAULT 'product_reconcile',
        last_sync_ref TEXT DEFAULT '',
        updated_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_yp_title ON youzan_products(title)",
    "CREATE INDEX IF NOT EXISTS idx_yp_alias ON youzan_products(alias)",
    # 有赞交易订单大宽表
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
    # analytics_events（分析埋点日志物理大宽表）
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
    # 有赞 Webhook 审计表
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
    # 顾客长期记忆画像
    """CREATE TABLE IF NOT EXISTS customer_profiles (
        id TEXT PRIMARY KEY,
        channel TEXT NOT NULL,
        user_id TEXT NOT NULL,
        display_name TEXT DEFAULT '',
        preferences_json TEXT DEFAULT '{}',
        order_summary_json TEXT DEFAULT '{}',
        allergens_json TEXT DEFAULT '[]',
        consent_status TEXT DEFAULT 'unknown'
            CHECK(consent_status IN ('unknown','granted','revoked')),
        source_evidence_json TEXT DEFAULT '{}',
        last_interaction_at TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        UNIQUE(channel, user_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_cp_channel_user ON customer_profiles(channel, user_id)",
    # 离线会话质检结果
    """CREATE TABLE IF NOT EXISTS conversation_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL REFERENCES sessions(id),
        quality_score INTEGER NOT NULL CHECK(quality_score >= 0 AND quality_score <= 100),
        issues_json TEXT DEFAULT '[]',
        reviewer_model TEXT DEFAULT '',
        reviewed_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_cr_session ON conversation_reviews(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_cr_score ON conversation_reviews(quality_score)",
    # 知识缺口建议，人工审核后才可进入知识库
    """CREATE TABLE IF NOT EXISTS knowledge_gaps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_norm TEXT NOT NULL,
        frequency INTEGER DEFAULT 1,
        status TEXT DEFAULT 'open'
            CHECK(status IN ('open','proposed','resolved','rejected')),
        proposed_answer TEXT DEFAULT '',
        related_sessions_json TEXT DEFAULT '[]',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_kg_status ON knowledge_gaps(status)",
    "CREATE INDEX IF NOT EXISTS idx_kg_freq ON knowledge_gaps(frequency)",
    # 微信客服同步状态：保存 sync_msg cursor，抵御历史回放
    """CREATE TABLE IF NOT EXISTS wecom_kf_sync_states (
        open_kfid TEXT PRIMARY KEY,
        last_cursor TEXT DEFAULT '',
        status TEXT DEFAULT 'idle'
            CHECK(status IN ('idle','syncing','failed')),
        last_error TEXT DEFAULT '',
        retry_count INTEGER DEFAULT 0,
        last_synced_at TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""",
    # 微信客服消息账本：按 msgid 做持久化幂等
    """CREATE TABLE IF NOT EXISTS wecom_kf_message_ledger (
        msg_id TEXT PRIMARY KEY,
        open_kfid TEXT DEFAULT '',
        external_userid TEXT DEFAULT '',
        origin INTEGER DEFAULT 0,
        msgtype TEXT DEFAULT '',
        event_type TEXT DEFAULT '',
        process_action TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_wkms_open_kfid ON wecom_kf_message_ledger(open_kfid)",
    "CREATE INDEX IF NOT EXISTS idx_wkms_external_user ON wecom_kf_message_ledger(external_userid)",
]

PRAGMA_STATEMENTS: list[str] = [
    "PRAGMA journal_mode = WAL",
    "PRAGMA busy_timeout = 5000",
    "PRAGMA foreign_keys = ON",
    "PRAGMA auto_vacuum = INCREMENTAL",
]
