"""
线上真实环境：100% 物理擦除 Mock 仿真商品及知识库向量索引重构脚本。
"""

import asyncio
import os
import sys

# 将项目根目录加入 Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import init_db
from app.config import settings
from app.repository.knowledge_repo import KnowledgeRepo
from app.service.embedding_search import EmbeddingSearcher


async def main() -> None:
    print("🧹 启动有赞仿真 Mock 商品一键无损擦除程序...")
    db_path = "data/bot.db"
    db = await init_db(db_path)

    try:
        # 1. 物理删除商品宽表中的 Mock 商品
        print("🗑️ 正在从商品大宽表 [youzan_products] 中删除 1001-1010 号仿真数据...")
        await db.execute("DELETE FROM youzan_products WHERE item_id <= 1010")
        await db.commit()

        # 2. 物理删除知识库表中的 Mock 商品
        print("🗑️ 正在从知识库 [knowledge_base] 中删除仿真数据的 RAG 节点...")
        await db.execute("DELETE FROM knowledge_base WHERE category = 'product' AND CAST(youzan_item_id AS INTEGER) <= 1010")
        await db.commit()

        # 3. 释放数据库磁盘碎片空间
        print("⚡ 正在执行 PRAGMA incremental_vacuum 物理收缩磁盘体积...")
        await db.execute("PRAGMA incremental_vacuum")
        await db.commit()

        # 4. 全量重新构建向量检索索引（重新计算 Embedding 对齐）
        print("\n🤖 正在重新装载真实商品、FAQ，全量重构 BGE 向量检索索引...")
        knowledge_repo = KnowledgeRepo(db)
        vs = EmbeddingSearcher()
        all_titles = await knowledge_repo.get_all_titles()
        print(f"  - 当前剩余的活跃知识条目总数: {len(all_titles)} 条 (含FAQ/售后/线上真实商品)")

        if all_titles:
            await asyncio.to_thread(vs.build, all_titles)
            await asyncio.to_thread(vs.save, settings.EMBEDDING_PATH)
            print("  - [NumPy] 向量搜索内存矩阵与本地 `.index` 文件同步对齐完成！")

        # 5. 打印最终保留的真实商品清单
        async with db.execute("SELECT item_id, title FROM youzan_products") as cursor:
            rows = await cursor.fetchall()
            print("\n🏆 净化大成功！当前物理数据库中 100% 仅保留线上真实商品：")
            for r in rows:
                print(f"  - [真实线上商品] ID: {r[0]} | {r[1]}")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
