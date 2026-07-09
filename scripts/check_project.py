"""项目质量门禁统一入口。"""

import argparse
import ast
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = ROOT_DIR / "app"
PYTHON_EXT = ".py"
TEXT_ENCODING = "utf-8"

ROOT_API_COMPAT_FILES: tuple[Path, ...] = (
    APP_DIR / "api" / "admin_addresses.py",
    APP_DIR / "api" / "admin_assets.py",
    APP_DIR / "api" / "admin_config.py",
    APP_DIR / "api" / "admin_dialog.py",
    APP_DIR / "api" / "admin_frontend.py",
    APP_DIR / "api" / "admin_knowledge.py",
    APP_DIR / "api" / "admin_observability.py",
    APP_DIR / "api" / "admin_orders.py",
    APP_DIR / "api" / "admin_products.py",
    APP_DIR / "api" / "admin_shop_pages.py",
    APP_DIR / "api" / "admin_transfer.py",
    APP_DIR / "api" / "channel_router.py",
    APP_DIR / "api" / "miniapp_auth.py",
    APP_DIR / "api" / "miniapp_addresses.py",
    APP_DIR / "api" / "miniapp_catalog.py",
    APP_DIR / "api" / "miniapp_chat.py",
    APP_DIR / "api" / "miniapp_orders.py",
    APP_DIR / "api" / "miniapp_payments.py",
    APP_DIR / "api" / "webhook.py",
    APP_DIR / "api" / "webhook_helpers.py",
    APP_DIR / "api" / "wecom.py",
)


@dataclass(frozen=True)
class ScanRule:
    name: str
    pattern: str
    paths: tuple[Path, ...]
    should_block: bool = True


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    details: list[str]


RED_LINE_RULES: tuple[ScanRule, ...] = (
    ScanRule("禁止 Optional/Union", r"Optional\[|Union\[", (APP_DIR,)),
    ScanRule("禁止 TODO 占位", r"# TODO", (APP_DIR,)),
    ScanRule("禁止 SELECT 星号", r"SELECT\s+\*", (APP_DIR,)),
    ScanRule(
        "app 内禁止依赖 miniapp service 兼容层",
        r"from app\.service\.miniapp_|import app\.service\.miniapp_",
        (APP_DIR,),
    ),
    ScanRule(
        "根 API 兼容文件仅作为兼容入口",
        r"from fastapi import|APIRouter\(|@router\.",
        ROOT_API_COMPAT_FILES,
    ),
    ScanRule(
        "api 层禁止直接导入 repository", r"from app\.repository", (APP_DIR / "api",)
    ),
    ScanRule(
        "service 层禁止直连 aiosqlite",
        r"import aiosqlite|aiosqlite\.",
        (APP_DIR / "service",),
    ),
    ScanRule(
        "models 层禁止引用上层模块",
        r"from app\.(service|repository|api)",
        (APP_DIR / "models",),
    ),
    ScanRule("禁止 SQL f-string 拼接", r"f\"(SELECT|INSERT|UPDATE|DELETE)", (APP_DIR,)),
    ScanRule("禁止静默吞异常", r"except.*:\s*pass", (APP_DIR,)),
    ScanRule(
        "禁止硬编码密钥", r"api_key\s*=\s*[\"']sk-|secret\s*=\s*[\"']", (APP_DIR,)
    ),
    ScanRule("app 内禁止裸 print", r"^\s+print\(", (APP_DIR,)),
    ScanRule("禁止英文注释", r"^\s*#\s+(?!.*[\u4e00-\u9fff])[A-Za-z]", (APP_DIR,)),
)

TEST_COMMANDS: tuple[tuple[str, ...], ...] = (
    (sys.executable, "-m", "pytest", "-q", "--tb=short"),
)

