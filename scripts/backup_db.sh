#!/bin/bash
# ============================================================
# 芸熙烘焙 SQLite 热备份脚本
#
# 功能：
#   使用 SQLite 官方 .backup 命令对 data/bot.db 进行热备份，
#   无需停机，备份期间数据库可正常读写。
#
# 用法：
#   bash scripts/backup_db.sh
#
# 建议 crontab（每小时执行）：
#   0 * * * * /opt/yunxibakebot/scripts/backup_db.sh >> /opt/yunxibakebot/data/backup.log 2>&1
# ============================================================

set -euo pipefail

# ── 路径配置 ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DB_PATH="$PROJECT_DIR/data/bot.db"
BACKUP_DIR="$PROJECT_DIR/data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/bot_backup_$TIMESTAMP.db"

# ── 日志函数 ──
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >&2
}

# ── 前置检查 ──
if [ ! -f "$DB_PATH" ]; then
    log_error "数据库文件不存在: $DB_PATH"
    exit 1
fi

# ── 创建备份目录 ──
if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
    log_info "创建备份目录: $BACKUP_DIR"
fi

# ── 执行热备份 ──
log_info "开始备份: $DB_PATH → $BACKUP_FILE"

# 使用 SQLite 的 .backup 命令进行热备份（安全、零停机）
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

# ── 验证备份 ──
if [ -f "$BACKUP_FILE" ]; then
    # 快速完整性检查
    sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" > /dev/null 2>&1
    INTEGRITY_STATUS=$?
    if [ $INTEGRITY_STATUS -eq 0 ]; then
        ORIG_SIZE=$(stat -c%s "$DB_PATH" 2>/dev/null || stat -f%z "$DB_PATH" 2>/dev/null)
        BACKUP_SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null)
        log_info "备份完成 | 文件: $(basename "$BACKUP_FILE") | 大小: $BACKUP_SIZE 字节 | 原库: $ORIG_SIZE 字节 | 完整性: OK"
    else
        log_error "备份完整性检查失败: $BACKUP_FILE"
        rm -f "$BACKUP_FILE"
        exit 2
    fi
else
    log_error "备份文件未生成: $BACKUP_FILE"
    exit 3
fi

# ── 旧备份保留 ──
# 备份属于受控恢复资产，不在应用脚本中批量删除；按隐私保留策略由运维逐个审核并清理。
log_info "备份保留策略: 30 天；过期文件由运维按单文件路径审核清理"
