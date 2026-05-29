"""
有赞历史脏数据一键修复与商品编码全量补齐脚本。

职责：
1. 找出本地 youzan_products 中已下架（is_active=0）但 knowledge_base 中依然活跃（is_active=1）的商品知识，联动将其软下架，消除重复行脏数据。
2. 找出本地 item_no 为空的商品，并发拉取有赞真实商品详情，全量回写补齐 item_no 与最新销量。
"""

import asyncio
import os
import sys

# 强行设置标准输出编码为 UTF-8，防止商品标题中的 Emoji 导致 Windows GBK 终端报错
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# 将项目根目录加入 Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import init_db
from app.config import settings
from app.service.youzan.client import YouzanClient
from app.repository.config_repo import ConfigRepo


async def main() -> None:
    print("=== 启动有赞脏数据校准与商品编码全量自愈通道 ===")

    # 强制激活真实有赞平台连通
    settings.YOUZAN_MOCK_MODE = False
    db_path = "data/bot.db"
    db = await init_db(db_path)

    try:
        # 1. 修复脏数据：youzan_products 中已下架，但 knowledge_base 依然活跃的商品知识
        print("[1] 正在检查并修复 knowledge_base 中的脏数据状态...")
        cursor = await db.execute(
            "UPDATE knowledge_base SET is_active = 0, "
            "vector_sync_status = 'success', "
            "vector_synced_at = datetime('now'), "
            "updated_at = datetime('now') "
            "WHERE youzan_item_id IN ("
            "  SELECT CAST(item_id AS TEXT) FROM youzan_products WHERE is_active = 0"
            ") AND is_active = 1 AND category = 'product'"
        )
        await db.commit()
        print(f"  - 成功联动下架 {cursor.rowcount} 个残留脏数据商品知识")

        # 2. 补齐商品编码 item_no
        print("[2] 正在获取数据库中商品编码为空的商品记录...")
        rows = await db.execute_fetchall(
            "SELECT item_id, title FROM youzan_products WHERE item_no = '' OR item_no IS NULL"
        )
        print(f"  - 共找到 {len(rows)} 个商品编码为空的本地商品记录")

        if not rows:
            print("🎉 没有需要补齐商品编码的商品！")
            return

        config_repo = ConfigRepo(db)
        yz_client = YouzanClient(config_repo=config_repo)

        sem = asyncio.Semaphore(10)
        updated_count = 0
        failed_count = 0

        async def _fetch_and_update(iid: int, title: str) -> None:
            nonlocal updated_count, failed_count
            async with sem:
                try:
                    raw = await yz_client.get_product(iid)
                    item = (raw.get("data") or raw.get("response") or {}).get("item") or {}
                    item_no = item.get("item_no", "") or ""
                    sold_num = int(item.get("sold_num", 0) or 0)

                    # 强制写入数据库
                    await db.execute(
                        "UPDATE youzan_products SET item_no = ?, sold_num = ? WHERE item_id = ?",
                        (item_no, sold_num, iid)
                    )
                    await db.commit()
                    print(f"    [OK] 补齐 [{title}] (ID: {iid}) -> 编码: {item_no}, 销量: {sold_num}")
                    updated_count += 1
                except Exception as exc:
                    print(f"    [ERROR] 补齐 [{title}] (ID: {iid}) 失败: {exc}")
                    failed_count += 1

        tasks = [_fetch_and_update(row["item_id"], row["title"]) for row in rows]
        await asyncio.gather(*tasks)
        await yz_client.close()

        print(f"\n自愈执行完毕！成功补齐: {updated_count}，失败: {failed_count}")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
