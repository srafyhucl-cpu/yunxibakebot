#!/bin/bash
set -e
# ============================================================
# 企微回调接入 — 服务器一键配置脚本
# 在服务器上执行：bash setup_wecom.sh
# ============================================================

DOMAIN="yunxifood.cn"
APP_PORT=7001
NGINX_CONF="/etc/nginx/sites-available/${DOMAIN}.conf"
NGINX_ENABLED="/etc/nginx/sites-enabled/${DOMAIN}.conf"
PROJECT_DIR="/opt/yunxibakebot"

echo "==== 1. 更新 .env 企微配置 ===="
cd "$PROJECT_DIR"

# 写入 TOKEN 和 AESKey（如果尚未配置）
if grep -q '^WECOM_TOKEN=$' .env 2>/dev/null; then
    sed -i "s/^WECOM_TOKEN=.*/WECOM_TOKEN=AIdH2j4QttfIvJcCrdDG/" .env
    echo "✓ WECOM_TOKEN 已写入 .env"
else
    echo "⚠ WECOM_TOKEN 已存在，跳过"
fi

if grep -q '^WECOM_ENCODING_AES_KEY=$' .env 2>/dev/null; then
    sed -i "s|^WECOM_ENCODING_AES_KEY=.*|WECOM_ENCODING_AES_KEY=MHyGeFISanfhz5sWiLDcHblE+ldp8aANnK9czp6KNGA=|" .env
    echo "✓ WECOM_ENCODING_AES_KEY 已写入 .env"
else
    echo "⚠ WECOM_ENCODING_AES_KEY 已存在，跳过"
fi

echo ""
echo "==== 2. 配置 Nginx（${DOMAIN}） ===="

cat > "$NGINX_CONF" << 'NGINX_EOF'
# yunxifood.cn — 芸熙烘焙主站（企微回调 + API + 静态页面）
server {
    listen 80;
    server_name yunxifood.cn;

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:7001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 企微回调
    location /api/v1/wecom/ {
        proxy_pass http://127.0.0.1:7001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 其余流量
    location / {
        proxy_pass http://127.0.0.1:7001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX_EOF

echo "✓ Nginx 配置已写入 $NGINX_CONF"

# 启用站点
if [ ! -L "$NGINX_ENABLED" ]; then
    ln -sf "$NGINX_CONF" "$NGINX_ENABLED"
    echo "✓ 已启用站点"
else
    echo "⚠ 站点已启用，跳过"
fi

echo ""
echo "==== 3. 申请 SSL 证书 ===="

# 先 reload HTTP 配置，确保 Let's Encrypt 能通过 HTTP 验证
nginx -t && systemctl reload nginx

# 申请证书
if [ ! -d "/etc/letsencrypt/live/${DOMAIN}" ]; then
    certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos --email admin@hclstudio.cn
    echo "✓ SSL 证书已签发"
else
    echo "⚠ SSL 证书已存在，跳过签发"
fi

# 确保证书自动续期
systemctl enable certbot.timer 2>/dev/null || true

echo ""
echo "==== 4. 重启服务 ===="
systemctl restart yunxibakebot
echo "✓ 服务已重启"

# 验证
sleep 3
echo ""
echo "==== 5. 验证回调 URL ===="
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "https://${DOMAIN}/health" 2>/dev/null || echo "000")
echo "健康检查 HTTP 状态码: ${HEALTH}"

echo ""
echo "============================================"
echo "  企微回调接入配置完成！"
echo ""
echo "  回调 URL:  https://${DOMAIN}/api/v1/wecom/callback"
echo "  Token:     AIdH2j4QttfIvJcCrdDG"
echo "  AESKey:    MHyGeFISanfhz5sWiLDcHblE+ldp8aANnK9czp6KNGA="
echo ""
echo "  下一步：登录企业微信管理后台 → 应用管理"
echo "  → 选择应用 → 接收消息 → 设置API接收"
echo "  → 填入上述 URL、Token、AESKey"
echo "  → 点击保存，企微会自动验证回调 URL"
echo "============================================"
