import sqlite3
import json
import os

db_path = 'data/bot.db'
if not os.path.exists(db_path):
    print("DB not found")
    exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT id, title, content, content_type FROM knowledge_base WHERE category != 'product'")
entries = [{'id': row[0], 'title': row[1], 'content': row[2], 'type': row[3]} for row in c.fetchall()]

with open('exported_knowledge_utf8.json', 'w', encoding='utf-8') as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)
