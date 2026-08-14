#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 .secrets.baseline 未被意外改写，并强制受控更新流程。

detect-secrets 的 `--baseline` 验证路径在部分版本会原地重写 baseline。
本守卫在 detect-secrets 钩子之后运行，检查三方状态：

1. worktree 相对 index 的未暂存污染（detect-secrets 意外改写）→ 阻断。
2. index 相对 HEAD 的已暂存变更 → 必须附受控记录（旧/新 SHA-256、命令、版本、trace、批准人），
   见 docs/harness-engineering/core/secrets-baseline-changes.md，否则阻断。

受控更新流程：候选副本生成 -> diff/哈希校验 -> 人工批准 -> 记录到 secrets-baseline-changes.md -> git add。
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BASELINE_REL = ".secrets.baseline"
CHANGES_LOG = (
    ROOT_DIR / "docs" / "harness-engineering" / "core" / "secrets-baseline-changes.md"
)


def _git_show(ref: str) -> bytes | None:
    # ":" 表示 index，使用 stage 0 语法避免 magic pathspec 干扰
    expr = f":0:{BASELINE_REL}" if ref == ":" else f"{ref}:{BASELINE_REL}"
    proc = subprocess.run(
        ["git", "show", expr],
        cwd=ROOT_DIR,
        capture_output=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def _sha256(data: bytes | None) -> str:
    return hashlib.sha256(data or b"").hexdigest()


def _approved_records() -> list[tuple[str, str]]:
    """解析受控记录文件，返回 [(old_sha256, new_sha256), ...]。"""
    if not CHANGES_LOG.exists():
        return []
    text = CHANGES_LOG.read_text(encoding="utf-8")
    records: list[tuple[str, str]] = []
    old = new = None
    for line in text.splitlines():
        m = re.match(r"^- old_sha256:\s*([0-9a-f]{64})", line.strip())
        if m:
            old = m.group(1)
        m = re.match(r"^- new_sha256:\s*([0-9a-f]{64})", line.strip())
        if m:
            new = m.group(1)
        if old and new:
            records.append((old, new))
            old = new = None
    return records


def main() -> int:
    # 1) worktree vs index：未暂存污染
    proc = subprocess.run(
        ["git", "diff", "--quiet", "--", BASELINE_REL],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        print(
            "[secrets-baseline] FAIL：.secrets.baseline 相对 index 存在未暂存改动。"
            "若为 detect-secrets 意外触发，执行 `git checkout -- .secrets.baseline` 恢复；"
            "若为有意更新，请按受控流程（候选副本 -> diff/哈希 -> 人工批准 -> 记录 -> git add）。",
            file=sys.stderr,
        )
        return 1

    # 2) index vs HEAD：已暂存变更必须附受控记录
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", BASELINE_REL],
        cwd=ROOT_DIR,
        capture_output=True,
    )
    if staged.returncode != 0:
        head_sha = _sha256(_git_show("HEAD"))
        index_sha = _sha256(_git_show(":"))
        if (head_sha, index_sha) not in _approved_records():
            print(
                "[secrets-baseline] FAIL：.secrets.baseline 存在已暂存变更，但缺少受控记录。"
                "请在 docs/harness-engineering/core/secrets-baseline-changes.md 登记 "
                "old_sha256/new_sha256/命令/版本/trace/批准人 后再提交。",
                file=sys.stderr,
            )
            return 1

    print("[secrets-baseline] OK：.secrets.baseline 状态一致且符合受控流程")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
