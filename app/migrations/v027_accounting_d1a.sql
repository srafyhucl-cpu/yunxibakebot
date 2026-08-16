-- D1-A 最小资金核心纵向切片（2026-08-16）：mock/余额订单 预占→结算→取消释放→重放
-- 1) payment_attempt：支付尝试（结算命令事实源 + 幂等源），subject-slot 部分唯一索引
--    保证单主体单活跃尝试（双连接恰一次结算）；快照绑定不可变 member_balance_id
-- 2) payment_attempt_leg：尝试腿（balance / points / coupon 预占额明细）
-- 3) account_hold：资金 / 积分预占（不可变账户绑定），取消 / 超时释放
-- 4) accounting_outbox：账务出站事件（order.settled / order.released，D1-C provider 对接预留）
-- 5) refund_shortfall_debt 扩展：remaining（剩余未偿额）+ version（部分偿还 / 结案 CAS）
-- 范围边界：真实微信 prepay / notify、真实券投影、正式导入保持 No-Go（设计文档见
-- docs/specs/2026-08-16-accounting-d1a-minimal-slice.md）

CREATE TABLE IF NOT EXISTS payment_attempt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_type TEXT NOT NULL DEFAULT 'order',
    subject_id TEXT NOT NULL DEFAULT '',
    provider TEXT NOT NULL DEFAULT 'mock',
    merchant_order_no TEXT NOT NULL DEFAULT '',
    payment_snapshot_json TEXT NOT NULL DEFAULT '{}',
    snapshot_hash TEXT NOT NULL DEFAULT '',
    member_balance_id INTEGER,
    status TEXT NOT NULL DEFAULT 'prepay_ready'
        CHECK(status IN ('draft', 'prepay_requested', 'prepay_unknown', 'prepay_ready',
                         'settling', 'settling_retry', 'succeeded', 'failed',
                         'cancelled', 'expired', 'manual_review')),
    active_command_type TEXT NOT NULL DEFAULT '',
    lease_token TEXT NOT NULL DEFAULT '',
    lease_until TEXT,
    state_version INTEGER NOT NULL DEFAULT 1,
    prepay_started_at TEXT,
    settled_at TEXT,
    last_error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- subject-slot 部分唯一索引：单主体最多一条活跃尝试（预占/结算中/重试/人工复核）
CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_attempt_active_slot
    ON payment_attempt(subject_type, subject_id)
    WHERE status IN ('draft', 'prepay_requested', 'prepay_unknown', 'prepay_ready',
                     'settling', 'settling_retry', 'manual_review');
CREATE INDEX IF NOT EXISTS idx_payment_attempt_subject
    ON payment_attempt(subject_type, subject_id);
CREATE INDEX IF NOT EXISTS idx_payment_attempt_member
    ON payment_attempt(member_balance_id);

CREATE TABLE IF NOT EXISTS payment_attempt_leg (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_attempt_id INTEGER NOT NULL,
    asset_type TEXT NOT NULL DEFAULT '',
    amount_fen INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'reserved'
        CHECK(status IN ('reserved', 'consumed', 'released')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_attempt_leg_unique
    ON payment_attempt_leg(payment_attempt_id, asset_type);

CREATE TABLE IF NOT EXISTS account_hold (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hold_key TEXT NOT NULL,
    subject_type TEXT NOT NULL DEFAULT 'order',
    subject_id TEXT NOT NULL DEFAULT '',
    payment_attempt_id INTEGER NOT NULL,
    asset_type TEXT NOT NULL DEFAULT '',
    amount_fen INTEGER NOT NULL DEFAULT 0,
    member_balance_id INTEGER,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK(status IN ('active', 'consumed', 'released', 'expired')),
    expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_account_hold_key ON account_hold(hold_key);
CREATE INDEX IF NOT EXISTS idx_account_hold_attempt ON account_hold(payment_attempt_id);
CREATE INDEX IF NOT EXISTS idx_account_hold_member ON account_hold(member_balance_id);

CREATE TABLE IF NOT EXISTS accounting_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_key TEXT NOT NULL,
    operation_type TEXT NOT NULL DEFAULT '',
    subject_type TEXT NOT NULL DEFAULT 'order',
    subject_id TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending', 'processing', 'succeeded', 'failed', 'dead_letter')),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    lease_token TEXT NOT NULL DEFAULT '',
    lease_until TEXT,
    depends_on_operation_key TEXT NOT NULL DEFAULT '',
    last_error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_accounting_outbox_key ON accounting_outbox(operation_key);
CREATE INDEX IF NOT EXISTS idx_accounting_outbox_status ON accounting_outbox(status);

-- 债务闭环扩展（评审问题 3 / D1-A）：剩余未偿额 + 版本 CAS（部分偿还、结案、幂等）
ALTER TABLE refund_shortfall_debt ADD COLUMN remaining INTEGER NOT NULL DEFAULT 0;
ALTER TABLE refund_shortfall_debt ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
UPDATE refund_shortfall_debt SET remaining = amount WHERE remaining = 0;
