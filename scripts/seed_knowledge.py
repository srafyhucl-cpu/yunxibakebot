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
FAQ_DIR = KNOWLEDGE_DIR / "FAQ"
RULES_DIR = KNOWLEDGE_DIR / "规则"
SCRIPTS_DIR = KNOWLEDGE_DIR / "话术"

DB_PATH = "data/bot.db"
ACTIVE_FAQ_FILES: tuple[str, ...] = (
    "基础服务FAQ.md",
    "商品选购FAQ.md",
    "场景与会员FAQ.md",
)
ACTIVE_RULE_FILES: tuple[str, ...] = (
    "订购与履约规则.md",
    "商品通用规则.md",
    "售后规则.md",
    "企业服务规则.md",
)
ACTIVE_SCRIPT_FILES: tuple[str, ...] = (
    "下单引导话术.md",
    "售后安抚话术.md",
)
AFTER_SALES_TITLE_SPECS: dict[str, tuple[str, int]] = {
    "配送损坏处理": ("损坏,配送损坏,售后,破损", 5),
    "漏发配件处理": ("漏发,配件,补发,售后", 4),
    "配送超时处理": ("超时,配送超时,售后", 4),
}


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


def parse_scripts(content: str) -> list[dict]:
    """解析话术库（！#### 话术N 标题）。"""
    entries: list[dict] = []
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("！#### 话术"):
            title = line.replace("！####", "").strip()
            texts: list[str] = []
            i += 1
            while i < len(lines):
                stripped = lines[i].strip()
                if stripped.startswith("！####"):
                    i -= 1
                    break
                if stripped and not stripped.startswith(("！", "#")):
                    texts.append(stripped)
                i += 1
            if texts:
                entries.append({
                    "category": "faq",
                    "title": title,
                    "content": "\n".join(texts),
                    "keywords": title,
                    "priority": 4,
                })
        i += 1
    logger.info("解析到 %d 条话术", len(entries))
    return entries


def _read_enabled_files(directory: Path, file_names: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for file_name in file_names:
        file_path = directory / file_name
        if not file_path.exists():
            logger.warning("知识文件不存在: %s", file_path)
            continue
        files.append(file_path)
    return files


def _parse_text_files(files: list[Path], parser) -> list[dict]:
    entries: list[dict] = []
    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        entries.extend(parser(text))
    return entries


def _extract_doc_meta(lines: list[str], key: str) -> str:
    marker = f"> {key}："
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(marker):
            return stripped.removeprefix(marker).strip()
    return ""


def _extract_document_body_lines(lines: list[str]) -> list[str]:
    body_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ">")):
            continue
        body_lines.append(stripped)
    return body_lines


def _build_rule_entry(lines: list[str]) -> dict | None:
    category = _extract_doc_meta(lines, "入库分类")
    title = _extract_doc_meta(lines, "入库标题")
    keywords = _extract_doc_meta(lines, "入库关键词")
    priority_text = _extract_doc_meta(lines, "入库优先级")
    body_lines = _extract_document_body_lines(lines)
    if not (category and title and keywords and priority_text and body_lines):
        return None
    return {
        "category": category,
        "title": title,
        "content": "\n".join(body_lines),
        "keywords": keywords,
        "priority": int(priority_text),
    }


def _parse_after_sales_rule_entries(lines: list[str]) -> list[dict]:
    entries: list[dict] = []
    current_title = ""
    current_keywords = ""
    current_priority = 0
    current_lines: list[str] = []
    for line in _extract_document_body_lines(lines):
        if line.startswith("！## "):
            continue
        if line.startswith("！### "):
            if current_title and current_lines:
                entries.append({
                    "category": "after_sales",
                    "title": current_title,
                    "content": "\n".join(current_lines),
                    "keywords": current_keywords,
                    "priority": current_priority,
                })
            current_title = line.removeprefix("！### ").strip()
            current_keywords, current_priority = AFTER_SALES_TITLE_SPECS.get(
                current_title,
                (current_title, 4),
            )
            current_lines = []
            continue
        if current_title:
            current_lines.append(line)
    if current_title and current_lines:
        entries.append({
            "category": "after_sales",
            "title": current_title,
            "content": "\n".join(current_lines),
            "keywords": current_keywords,
            "priority": current_priority,
        })
    return entries


def parse_rule_documents(files: list[Path]) -> list[dict]:
    entries: list[dict] = []
    for file_path in files:
        lines = file_path.read_text(encoding="utf-8").split("\n")
        if _extract_doc_meta(lines, "入库分类") == "after_sales":
            entries.extend(_parse_after_sales_rule_entries(lines))
            continue
        entry = _build_rule_entry(lines)
        if entry:
            entries.append(entry)
    logger.info("解析到 %d 条服务规则", len(entries))
    return entries


async def init_db() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    for pragma in PRAGMA_STATEMENTS:
        await conn.execute(pragma)
    for stmt in SCHEMA_STATEMENTS:
        await conn.execute(stmt)
    await conn.commit()
    return conn


async def seed() -> None:
    conn = await init_db()

    # 清空旧数据
    await conn.execute("DELETE FROM knowledge_base")
    await conn.commit()

    # 1. 导入商品
    products_text = PRODUCTS_FILE.read_text(encoding="utf-8")
    products = parse_products(products_text)

    # 2. 导入 FAQ
    faq_files = _read_enabled_files(FAQ_DIR, ACTIVE_FAQ_FILES)
    faqs = _parse_text_files(faq_files, parse_faq)

    # 3. 导入服务/政策知识
    rule_files = _read_enabled_files(RULES_DIR, ACTIVE_RULE_FILES)
    rules = parse_rule_documents(rule_files)

    # 4. 导入客服话术
    script_files = _read_enabled_files(SCRIPTS_DIR, ACTIVE_SCRIPT_FILES)
    scripts = _parse_text_files(script_files, parse_scripts)

    all_entries = products + faqs + rules + scripts
    for entry in all_entries:
        await conn.execute(
            "INSERT INTO knowledge_base (category, title, content, keywords, priority) "
            "VALUES (?, ?, ?, ?, ?)",
            (entry["category"], entry["title"], entry["content"],
             entry["keywords"], entry["priority"]),
        )

    await conn.commit()
    await conn.close()
    logger.info("导入完成！共 %d 条知识（产品 %d，FAQ %d，服务 %d，话术 %d）",
                len(all_entries), len(products), len(faqs), len(rules),
                len(scripts))


if __name__ == "__main__":
    asyncio.run(seed())