CONTRACT_COMMANDS: tuple[tuple[str, ...], ...] = (
    (
        sys.executable,
        "scripts/check_employee_agent_capability_contracts.py",
        "--summary",
    ),
    (sys.executable, "scripts/check_customer_rag_golden_cases.py", "--summary"),
    (sys.executable, "scripts/check_knowledge_governance_plan.py", "--summary"),
    (
        sys.executable,
        "scripts/check_customer_memory_governance_plan.py",
        "--summary",
    ),
    (
        sys.executable,
        "scripts/check_customer_observability_contract.py",
        "--summary",
    ),
    (
        sys.executable,
        "scripts/check_miniapp_page_api_contract.py",
        "--summary",
    ),
    (
        sys.executable,
        "scripts/check_github_reference_implementation_plan.py",
        "--summary",
    ),
    (
        sys.executable,
        "scripts/check_langchain_ai_layer_production_plan.py",
        "--summary",
    ),
    (
        sys.executable,
        "scripts/check_real_conversation_replay_pool.py",
        "--summary",
    ),
    (
        sys.executable,
        "scripts/check_real_conversation_replay_intake_readiness.py",
        "--summary",
    ),
    (
        sys.executable,
        "scripts/build_real_conversation_replay_intake_packet.py",
        "--summary",
    ),
    (
        sys.executable,
        "scripts/check_langsmith_runtime_config.py",
        "--summary",
    ),
    (
        sys.executable,
        "scripts/report_langchain_observability_evidence.py",
        "--summary",
    ),
)

# ── 洁净代码检查常量 ────────────────────────────────────────────────────────
# 函数体行数上限（超出此值记录警告，暂不阻断；待存量修复后升级为 BLOCK）
FUNC_MAX_LINES = 50

# 禁止在函数体内直接硬编码的平台域名（必须通过模块级常量引用）
HARDCODED_DOMAINS: tuple[str, ...] = (
    "h5.youzan.com",
    "qyapi.weixin.qq.com",
    "open.youzanyun.com",
)

# 必须命名为常量的已知业务魔法整数
KNOWN_MAGIC_INTEGERS: frozenset[int] = frozenset(
    {
        172800,
        86400,
        43200,
        604800,  # 秒级时间常量
    }
)


def _parse_ast(file_path: Path) -> ast.Module | None:
    """安全解析 Python 文件为 AST，语法错误时返回 None。"""
    try:
        return ast.parse(
            file_path.read_text(encoding=TEXT_ENCODING), filename=str(file_path)
        )
    except SyntaxError:
        return None


def check_hardcoded_urls_in_functions(app_dir: Path) -> CheckResult:
    """检查函数体内是否存在硬编码平台域名 URL（应通过模块级常量引用）。"""
    violations: list[str] = []
    for file_path in iter_python_files((app_dir,)):
        tree = _parse_ast(file_path)
        if tree is None:
            continue
        for func_node in ast.walk(tree):
            if not isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for child in ast.walk(func_node):
                if child is func_node:
                    continue
                if not (
                    isinstance(child, ast.Constant) and isinstance(child.value, str)
                ):
                    continue
                if any(domain in child.value for domain in HARDCODED_DOMAINS):
                    rel = file_path.relative_to(ROOT_DIR)
                    violations.append(f"{rel}:{child.lineno}: {child.value[:80]!r}")
    return CheckResult("函数体内禁止硬编码平台 URL", not violations, violations)


def check_known_magic_integers(app_dir: Path) -> CheckResult:
    """检查函数体内是否存在已知业务魔法整数（应提取为命名常量）。"""
    violations: list[str] = []
    for file_path in iter_python_files((app_dir,)):
        tree = _parse_ast(file_path)
        if tree is None:
            continue
        for func_node in ast.walk(tree):
            if not isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for child in ast.walk(func_node):
                if child is func_node:
                    continue
                if (
                    isinstance(child, ast.Constant)
                    and child.value in KNOWN_MAGIC_INTEGERS
                ):
                    rel = file_path.relative_to(ROOT_DIR)
                    violations.append(
                        f"{rel}:{child.lineno}: 魔法整数 {child.value!r}（请提取为命名常量）"
                    )
    return CheckResult("函数体内禁止已知业务魔法整数", not violations, violations)


