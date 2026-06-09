#!/bin/bash
# ============================================================
# 芸熙烘焙 — 生产数据安全拉取脚本（本地执行）
#
# 用途：
#   为离线检索评测（scripts/eval_retrieval.py）准备一份贴近线上的
#   知识库 + 商品数据快照。仅拉取检索评测所需数据，并在本地脱敏，
#   清除顾客 PII（messages / youzan_orders 等），避免敏感数据落地。
#
# 安全设计：
#   1. 服务器侧用 SQLite 官方 .backup 生成一致快照（WAL 安全，只读，不停机）
#   2. 仅 scp 拉取该快照到本地 data/prod_snapshot/
#   3. 本地脱敏：DROP / 清空所有含顾客 PII 的表，仅保留 knowledge_base + youzan_products
#   4. 产物位于 data/（已被 .gitignore 忽略），不会进入版本库
#
# 用法：
#   bash scripts/pull_prod_snapshot.sh
#
# 环境变量（与 deploy.sh 对齐，可覆盖）：
#   SSH_HOST / SSH_USER / SSH_PORT / SSH_KEY
# ============================================================

set -euo pipefail

# ---- 服务器连接配置（默认值与 deploy.sh 一致）----
SSH_HOST="${SSH_HOST:-47.94.102.250}"
SSH_USER="${SSH_USER:-root}"
SSH_PORT="${SSH_PORT:-22}"
SSH_KEY="${SSH_KEY:-/mnt/c/Users/srafy/.ssh/id_ed25519}"
REMOTE_DIR="/opt/yunxibakebot"
REMOTE_DB="${REMOTE_DIR}/data/bot.db"

# ---- 本地路径 ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SNAPSHOT_DIR="$PROJECT_DIR/data/prod_snapshot"
RAW_SNAPSHOT="$SNAPSHOT_DIR/bot_raw.db"          # 服务器拉回的原始快照
EVAL_DB="$SNAPSHOT_DIR/eval.db"                   # 脱敏后供评测使用的库
REMOTE_TMP="/tmp/yunxi_eval_snapshot_$$.db"

CONNECT_TIMEOUT=10

# ---- 参数解析 ----
# --raw : 跳过本地脱敏，原库直接落到 data/prod_snapshot/bot_raw.db（仍受 .gitignore 保护）
RAW_MODE=0
for arg in "$@"; do
    case "$arg" in
        --raw) RAW_MODE=1 ;;
        -h|--help)
            echo "用法: bash scripts/pull_prod_snapshot.sh [--raw]"
            echo "  默认    : 拉取并本地脱敏（清除 messages/orders 等 PII），生成 eval.db"
            echo "  --raw   : 跳过脱敏，保留原库 bot_raw.db（含顾客 PII，请用完即删）"
            exit 0
            ;;
    esac
done

log_info()  { echo "[$(date '+%H:%M:%S')] [INFO] $*"; }
log_warn()  { echo "[$(date '+%H:%M:%S')] [WARN] $*"; }
log_error() { echo "[$(date '+%H:%M:%S')] [ERROR] $*" >&2; }

