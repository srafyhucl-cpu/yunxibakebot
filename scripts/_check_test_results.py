"""临时用：查询本地 DB 打印测试详细结果，用完可删。"""

import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
db = sqlite3.connect(str(ROOT_DIR / "data" / "bot.db"))
db.row_factory = sqlite3.Row

ITEM_ID = "3421897229"

print("=" * 60)
print("youzan_orders（最近 5 条）")
print("=" * 60)
rows = db.execute(
    "SELECT order_no, status, amount_fen, product_titles, buyer_id, updated_at"
    " FROM youzan_orders ORDER BY updated_at DESC LIMIT 5"
).fetchall()
if rows:
    for r in rows:
        print(dict(r))
else:
    print("（无记录）")

print()
print("=" * 60)
print(f"youzan_products  item_id={ITEM_ID}")
print("=" * 60)
rows = db.execute(
    "SELECT item_id, title, price_fen, stock, is_active, updated_at"
    " FROM youzan_products WHERE item_id = ?",
    (ITEM_ID,),
).fetchall()
for r in rows:
    print(dict(r))

print()
print("=" * 60)
print(f"knowledge_base  youzan_item_id={ITEM_ID}")
print("=" * 60)
rows = db.execute(
    "SELECT id, title, youzan_item_id, category, updated_at,"
    " SUBSTR(content, 1, 300) AS content_preview"
    " FROM knowledge_base WHERE youzan_item_id = ?",
    (ITEM_ID,),
).fetchall()
if rows:
    for r in rows:
        d = dict(r)
        print(f"  id={d['id']}")
        print(f"  title={d['title']}")
        print(f"  category={d['category']}")
        print(f"  updated_at={d['updated_at']}")
        print(f"  content_preview={d['content_preview']}")
        print()
else:
    print("（无记录）")

print()
print("=" * 60)
print("analytics_events（最近 10 条）")
print("=" * 60)
rows = db.execute(
    "SELECT event_type, event_source, ref_id, meta_data, created_at"
    " FROM analytics_events ORDER BY created_at DESC LIMIT 10"
).fetchall()
if rows:
    for r in rows:
        print(dict(r))
else:
    print("（无记录）")