def check_function_lengths(app_dir: Path) -> list[str]:
    """扫描超过 FUNC_MAX_LINES 行的函数，返回警告列表（不阻断）。"""
    warnings: list[str] = []
    for file_path in iter_python_files((app_dir,)):
        tree = _parse_ast(file_path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not (hasattr(node, "end_lineno") and node.end_lineno):
                continue
            func_lines = node.end_lineno - node.lineno
            if func_lines > FUNC_MAX_LINES:
                rel = file_path.relative_to(ROOT_DIR)
                warnings.append(
                    f"{rel}:{node.lineno}: `{node.name}()` {func_lines} 行（上限 {FUNC_MAX_LINES}）"
                )
    return warnings


def iter_python_files(paths: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == PYTHON_EXT:
            files.append(path)
            continue
        if path.exists():
            files.extend(sorted(path.rglob(f"*{PYTHON_EXT}")))
    return files


def scan_rule(rule: ScanRule) -> CheckResult:
    regex = re.compile(rule.pattern)
    matches: list[str] = []
    for file_path in iter_python_files(rule.paths):
        text = file_path.read_text(encoding=TEXT_ENCODING)
        for line_no, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                rel_path = file_path.relative_to(ROOT_DIR)
                detail = f"{rel_path}:{line_no}: {line.strip()}"
                matches.append(detail)
    return CheckResult(rule.name, not matches, matches)


def run_command(command: tuple[str, ...]) -> CheckResult:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    if "pytest" in command:
        env.setdefault("YUNXI_USE_FAKE_EMBEDDING", "1")
    completed = subprocess.run(
        command,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=env,
    )
    command_text = " ".join(command)
    details = []
    if completed.stdout.strip():
        details.append(completed.stdout.strip())
    if completed.stderr.strip():
        details.append(completed.stderr.strip())
    return CheckResult(command_text, completed.returncode == 0, details)


def run_red_line_checks() -> list[CheckResult]:
    return [scan_rule(rule) for rule in RED_LINE_RULES]


def run_clean_code_checks() -> list[CheckResult]:
    """运行洁净代码阻断检查（硬编码 URL、魔法整数）。"""
    return [
        check_hardcoded_urls_in_functions(APP_DIR),
        check_known_magic_integers(APP_DIR),
    ]


def run_tests() -> list[CheckResult]:
    return [run_command(command) for command in TEST_COMMANDS]


def run_contract_checks() -> list[CheckResult]:
    """运行业务合约静态检查。"""
    return [run_command(command) for command in CONTRACT_COMMANDS]


def print_results(title: str, results: list[CheckResult]) -> None:
    print(f"\n[{title}]")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name}")
        for detail in result.details:
            print(detail)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="项目质量门禁统一入口")
    parser.add_argument("--skip-tests", action="store_true", help="跳过测试脚本")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    red_line_results = run_red_line_checks()
    print_results("红线检查", red_line_results)

    clean_code_results = run_clean_code_checks()
    print_results("洁净代码检查", clean_code_results)

    contract_results = run_contract_checks()
    print_results("业务合约检查", contract_results)

    func_length_warnings = check_function_lengths(APP_DIR)
    if func_length_warnings:
        print(f"\n[函数行数警告（{len(func_length_warnings)} 处，暂不阻断）]")
        for warning in func_length_warnings:
            print(f"WARN {warning}")

    test_results: list[CheckResult] = []
    if not args.skip_tests:
        test_results = run_tests()
        print_results("测试验证", test_results)

    all_results = (
        red_line_results + clean_code_results + contract_results + test_results
    )
    failed_results = [result for result in all_results if not result.passed]
    if failed_results:
        print(f"\n质量门禁失败: {len(failed_results)} 项")
        return 1
    print("\n质量门禁通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
