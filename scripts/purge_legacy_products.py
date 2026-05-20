"""
本地陈旧商品知识一键无损擦除与 RAG 向量索引库重塑重组脚本。
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
    print("🧹 启动历史本地陈旧商品知识一键无损擦除程序...")
    db_path = "data/bot.db"
    db = await init_db(db_path)

    try:
        knowledge_repo = KnowledgeRepo(db)

        # 1. 统计擦除前数量
        async with db.execute("SELECT COUNT(*) FROM knowledge_base WHERE category = 'product'") as cursor:
            total_products_before = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM knowledge_base WHERE category = 'product' AND youzan_item_id IS NULL") as cursor:
            legacy_count = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM knowledge_base WHERE category = 'product' AND youzan_item_id IS NOT NULL") as cursor:
            youzan_count = (await cursor.fetchone())[0]

        print("📊 擦除前统计：")
        print(f"  - 数据库中商品分类总条数: {total_products_before} 条")
        print(f"  - 待擦除的历史静态本地商品数: {legacy_count} 条")
        print(f"  - 保留的有赞线上同步活跃商品数: {youzan_count} 条")

        if legacy_count == 0:
            print("✨ 检查完毕：数据库中已经没有任何陈旧本地商品，无需重复擦除！")
            return

        # 2. 物理执行擦除命令
        print("\n🗑️ 正在从知识库中物理删除非有赞线上数据...")
        await db.execute("DELETE FROM knowledge_base WHERE category = 'product' AND youzan_item_id IS NULL")
        await db.commit()
        print("  - [SQLite] 数据库陈旧记录删除完成！")

        # 3. 释放数据库碎片，物理收缩 SQLite 文件磁盘空间
        print("⚡ 正在执行 PRAGMA incremental_vacuum 物理收缩磁盘体积...")
        await db.execute("PRAGMA incremental_vacuum")
        await db.commit()

        # 4. 重新加载全部保留的活跃知识（FAQ、售后、政策、以及有赞新商品）并重建 BGE 向量库
        print("\n🤖 正在全量重新读取知识并重塑 BGE 向量库...")
        vs = EmbeddingSearcher()
        all_titles = await knowledge_repo.get_all_titles()
        print(f"  - 重新装载的活跃向量条目总数: {len(all_titles)} 条 (含FAQ/售后/有赞动态商品)")

        if all_titles:
            await asyncio.to_thread(vs.build, all_titles)
            await asyncio.to_thread(vs.save, settings.EMBEDDING_PATH)
            print("  - [NumPy] 内存向量搜索库与本地 `.index` 文件全量重构对齐成功！")
        else:
            print("  - 警告：无任何活跃知识，跳过向量重塑")

        # 5. 校验擦除后数量
        async with db.execute("SELECT COUNT(*) FROM knowledge_base WHERE category = 'product'") as cursor:
            total_products_after = (await cursor.fetchone())[0]
        print(f"\n✅ 擦除净化完成！当前数据库中 [product] 商品条目数: {total_products_after} 条 (100% 均为有赞商品)！")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
