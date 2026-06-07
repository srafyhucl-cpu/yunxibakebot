"""文件体量门禁脚本。

在 pre-commit 阶段检查本项目所有 .py 文件是否超过 blocking 阈值。
超线时打印详情并以非零退出码阻断提交。
"""

import sys
from pathlib import Path

# 强制 stdout 使用 UTF-8，避免 Windows GBK 编码下 pre-commit 管道卡死
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except AttributeError:
    pass  # Python < 3.7 或某些环境不支持 reconfigure，忽略即可

# blocking 阈值（行数）：各层模块上限
BLOCKING_RULES: list[tuple[str, int]] = [
    ("app/repository/", 250),
    ("app/service/llm/", 180),
    ("app/service/youzan/", 250),
    ("app/service/", 320),
    ("app/api/", 350),
    ("app/", 400),
]

# 忽略目录（不参与检查）
IGNORE_DIRS = {"__pycache__", ".git", "venv", "node_modules", "migrations"}

# 已知超线但尚未完成拆分的存量文件（仅发出警告，不阻断提交）
# 完成拆分后请从此名单移除
KNOWN_OVERSIZE = {
    "app/repository/knowledge_repo.py",  # 254行，超出4行，待微调
    "app/service/chat.py",  # 496行，核心链路，待拆 tool_executor
    "app/service/observability.py",  # 353行，待拆分页查询与报表
    "app/service/llm/function_tool_order.py",  # 181行，超出1行
    "app/service/llm/function_tool_product.py",  # 252行，待拆 product_rag_helper
    "app/service/youzan/event_item.py",  # 396行，待拆 item_builder
    "app/service/wecom/client_kf.py",  # 387行，mixin模式待拆分
    "app/service/wecom/kf_message_queue.py",  # 348行，待拆消息处理链路
    # app/database.py 已拆分，365 行，无超线
}


def get_limit(rel: str) -> int:
    """按最精确路径前缀返回 blocking 阈值。"""
    for prefix, limit in BLOCKING_RULES:
        if rel.replace("\\", "/").startswith(prefix):
            return limit
    return 400


def count_lines(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8").splitlines())
    except Exception:
        return 0


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    violations: list[str] = []

    app_root = root / "app"
    warnings: list[str] = []
    for py_file in sorted(app_root.rglob("*.py")):
        parts = py_file.relative_to(root).parts
        if any(d in IGNORE_DIRS for d in parts):
            continue
        rel = str(py_file.relative_to(root))
        rel_unix = rel.replace("\\", "/")
        limit = get_limit(rel_unix)
        lines = count_lines(py_file)
        if lines > limit:
            msg = (
                f"  {rel_unix}: {lines} 行（上限 {limit} 行，超出 {lines - limit} 行）"
            )
            if rel_unix in KNOWN_OVERSIZE:
                warnings.append(msg)
            else:
                violations.append(msg)

    if warnings:
        print(
            "\n[WARN] 已知存量超线文件（不阻断提交，完成拆分后请从 KNOWN_OVERSIZE 移除）："
        )
        for w in warnings:
            print(w)

    if violations:
        print("\n[ERROR] 文件体量超线，提交被阻断：")
        for v in violations:
            print(v)
        print("\n请先拆分超线文件，再重新提交。")
        return 1

    print(
        f"[OK] 文件体量检查通过（共检查 {sum(1 for _ in app_root.rglob('*.py'))} 个文件）"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
