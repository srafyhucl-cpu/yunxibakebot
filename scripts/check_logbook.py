# -*- coding: utf-8 -*-
"""
Pre-commit hook: 检查本次暂存的变更是否包含 LOGBOOK.md 更新。
当有 .py / .html / .css 文件被暂存时，要求 LOGBOOK.md 也在暂存区。
"""
import subprocess
import sys

SKIP_SENTINEL = "SKIP_LOGBOOK_CHECK"


def get_staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().splitlines()


CODE_EXTENSIONS = {".py", ".html", ".css", ".js"}


def main() -> int:
    import os
    if os.environ.get(SKIP_SENTINEL):
        print("[logbook-check] 跳过检查（环境变量 SKIP_LOGBOOK_CHECK 已设置）")
        return 0

    staged = get_staged_files()
    if not staged:
        return 0

    has_code = any(
        any(f.endswith(ext) for ext in CODE_EXTENSIONS)
        for f in staged
    )
    if not has_code:
        return 0

    if "LOGBOOK.md" in staged:
        return 0

    print(
        "\n[logbook-check] ❌ 检测到代码文件变更，但 LOGBOOK.md 未在暂存区。\n"
        "\n"
        "  请先更新 LOGBOOK.md（在顶部追加本轮变更记录），然后 git add LOGBOOK.md。\n"
        "  格式参见 .windsurf/workflows/commit.md 第 4 步。\n"
        "\n"
        "  如确认本次变更无需记录（纯配置/格式修正），可临时跳过：\n"
        f"    SKIP_LOGBOOK_CHECK=1 git commit ...\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
