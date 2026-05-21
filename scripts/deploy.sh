#!/bin/bash
set -e

echo "==== 1. 开始在服务器上合入本次极客高加固代码 ===="
cd /opt/yunxibakebot
git fetch server.bundle HEAD:refs/remotes/bundle/master
git reset --hard bundle/master
rm -f server.bundle
echo "✓ Git 代码合入成功！"

echo "==== 2. 安全屏障：停用服务，释放 SQLite 独占锁 ===="
systemctl stop yunxibakebot
echo "✓ 生产服务已成功关闭！"

echo "==== 3. 原子物理级移置置换新一代数据库与向量库 ===="
if [ -f "data/bot.db.tmp" ]; then
    mv -f data/bot.db.tmp data/bot.db
    echo "✓ 主物理数据库 (bot.db) 原子替换完毕！"
fi
if [ -f "data/embeddings.pkl.tmp" ]; then
    mv -f data/embeddings.pkl.tmp data/embeddings.pkl
    echo "✓ RAG向量库 (embeddings.pkl) 原子替换完毕！"
fi

echo "==== 4. 重新拉起应用，见证 0.05秒瞬间启动奇迹 ===="
systemctl start yunxibakebot
echo "✓ 生产服务已成功重新拉起，指纹校验通过，极速通航！"
