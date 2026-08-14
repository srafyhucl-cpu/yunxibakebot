#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 .secrets.baseline 未被 detect-secrets 意外改写。

detect-secrets 的 `--baseline` 验证路径在部分版本会原地重写 baseline。
本守卫在 detect-secrets 钩子之后运行：若 baseline 的 worktree 相对 index
出现未暂存改动（即工具意外改写），则阻断提交，要求恢复或走受控更新流程。

受控更新流程（G1）：候选副本生成 -> diff/哈希校验 -> 人工批准 -> 单文件替换。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BASELINE_REL = ".secrets.baseline"


def main() -> int:
    proc = subprocess.run(
        ["git", "diff", "--quiet", "--", BASELINE_REL],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode == 0:
        print("[secrets-baseline] OK：.secrets.baseline 未被改写")
        return 0
    print(
        "[secrets-baseline] FAIL：.secrets.baseline 相对 index 被改写。"
        "若为 detect-secrets 意外触发，执行 `git checkout -- .secrets.baseline` 恢复；"
        "若为有意更新，请按受控流程（候选副本 -> diff/哈希校验 -> 人工批准 -> 单文件替换）"
        "后再 `git add .secrets.baseline`。",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
