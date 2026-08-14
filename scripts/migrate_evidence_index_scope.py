#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 evidence-index.md 迁移到工件级引用与完整性 schema（B1.6）。

对每个证据条目做机械迁移：
1. `file` 字段中的引用统一为工件级前缀：
   - D:/Project/YunxiBakeBot/<rel>（或反斜杠变体）→ `repo:<rel>`（reports/harness 下为 `local:<rel>`）
   - /opt/... → `production:<abs>`
   - 其他绝对路径 → `external:<abs>`
   - 裸相对路径 → `repo:<rel>`
   - 已是前缀 / http(s) → 保留
2. 补充 `storage_scope`（repository / local / production / external，按 file 引用优先级判定）。
3. 为 repo: 文件引用补充 `sha256`（目录引用不哈希）；已有 sha256 的条目保留。

幂等：已带前缀的引用、已有 storage_scope / sha256 的条目不重复处理。
运行：python scripts/migrate_evidence_index_scope.py [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INDEX = ROOT_DIR / "docs" / "harness-engineering" / "core" / "evidence-index.md"
ENTRY_HEADING_RE = re.compile(r"^##\s+(E-\d{8}-\d{3})：(.+)$")
FILE_REFERENCE_RE = re.compile(r"`([^`]+)`")
REFERENCE_PREFIXES = ("repo:", "local:", "production:", "external:")
REGISTRY_REL = "docs/harness-engineering/core/evidence-index.md"
LEGACY_FILE_ALIASES = {
    "app/service/wecom/employee_agent_reply_guard.py": "app/service/wecom/employee_agent_mixed_reply.py",
    "app/service/wecom/employee_agent_order_list_guard.py": "app/service/wecom/intelligent_bot_order_lookup.py",
    "app/service/wecom/employee_agent_llm_plan.py": "app/service/wecom/employee_agent_planner.py",
    "tests/service/test_miniapp_order.py": "tests/service/test_order.py",
    "tests/service/test_miniapp_chat.py": "tests/api/test_miniapp_chat_api.py",
    "tests/service/llm": "tests/service/test_llm_provider.py",
    "tests/service/agents": "tests/service/agents/test_llm_factory.py",
}


def _prefix_reference(reference: str) -> str:
    norm = reference.strip()
    forward = norm.replace("\\", "/")
    if forward.startswith(("http://", "https://")):
        return norm
    if forward.startswith(REFERENCE_PREFIXES):
        scope = forward.split(":", 1)[0]
        rel = forward.split(":", 1)[1].lstrip("/").replace("\\", "/")
        if scope == "repo" and rel.startswith("reports/"):
            return f"local:{rel}"
        return norm
    match = re.match(r"^[A-Za-z]:/Project/YunxiBakeBot/(.*)$", forward)
    if match:
        rel = match.group(1).lstrip("/")
        if rel.startswith("reports/"):
            return f"local:{rel}"
        return f"repo:{rel}"
    if forward.startswith("/opt/"):
        return f"production:{forward}"
    if forward.startswith("/") or re.match(r"^[A-Za-z]:/", forward):
        return f"external:{forward}"
    if norm:
        bare = norm.replace(chr(92), "/")
        if bare.startswith("reports/"):
            return f"local:{bare}"
        return f"repo:{bare}"
    return norm


def _scope_for_references(references: list[str]) -> str:
    for prefix, scope in (
        ("production:", "production"),
        ("repo:", "repository"),
        ("local:", "local"),
        ("external:", "external"),
    ):
        if any(ref.startswith(prefix) for ref in references):
            return scope
    return "external"


def _hash_repo_files(references: list[str]) -> list[tuple[str, str]]:
    """为存在且为文件的 repo: 引用计算 sha256，返回 (rel, digest) 列表。"""
    hashed: list[tuple[str, str]] = []
    for reference in references:
        if not reference.startswith("repo:"):
            continue
        rel = reference.split(":", 1)[1].lstrip("/").replace("\\", "/")
        if rel == REGISTRY_REL:
            continue
        actual_rel = LEGACY_FILE_ALIASES.get(rel, rel)
        path = ROOT_DIR / actual_rel
        if not path.exists() or path.is_dir():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashed.append((rel, digest))
    return hashed


def _format_hashes(hashed: list[tuple[str, str]]) -> str | None:
    if not hashed:
        return None
    if len(hashed) == 1:
        return hashed[0][1]
    return "；".join(f"{rel}={digest}" for rel, digest in hashed)


def _merge_sha256(
    existing: str,
    hashed: list[tuple[str, str]],
    refs: list[str],
) -> str | None:
    """合并既有 sha256 与最新 repo 哈希。

    只保留指向 repo: 文件引用的哈希（local: 为可选/仅格式校验，生成物每次
    运行会漂移）；纯 hex（单文件语义）先归属到恰好匹配该哈希的 repo 文件，
    再被最新 repo 哈希覆盖。
    """
    repo_rels = {
        ref.split(":", 1)[1].lstrip("/").replace("\\", "/")
        for ref in refs
        if ref.startswith("repo:")
    }
    repo_rels.discard(REGISTRY_REL)
    merged: dict[str, str] = {}
    if "=" in existing:
        for part in existing.split("；"):
            if "=" in part:
                key, value = part.split("=", 1)
                key = key.strip()
                if key in repo_rels:
                    merged[key] = value.strip()
    elif re.fullmatch(r"[0-9a-f]{64}", existing.strip()):
        for ref in refs:
            if not ref.startswith("repo:"):
                continue
            rel = ref.split(":", 1)[1].lstrip("/").replace("\\", "/")
            if rel == REGISTRY_REL:
                continue
            actual_rel = LEGACY_FILE_ALIASES.get(rel, rel)
            path = ROOT_DIR / actual_rel
            if not path.exists() or path.is_dir():
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() == existing.strip():
                merged[rel] = existing.strip()
                break
    for rel, digest in hashed:
        merged[rel] = digest
    return _format_hashes(list(merged.items()))


def _transform_file_field(value: str) -> tuple[str, list[str]]:
    refs = FILE_REFERENCE_RE.findall(value)
    replaced: dict[str, str] = {}
    for ref in refs:
        if ref not in replaced:
            replaced[ref] = _prefix_reference(ref)
    for old, new in replaced.items():
        value = value.replace(f"`{old}`", f"`{new}`")
    return value, list(replaced.values())


def _process_entry(lines: list[str]) -> tuple[list[str], int]:
    """迁移单个条目行块，返回 (新行, 修改计数)。"""
    changes = 0
    file_field_idx = next(
        (i for i, line in enumerate(lines) if re.match(r"^-\s+file:", line)), None
    )
    if file_field_idx is None:
        return lines, changes
    raw_value = re.sub(r"^-\s+file:\s*", "", lines[file_field_idx])
    new_value, refs = _transform_file_field(raw_value)
    if new_value != raw_value:
        lines[file_field_idx] = f"- file: {new_value}"
        changes += 1

    prefixed_refs = [
        ref.strip().replace("\\", "/")
        for ref in refs
        if not ref.strip().startswith(("http://", "https://"))
    ]
    if not any(line.startswith("- storage_scope:") for line in lines):
        scope = _scope_for_references(prefixed_refs)
        lines.append(f"- storage_scope: {scope}")
        changes += 1

    hashed = _hash_repo_files([ref for ref in prefixed_refs if ref.startswith("repo:")])
    sha_index = next(
        (i for i, line in enumerate(lines) if line.startswith("- sha256:")),
        None,
    )
    if sha_index is None:
        if hashed:
            lines.append(f"- sha256: {_format_hashes(hashed)}")
            changes += 1
    else:
        existing = re.sub(r"^-\s+sha256:\s*", "", lines[sha_index])
        merged = _merge_sha256(existing, hashed, prefixed_refs)
        if merged and merged != existing:
            lines[sha_index] = f"- sha256: {merged}"
            changes += 1
    return lines, changes


def migrate(path: Path = DEFAULT_INDEX, *, dry_run: bool = False) -> int:
    path = Path(path)
    if not path.exists():
        print(f"[migrate-evidence] FAIL：找不到索引 {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8-sig")
    out_lines: list[str] = []
    current: list[str] = []
    total_changes = 0
    entry_count = 0

    for raw_line in text.splitlines():
        raw_line = raw_line.removeprefix("\ufeff")
        if ENTRY_HEADING_RE.match(raw_line):
            if current:
                entry_count += 1
                new_lines, changes = _process_entry(current)
                total_changes += changes
                out_lines.extend(new_lines)
            current = [raw_line]
        elif re.match(r"^##\s+", raw_line):
            if current:
                entry_count += 1
                new_lines, changes = _process_entry(current)
                total_changes += changes
                out_lines.extend(new_lines)
            current = []
            out_lines.append(raw_line)
        elif current:
            current.append(raw_line)
        else:
            out_lines.append(raw_line)
    if current:
        entry_count += 1
        new_lines, changes = _process_entry(current)
        total_changes += changes
        out_lines.extend(new_lines)

    print(
        f"[migrate-evidence] 条目 {entry_count}，修改行 {total_changes}"
        + ("（dry-run，未写回）" if dry_run else "")
    )
    if dry_run:
        return 0
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="迁移 evidence index 到工件级引用")
    parser.add_argument("--path", default=str(DEFAULT_INDEX), help="索引路径")
    parser.add_argument("--dry-run", action="store_true", help="只统计不写回")
    return parser


if __name__ == "__main__":
    raise SystemExit(migrate(**vars(build_parser().parse_args())))
