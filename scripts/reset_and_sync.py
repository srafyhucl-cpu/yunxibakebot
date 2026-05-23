"""
高性能全量同步脚本：精细化重置 + 并发拉取 + 批量写库 + 一次性向量构建。

执行流程：
  Phase 0: 精细化重置（保护非商品知识 store_info/policy/faq/after_sales）
  Phase 1: 分页拉取有赞全量在售商品列表
  Phase 2: Semaphore(5) 并发获取商品详情
  Phase 3: 单事务批量写入 youzan_products + knowledge_base
  Phase 4: 全量重构向量索引（含非商品知识）

使用方式：
  cd /opt/yunxibakebot
  /opt/yunxibakebot/venv/bin/python3 scripts/reset_and_sync.py
"""

import asyncio
import datetime
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.database import init_db
from app.repository.config_repo import ConfigRepo
from app.repository.knowledge_repo import KnowledgeRepo
from app.service.embedding_search import EmbeddingSearcher
from app.service.youzan.client import YouzanClient
from app.service.youzan.event_item import _build_rag_content, _extract_item_tags

# ── 并发控制常量 ────────────────────────────────────────────────────────────
CONCURRENCY_LIMIT = 5
PAGE_SIZE = 100
API_INTERVAL = 0.05  # 并发请求间礼貌延迟（秒）


async def phase0_reset(db) -> None:
    """Phase 0: 精细化重置 — 清空业务表但保护非商品知识和运行配置。"""
    print("\n" + "=" * 60)
    print("Phase 0: 精细化数据重置")
    print("=" * 60)

    # 全表清空的业务表
    full_delete_tables = [
        "youzan_products",
        "youzan_orders",
        "sessions",
        "messages",
        "human_transfers",
        "orders",
        "analytics_events",
    ]
    for table in full_delete_tables:
        await db.execute(f"DELETE FROM {table}")
        print(f"  ✓ 已清空 {table}")

    # knowledge_base 精细化清除：仅删除商品类条目
    result = await db.execute(
        "DELETE FROM knowledge_base WHERE category = 'product' OR youzan_item_id IS NOT NULL"
    )
    deleted_count = result.rowcount
    await db.commit()
    print(f"  ✓ 已清除 knowledge_base 商品类条目: {deleted_count} 条")
    print("  ℹ 保留非商品知识（store_info/policy/faq/after_sales）+ shop_config")

    # 删除向量缓存文件
    embedding_dir = Path(settings.EMBEDDING_PATH).parent
    for suffix in (".npy", ".json"):
        vec_file = Path(settings.EMBEDDING_PATH).with_suffix(suffix)
        if vec_file.exists():
            vec_file.unlink()
            print(f"  ✓ 已删除向量缓存: {vec_file.name}")

    print("  🧹 Phase 0 完成")


async def phase1_fetch_list(yz_client: YouzanClient) -> list[dict]:
    """Phase 1: 分页拉取有赞全量在售商品列表。"""
    print("\n" + "=" * 60)
    print("Phase 1: 分页拉取商品列表")
    print("=" * 60)

    items: list[dict] = []
    page_no = 1

    while True:
        print(f"  - 正在请求第 {page_no} 页 (page_size={PAGE_SIZE})...")
        resp = await yz_client._call(
            "youzan.items.onsale.get", "3.0.0",
            {"kdt_id": settings.YOUZAN_KDT_ID, "page_no": page_no, "page_size": PAGE_SIZE}
        )

        outer_data = resp.get("data") or resp.get("response") if isinstance(resp, dict) else None
        if not isinstance(outer_data, dict) or "items" not in outer_data:
            print(f"  ❌ 第 {page_no} 页数据异常，已中止。响应键: {list(resp.keys()) if isinstance(resp, dict) else type(resp)}")
            break

        page_items = outer_data.get("items") or []
        if not page_items:
            break

        items.extend(page_items)
        print(f"    ✓ 获取 {len(page_items)} 条")

        if len(page_items) < PAGE_SIZE:
            break

        page_no += 1
        await asyncio.sleep(API_INTERVAL)

    print(f"  📦 Phase 1 完成: 共 {len(items)} 条在售商品")
    return items