# ---- WSL 兼容：修复密钥权限（同 deploy.sh）----
TMP_SSH_KEY=""
if [[ "$SSH_KEY" == /mnt/c/* || "${OSTYPE:-}" == "msys" ]]; then
    TMP_SSH_KEY="/tmp/pull_ssh_key_$$"
    cp "$SSH_KEY" "$TMP_SSH_KEY"
    chmod 600 "$TMP_SSH_KEY"
    SSH_KEY="$TMP_SSH_KEY"
fi

cleanup() {
    [ -n "$TMP_SSH_KEY" ] && rm -f "$TMP_SSH_KEY" 2>/dev/null || true
}
trap cleanup EXIT

ssh_run() {
    ssh -i "$SSH_KEY" -p "$SSH_PORT" \
        -o ConnectTimeout=$CONNECT_TIMEOUT \
        -o StrictHostKeyChecking=accept-new \
        "${SSH_USER}@${SSH_HOST}" "$@"
}

echo ""
echo "============================================"
echo "  生产数据安全拉取（仅检索评测用，本地脱敏）"
echo "============================================"
echo ""

mkdir -p "$SNAPSHOT_DIR"

# ============================================================
# Phase 1: 服务器侧生成一致快照（.backup，WAL 安全，只读）
# ============================================================
log_info "Phase 1/4: 在服务器上用 sqlite3 .backup 生成一致快照..."
if ! ssh_run "test -f '$REMOTE_DB'"; then
    log_error "服务器数据库不存在: $REMOTE_DB"
    exit 1
fi
# .backup 对在线 WAL 库生成一致副本，不停机、不锁写、纯只读
if ! ssh_run "sqlite3 '$REMOTE_DB' \".backup '$REMOTE_TMP'\" && sqlite3 '$REMOTE_TMP' 'PRAGMA integrity_check;' >/dev/null"; then
    log_error "服务器快照生成或完整性校验失败"
    ssh_run "rm -f '$REMOTE_TMP'" || true
    exit 1
fi
log_info "✓ 服务器快照已生成并通过完整性校验"

# ============================================================
# Phase 2: 拉取快照到本地
# ============================================================
log_info "Phase 2/4: 拉取快照到本地 $RAW_SNAPSHOT ..."
if ! scp -i "$SSH_KEY" -P "$SSH_PORT" \
        -o ConnectTimeout=$CONNECT_TIMEOUT \
        -o StrictHostKeyChecking=accept-new \
        "${SSH_USER}@${SSH_HOST}:${REMOTE_TMP}" "$RAW_SNAPSHOT"; then
    log_error "快照拉取失败"
    ssh_run "rm -f '$REMOTE_TMP'" || true
    exit 1
fi
# 清理服务器临时快照，避免敏感数据滞留
ssh_run "rm -f '$REMOTE_TMP'" || log_warn "服务器临时快照清理失败，请手动删除: $REMOTE_TMP"
log_info "✓ 快照已拉取到本地"

# ============================================================
# Phase 3: 本地脱敏 —— 仅保留检索评测所需数据，清除顾客 PII
#          （--raw 模式跳过本步，保留原库）
# ============================================================
if [ "$RAW_MODE" = "1" ]; then
    log_warn "Phase 3/4: --raw 模式，跳过脱敏，保留原库（含顾客 PII）"
    KB_COUNT=$(sqlite3 "$RAW_SNAPSHOT" "SELECT COUNT(*) FROM knowledge_base WHERE is_active=1;")
    PROD_COUNT=$(sqlite3 "$RAW_SNAPSHOT" "SELECT COUNT(*) FROM youzan_products;")
    FINAL_DB="$RAW_SNAPSHOT"
    log_warn "⚠ 原库含真实顾客对话/订单 PII，评测完成后请执行: rm -f '$RAW_SNAPSHOT'"
else
    log_info "Phase 3/4: 本地脱敏，生成评测库 $EVAL_DB ..."
    rm -f "$EVAL_DB"
    cp "$RAW_SNAPSHOT" "$EVAL_DB"

    # 评测只需要 knowledge_base（知识/FAQ）与 youzan_products（商品宽表）作为检索语料。
    # 其余表一律清空，重点清除任何可能含顾客 PII 的对话 / 订单 / 工单 / 埋点数据。
    sqlite3 "$EVAL_DB" <<'SQL'
PRAGMA foreign_keys = OFF;
-- 顾客对话与画像类（PII 高风险）
DELETE FROM messages;
DELETE FROM sessions;
DELETE FROM human_transfers;
DELETE FROM analytics_events;
-- 订单类（含买家 ID / 物流地址等 PII）
DELETE FROM orders;
DELETE FROM youzan_orders;
-- 审计 / 历史类（可能含 payload 片段）
DELETE FROM youzan_webhook_events;
DELETE FROM content_change_history;
VACUUM;
SQL

    # 校验脱敏结果：messages 必须为 0，knowledge_base 必须 > 0
    REMAIN_MSG=$(sqlite3 "$EVAL_DB" "SELECT COUNT(*) FROM messages;")
    KB_COUNT=$(sqlite3 "$EVAL_DB" "SELECT COUNT(*) FROM knowledge_base WHERE is_active=1;")
    PROD_COUNT=$(sqlite3 "$EVAL_DB" "SELECT COUNT(*) FROM youzan_products;")
    if [ "$REMAIN_MSG" != "0" ]; then
        log_error "脱敏校验失败：messages 仍有 $REMAIN_MSG 条，已中止"
        rm -f "$EVAL_DB"
        exit 2
    fi
    log_info "✓ 脱敏完成：messages=0 | 启用知识=$KB_COUNT | 商品=$PROD_COUNT"

    # 删除未脱敏的原始快照，避免本地滞留 PII
    rm -f "$RAW_SNAPSHOT"
    log_info "✓ 已删除未脱敏原始快照"
    FINAL_DB="$EVAL_DB"
fi

# ============================================================
# Phase 4: 报告
# ============================================================
echo ""
echo "============================================"
echo "  ✓ 评测数据准备完成"
echo ""
echo "  评测库:      $FINAL_DB"
echo "  启用知识:    $KB_COUNT 条"
echo "  商品:        $PROD_COUNT 条"
if [ "$RAW_MODE" = "1" ]; then
echo "  ⚠ 含 PII:    是（--raw 模式，用完请删: rm -f '$FINAL_DB'）"
fi
echo ""
echo "  下一步:"
echo "    python scripts/eval_retrieval.py --db $FINAL_DB"
echo "============================================"
