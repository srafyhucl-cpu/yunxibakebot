"""
知识库种子脚本。

将 knowledge/ 目录下的数据导入 SQLite 知识库。
运行: python scripts/seed_knowledge.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import aiosqlite

from app.database import SCHEMA_STATEMENTS, PRAGMA_STATEMENTS
from app.logger import setup_logger

logger = setup_logger()

# 源数据路径（项目内）
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
PRODUCTS_FILE = KNOWLEDGE_DIR / "芸熙烘焙商品库知识库.md"
FAQ_FILE = KNOWLEDGE_DIR / "芸熙烘焙常见问题FAQ.md"
SERVICE_FILE = KNOWLEDGE_DIR / "芸熙烘焙通用服务与售后指引.md"

DB_PATH = "data/bot.db"


async def init_db() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    for pragma in PRAGMA_STATEMENTS:
        await conn.execute(pragma)
    for stmt in SCHEMA_STATEMENTS:
        await conn.execute(stmt)
    await conn.commit()
    return conn


def parse_products(content: str) -> list[dict]:
    """从商品库 Markdown 解析商品条目。"""
    entries: list[dict] = []
    lines = content.split("\n")
    current_category = "未分类"

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("## "):
            current_category = line.replace("## ", "").strip()

        elif line.startswith("！####"):
            title = line.replace("！####", "").strip()
            # 清理可能存在的 emoji
            title = re.sub(r"[^\w\s一-鿿\-（）()【】、,.\d]", "", title).strip()

            price_lines = []
            i += 1
            while i < len(lines):
                raw_line = lines[i]
                stripped = raw_line.strip()
                # 遇到下一个产品、分类标题或文档结尾时停止
                if stripped.startswith("！####") or stripped.startswith("## ") or stripped.startswith("！###"):
                    i -= 1
                    break
                # 收集价格相关的行（含规格、价格、配送信息）
                if "元" in stripped or "规格" in stripped or "价格" in stripped or "配送" in stripped:
                    price_lines.append(stripped)
                i += 1

            specs = "，".join(price_lines)
            entries.append({
                "category": "product",
                "title": title,
                "content": f"分类: {current_category} | {specs}" if specs else f"分类: {current_category}",
                "keywords": title,
                "priority": 1,
            })

        i += 1

    logger.info("解析到 %d 个商品", len(entries))
    return entries


def parse_faq(content: str) -> list[dict]:
    """从 FAQ 解析问答条目。"""
    entries = []
    q_pattern = re.compile(r"！### Q: (.+)")

    lines = content.split("\n")
    i = 0
    while i < len(lines):
        q_match = q_pattern.search(lines[i])
        if q_match:
            question = q_match.group(1).strip()
            answers = []
            i += 1
            while i < len(lines):
                if "！###" in lines[i]:
                    i -= 1
                    break
                stripped = lines[i].strip()
                if stripped and not stripped.startswith(("！", "#'")):
                    answers.append(stripped)
                i += 1

            if answers:
                entries.append({
                    "category": "faq",
                    "title": question,
                    "content": "\n".join(answers),
                    "keywords": question,
                    "priority": 5,
                })
        i += 1

    logger.info("解析到 %d 条 FAQ", len(entries))
    return entries


def parse_service() -> list[dict]:
    """预设服务与售后知识条目。"""
    return [
        {
            "category": "policy",
            "title": "预订与配送规则",
            "content": "常规蛋糕建议提前3-5小时预订，节日款建议提前1-2天。退改：24小时以上全额退款，4-24小时扣30%材料费，4小时内不支持退款改期。",
            "keywords": "预订,配送,退改,取消,改期",
            "priority": 5,
        },
        {
            "category": "policy",
            "title": "蛋糕配件与收费标准",
            "content": "标配5人份餐具+生日帽+蜡烛。额外餐具2元/套，数字蜡烛2元/支，烟花/音乐蜡烛5-10元/支。",
            "keywords": "配件,餐具,蜡烛",
            "priority": 4,
        },
        {
            "category": "store_info",
            "title": "动物奶油说明",
            "content": "使用100%进口动物奶油（安佳/蓝风车），无植物奶油。动物奶油蛋糕需冷藏0-4℃保存，最佳24小时内食用，常温不超过1小时。",
            "keywords": "奶油,动物奶油,保存,冷藏",
            "priority": 5,
        },
        {
            "category": "after_sales",
            "title": "配送损坏处理",
            "content": "配送磕碰损坏：请客户拍下受损照片，转接人工售后经理，根据受损程度退款或补发或补偿优惠券。",
            "keywords": "损坏,配送损坏,售后",
            "priority": 5,
        },
        {
            "category": "after_sales",
            "title": "漏发配件处理",
            "content": "漏发蜡烛/餐具：可紧急闪送补发，或全额退还配件费用并补偿优惠券。",
            "keywords": "漏发,配件,补发",
            "priority": 4,
        },
        {
            "category": "after_sales",
            "title": "配送超时处理",
            "content": "超时30分钟以上视情况申请运费补偿，售后专员对接。",
            "keywords": "超时,配送超时",
            "priority": 4,
        },
        {
            "category": "policy",
            "title": "团购与企业订单",
            "content": "企业团购5件以上9折。支持增值税电子普通发票，1-3个工作日开出。",
            "keywords": "团购,企业,发票,折扣",
            "priority": 3,
        },
    ]


async def seed() -> None:
    conn = await init_db()

    # 清空旧数据
    await conn.execute("DELETE FROM knowledge_base")
    await conn.commit()

    # 1. 导入商品
    products_text = PRODUCTS_FILE.read_text(encoding="utf-8")
    products = parse_products(products_text)

    # 2. 导入 FAQ
    faq_text = FAQ_FILE.read_text(encoding="utf-8")
    faqs = parse_faq(faq_text)

    # 3. 导入服务/政策知识
    services = parse_service()

    all_entries = products + faqs + services
    for entry in all_entries:
        await conn.execute(
            "INSERT INTO knowledge_base (category, title, content, keywords, priority) "
            "VALUES (?, ?, ?, ?, ?)",
            (entry["category"], entry["title"], entry["content"],
             entry["keywords"], entry["priority"]),
        )

    await conn.commit()
    await conn.close()
    logger.info("导入完成！共 %d 条知识（产品 %d，FAQ %d，服务 %d）",
                len(all_entries), len(products), len(faqs), len(services))


if __name__ == "__main__":
    asyncio.run(seed())