async def phase2_fetch_details(yz_client: YouzanClient, items: list[dict]) -> list[dict]:
    """Phase 2: Semaphore 并发获取商品详情。"""
    print("\n" + "=" * 60)
    print(f"Phase 2: 并发获取商品详情 (并发度={CONCURRENCY_LIMIT})")
    print("=" * 60)

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    results: list[dict | None] = [None] * len(items)

    async def fetch_one(idx: int, item_id: int) -> None:
        async with semaphore:
            try:
                raw = await yz_client.get_product(item_id)
                if isinstance(raw, dict) and raw.get("gw_err_resp"):
                    print(f"    ⚠ 商品 {item_id} API 拒绝: {raw['gw_err_resp']}")
                    return
                outer = raw.get("data") or raw.get("response") if isinstance(raw, dict) else None
                if isinstance(outer, dict) and "item" in outer:
                    results[idx] = outer["item"]
                else:
                    print(f"    ⚠ 商品 {item_id} 响应结构异常")
            except Exception as exc:
                print(f"    ⚠ 商品 {item_id} 请求失败: {exc}")
            await asyncio.sleep(API_INTERVAL)

    tasks = [
        fetch_one(i, item.get("item_id"))
        for i, item in enumerate(items)
    ]
    await asyncio.gather(*tasks)

    valid = [r for r in results if r is not None]
    print(f"  ⚡ Phase 2 完成: 成功获取 {len(valid)}/{len(items)} 条详情")
    return valid


async def phase3_batch_write(db, details: list[dict]) -> int:
    """Phase 3: 单事务批量写入 youzan_products + knowledge_base。"""
    print("\n" + "=" * 60)
    print("Phase 3: 批量写库（单事务）")
    print("=" * 60)

    products_rows: list[tuple] = []
    kb_rows: list[tuple] = []
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item_data in details:
        item_id = item_data.get("item_id", 0)
        if not item_id:
            continue

        title = item_data.get("title", "")
        alias = item_data.get("alias", "") or str(item_id)
        price_fen = item_data.get("price", 0)
        stock = item_data.get("quantity", 0)
        image = item_data.get("pic_url") or item_data.get("image") or ""
        is_active = 1  # 从 onsale 接口拉取的都是在售
        skus = item_data.get("skus", [])
        item_props = item_data.get("item_props", [])

        raw_desc = item_data.get("desc", "") or item_data.get("summary", "") or ""
        desc_clean = re.sub(r"\s+", " ", re.sub(r"\n+", "\n", re.sub(r"<.*?>", "", raw_desc))).strip()

        spec_names, prop_names, found_ingredients = _extract_item_tags(title, skus, item_props, desc_clean)
        status_lbl = "在售"
        tags_str = ", ".join([status_lbl] + list(set(spec_names)) + list(set(prop_names)) + list(set(found_ingredients)))

        skus_json = json.dumps(skus, ensure_ascii=False)
        item_props_json = json.dumps(item_props, ensure_ascii=False)

        products_rows.append((
            item_id, title, alias, price_fen, stock, image,
            is_active, skus_json, item_props_json, desc_clean, tags_str, now_str,
        ))

        # 构建 RAG 知识内容
        content_md = _build_rag_content(
            title, alias, status_lbl, skus, item_props,
            price_fen, stock, desc_clean, tags_str,
            item_id=item_id, image=image,
        )
        keywords = f"商品, 价格, 推荐, 蛋糕, {title}, {tags_str}"
        kb_rows.append((title, content_md, keywords, 50, str(item_id), now_str))

    if products_rows:
        await db.executemany(
            "INSERT INTO youzan_products "
            "(item_id, title, alias, price_fen, stock, image, is_active, skus_json, item_props_json, desc, tags, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(item_id) DO UPDATE SET "
            "title=excluded.title, alias=excluded.alias, price_fen=excluded.price_fen, "
            "stock=excluded.stock, image=excluded.image, is_active=excluded.is_active, "
            "skus_json=excluded.skus_json, item_props_json=excluded.item_props_json, "
            "desc=excluded.desc, tags=excluded.tags, updated_at=excluded.updated_at",
            products_rows,
        )

    if kb_rows:
        await db.executemany(
            "INSERT INTO knowledge_base "
            "(category, title, content, keywords, priority, youzan_item_id, is_active, updated_at) "
            'VALUES ("product", ?, ?, ?, ?, ?, 1, ?) '
            "ON CONFLICT(youzan_item_id) DO UPDATE SET "
            "title=excluded.title, content=excluded.content, keywords=excluded.keywords, "
            "priority=excluded.priority, is_active=1, updated_at=excluded.updated_at",
            kb_rows,
        )

    await db.commit()
    print(f"  💾 Phase 3 完成: {len(products_rows)} 条商品 + {len(kb_rows)} 条知识 (1 次 commit)")
    return len(products_rows)


