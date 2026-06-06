#!/bin/bash
set -euo pipefail

# ============================================================
# 服务器端部署脚本（由 deploy.sh 通过 SSH 远程调用）
# 职责：合入代码 → 停服务 → 替换数据 → 启服务 → 验证
# ============================================================

PROJECT_DIR="/opt/yunxibakebot"
SERVICE_NAME="yunxibakebot"
HEALTH_URL="http://127.0.0.1:7001/health"
MAX_WAIT=60

log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $1" >&2
}

# ---- Step 1: 合入 Git bundle ----
log_info "正在合入代码..."
cd "$PROJECT_DIR"

if [ ! -f "server.bundle" ]; then
    log_error "server.bundle 不存在！请确认本地已传输成功"
    exit 1
fi

git fetch server.bundle HEAD:refs/remotes/bundle/master 2>/dev/null || {
    log_error "git fetch 失败，bundle 可能损坏"
    rm -f server.bundle
    exit 1
}

git reset --hard bundle/master
rm -f server.bundle
log_info "✓ 代码合入成功 (commit: $(git rev-parse --short HEAD))"

# ---- Step 2: 安装/更新依赖 ----
log_info "检查 Python 依赖..."
if git diff --name-only HEAD~1 HEAD 2>/dev/null | grep -q "requirements.txt"; then
    log_info "检测到 requirements.txt 变化，执行 pip install..."
    # 使用 --quiet 减少输出，只显示错误
    pip install --quiet -r requirements.txt 2>&1 | grep -v "^Requirement already satisfied" || true
    log_info "✓ 依赖更新完成"
else
    log_info "依赖无变化，跳过安装"
fi

# ---- Step 3: 停止服务 ----
log_info "停止服务 ${SERVICE_NAME}..."
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    systemctl stop "$SERVICE_NAME"
    sleep 2
    log_info "✓ 服务已停止"
else
    log_info "⚠ 服务未运行，跳过停止"
fi

# ---- Step 4: 数据库原子替换 ----
log_info "检查数据库临时文件..."

for db_file in bot.db embeddings.pkl; do
    tmp_file="data/${db_file}.tmp"
    if [ -f "$tmp_file" ]; then
        mv -f "$tmp_file" "data/${db_file}"
        log_info "✓ ${db_file} 原子替换完成"
    fi
done

# ---- Step 5: 启动服务 ----
log_info "启动服务 ${SERVICE_NAME}..."
systemctl start "$SERVICE_NAME"
log_info "✓ 服务已启动"

# ---- Step 6: 健康检查（等待就绪）----
log_info "等待服务就绪 (最多 ${MAX_WAIT}s)..."
elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null || echo "000")
    if [ "$status" = "200" ]; then
        log_info "✓ 服务健康检查通过 (HTTP 200, 耗时 ${elapsed}s)"
        break
    fi
    sleep 3
    elapsed=$((elapsed + 3))
done

if [ $elapsed -ge $MAX_WAIT ]; then
    log_error "❌ 服务在 ${MAX_WAIT}s 内未就绪！请手动排查:"
    log_error "  journalctl -u ${SERVICE_NAME} -n 50 --no-pager"
    log_error "  回滚命令: cd ${PROJECT_DIR} && git reset --hard HEAD~1 && systemctl restart ${SERVICE_NAME}"
    exit 1
fi

# ---- 完成 ----
echo ""
echo "============================================"
echo "  部署完成！版本: $(cat VERSION 2>/dev/null || echo 'unknown')"
echo "  Commit:   $(git rev-parse --short HEAD)"
echo "  时间:     $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
