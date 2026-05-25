"""项目质量门禁统一入口。"""

import argparse
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
    ScanRule("api 层禁止直接导入 repository", r"from app\.repository", (APP_DIR / "api",)),
    ScanRule("service 层禁止直连 aiosqlite", r"import aiosqlite|aiosqlite\.", (APP_DIR / "service",)),
    ScanRule("models 层禁止引用上层模块", r"from app\.(service|repository|api)", (APP_DIR / "models",)),
    ScanRule("禁止 SQL f-string 拼接", r"f\"(SELECT|INSERT|UPDATE|DELETE)", (APP_DIR,)),
    ScanRule("禁止静默吞异常", r"except.*:\s*pass", (APP_DIR,)),
    ScanRule("禁止硬编码密钥", r"api_key\s*=\s*[\"']sk-|secret\s*=\s*[\"']", (APP_DIR,)),
    ScanRule("app 内禁止裸 print", r"^\s+print\(", (APP_DIR,)),
)

TEST_COMMANDS: tuple[tuple[str, ...], ...] = (
    (sys.executable, "-m", "pytest", "-q", "--tb=short"),
)


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


def run_tests() -> list[CheckResult]:
    return [run_command(command) for command in TEST_COMMANDS]


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

    test_results: list[CheckResult] = []
    if not args.skip_tests:
        test_results = run_tests()
        print_results("测试验证", test_results)

    all_results = red_line_results + test_results
    failed_results = [result for result in all_results if not result.passed]
    if failed_results:
        print(f"\n质量门禁失败: {len(failed_results)} 项")
        return 1
    print("\n质量门禁通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