async def phase4_build_vectors(db) -> None:
    """Phase 4: 全量重构向量索引（含非商品知识条目）。"""
    print("\n" + "=" * 60)
    print("Phase 4: 全量向量索引构建")
    print("=" * 60)

    knowledge_repo = KnowledgeRepo(db)
    all_docs = await knowledge_repo.get_all_titles_with_keys()

    if not all_docs:
        print("  ⚠ 知识库无活跃条目，跳过向量构建")
        return

    # 计算 MD5 指纹
    sorted_docs = sorted(all_docs, key=lambda x: x[0])
    concat_text = "".join(f"{d[1]}{d[2]}" for d in sorted_docs)
    current_db_md5 = hashlib.md5(concat_text.encode("utf-8")).hexdigest()

    print(f"  - 待编码文档: {len(all_docs)} 条（含非商品知识）")
    print(f"  - 数据指纹 MD5: {current_db_md5[:16]}...")

    t0 = time.perf_counter()
    vs = EmbeddingSearcher()
    await asyncio.to_thread(vs.build, all_docs, current_db_md5)
    encode_ms = (time.perf_counter() - t0) * 1000

    await vs.save(settings.EMBEDDING_PATH)
    print(f"  🤖 Phase 4 完成: {vs.doc_count} 条向量已构建并落盘 ({encode_ms:.0f}ms)")


async def main() -> None:
    """高性能全量同步主入口。"""
    print("🚀 芸熙烘焙 · 有赞全量同步管道启动")
    print(f"   数据库: {settings.DB_PATH}")
    print(f"   向量路径: {settings.EMBEDDING_PATH}")
    print(f"   KDT_ID: {settings.YOUZAN_KDT_ID}")

    # 强制关闭 Mock 模式
    settings.YOUZAN_MOCK_MODE = False

    db = await init_db(settings.DB_PATH)
    config_repo = ConfigRepo(db)
    yz_client = YouzanClient(config_repo=config_repo)

    t_start = time.perf_counter()

    try:
        # Phase 0: 精细化重置
        await phase0_reset(db)

        # Phase 1: 拉取商品列表
        items = await phase1_fetch_list(yz_client)
        if not items:
            print("\n⚠ 线上无在售商品，同步结束。")
            return

        # Phase 2: 并发获取详情
        details = await phase2_fetch_details(yz_client, items)
        if not details:
            print("\n⚠ 无有效商品详情，同步结束。")
            return

        # Phase 3: 批量写库
        count = await phase3_batch_write(db, details)

        # Phase 4: 全量向量构建
        await phase4_build_vectors(db)

        elapsed = time.perf_counter() - t_start
        print("\n" + "=" * 60)
        print(f"🏆 全量同步完成！{count} 条商品 | 总耗时 {elapsed:.1f}s")
        print("=" * 60)

    finally:
        await yz_client.close()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
