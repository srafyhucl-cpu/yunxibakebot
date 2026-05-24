"""
Knowledge seed script.

Seeds FAQ, rules, and service scripts from the `knowledge/` directory into
SQLite. Product knowledge is no longer imported from Markdown; product entries
must come from Youzan sync and runtime refresh flows.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import aiosqlite

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import PRAGMA_STATEMENTS, SCHEMA_STATEMENTS
from app.logger import setup_logger

logger = setup_logger()

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
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


def parse_faq(content: str) -> list[dict]:
    entries: list[dict] = []
    lines = content.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith("## Q: "):
            question = line.removeprefix("## Q: ").strip()
            answers: list[str] = []
            index += 1
            while index < len(lines):
                current = lines[index].strip()
                if current.startswith("## "):
                    index -= 1
                    break
                if current and not current.startswith(("#", ">")):
                    answers.append(current)
                index += 1
            if answers:
                entries.append(
                    {
                        "category": "faq",
                        "title": question,
                        "content": "\n".join(answers),
                        "keywords": question,
                        "priority": 5,
                    }
                )
        index += 1
    logger.info("Parsed %d FAQ entries", len(entries))
    return entries


def parse_scripts(content: str) -> list[dict]:
    entries: list[dict] = []
    lines = content.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith("### 话术"):
            title = line.removeprefix("###").strip()
            texts: list[str] = []
            index += 1
            while index < len(lines):
                current = lines[index].strip()
                if current.startswith("###"):
                    index -= 1
                    break
                if current and not current.startswith(("#", ">")):
                    texts.append(current)
                index += 1
            if texts:
                entries.append(
                    {
                        "category": "faq",
                        "title": title,
                        "content": "\n".join(texts),
                        "keywords": title,
                        "priority": 4,
                    }
                )
        index += 1
    logger.info("Parsed %d script entries", len(entries))
    return entries


def _read_enabled_files(directory: Path, file_names: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for file_name in file_names:
        file_path = directory / file_name
        if not file_path.exists():
            logger.warning("Knowledge file not found: %s", file_path)
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
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            if current_title and current_lines:
                entries.append(
                    {
                        "category": "after_sales",
                        "title": current_title,
                        "content": "\n".join(current_lines),
                        "keywords": current_keywords,
                        "priority": current_priority,
                    }
                )
            current_title = line.removeprefix("## ").strip()
            current_keywords, current_priority = AFTER_SALES_TITLE_SPECS.get(
                current_title,
                (current_title, 4),
            )
            current_lines = []
            continue
        if current_title:
            current_lines.append(line)
    if current_title and current_lines:
        entries.append(
            {
                "category": "after_sales",
                "title": current_title,
                "content": "\n".join(current_lines),
                "keywords": current_keywords,
                "priority": current_priority,
            }
        )
    return entries


def parse_rule_documents(files: list[Path]) -> list[dict]:
    entries: list[dict] = []
    for file_path in files:
        lines = file_path.read_text(encoding="utf-8").splitlines()
        if _extract_doc_meta(lines, "入库分类") == "after_sales":
            entries.extend(_parse_after_sales_rule_entries(lines))
            continue
        entry = _build_rule_entry(lines)
        if entry:
            entries.append(entry)
    logger.info("Parsed %d rule entries", len(entries))
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
    await conn.execute("DELETE FROM knowledge_base")
    await conn.commit()

    faq_files = _read_enabled_files(FAQ_DIR, ACTIVE_FAQ_FILES)
    faqs = _parse_text_files(faq_files, parse_faq)

    rule_files = _read_enabled_files(RULES_DIR, ACTIVE_RULE_FILES)
    rules = parse_rule_documents(rule_files)

    script_files = _read_enabled_files(SCRIPTS_DIR, ACTIVE_SCRIPT_FILES)
    scripts = _parse_text_files(script_files, parse_scripts)

    all_entries = [*faqs, *rules, *scripts]
    for entry in all_entries:
        await conn.execute(
            "INSERT INTO knowledge_base (category, title, content, keywords, priority) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                entry["category"],
                entry["title"],
                entry["content"],
                entry["keywords"],
                entry["priority"],
            ),
        )

    await conn.commit()
    await conn.close()
    logger.info(
        "Seed completed: total=%d faq=%d rules=%d scripts=%d",
        len(all_entries),
        len(faqs),
        len(rules),
        len(scripts),
    )


if __name__ == "__main__":
    asyncio.run(seed())
