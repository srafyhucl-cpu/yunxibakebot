#!/bin/bash
set -e

echo "==== 1. 开始在服务器上合入本次 UMP 高加固增量代码 ===="
cd /opt/yunxibakebot
git fetch server.bundle HEAD:refs/remotes/bundle/master
git reset --hard bundle/master
rm -f server.bundle
echo "✓ Git 增量代码合并成功！"

echo "==== 2. 重启 Systemd 芸熙烘焙 AI 客服进程 ===="
systemctl restart yunxibakebot
echo "✓ 生产服务重启成功，UMP 统一多媒体协议正式线上合龙！"
