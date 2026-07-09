"""LangChain AI 应用层发布门禁。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_AGENT_EVAL_PATH = ROOT_DIR / "reports" / "agent-eval" / "latest.json"
DEFAULT_REPLY_PROBE_PATH = (
    ROOT_DIR / "reports" / "agent-eval" / "customer-reply-replay-probe-latest.json"
)
DEFAULT_REPLY_EVAL_PATH = (
    ROOT_DIR / "reports" / "agent-eval" / "latest-with-reply-replay.json"
)
DEFAULT_RAG_MATRIX_PATH = ROOT_DIR / "reports" / "rag-eval" / "latest-matrix.json"


@dataclass(frozen=True)
class GateStep:
    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class GateStepResult:
    name: str
    command: tuple[str, ...]
    returncode: int
    stdout: str | None
    stderr: str | None

    @property
    def passed(self) -> bool:
        return self.returncode == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "command": list(self.command),
            "passed": self.passed,
            "returncode": self.returncode,
            "stdout": (self.stdout or "").strip(),
            "stderr": (self.stderr or "").strip(),
        }


def build_gate_steps(
    *,
    include_rag_matrix: bool = False,
    agent_eval_path: Path = DEFAULT_AGENT_EVAL_PATH,
    reply_probe_path: Path = DEFAULT_REPLY_PROBE_PATH,
    reply_eval_path: Path = DEFAULT_REPLY_EVAL_PATH,
    rag_matrix_path: Path = DEFAULT_RAG_MATRIX_PATH,
) -> tuple[GateStep, ...]:
    steps = [
        GateStep(
            name="agent_eval_default",
            command=(
                sys.executable,
                "scripts/report_agent_eval.py",
                "--latest",
                "--json-out",
                str(agent_eval_path),
                "--summary",
            ),
        ),
        GateStep(
            name="customer_reply_replay_probe",
            command=(
                sys.executable,
                "scripts/probe_customer_reply_replay.py",
                "--output",
                str(reply_probe_path),
            ),
        ),
        GateStep(
            name="agent_eval_with_reply_replay",
            command=(
                sys.executable,
                "scripts/report_agent_eval.py",
                "--latest",
                "--include-reply-replay",
                "--reply-replay-json",
                str(reply_probe_path),
                "--json-out",
                str(reply_eval_path),
                "--summary",
            ),
        ),
    ]
    if include_rag_matrix:
        steps.append(
            GateStep(
                name="rag_eval_matrix",
                command=(
                    sys.executable,
                    "scripts/report_retrieval_eval_matrix.py",
                    "--db",
                    "data/bot.db",
                    "--fixture",
                    "tests/fixtures/customer_rag_golden_cases.json",
                    "--k",
                    "5",
                    "--json-out",
                    str(rag_matrix_path),
                ),
            )
        )
    return tuple(steps)


def run_gate_steps(steps: tuple[GateStep, ...]) -> tuple[GateStepResult, ...]:
    results: list[GateStepResult] = []
    for step in steps:
        completed = subprocess.run(
            step.command,
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        result = GateStepResult(
            name=step.name,
            command=step.command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        results.append(result)
        if not result.passed:
            break
    return tuple(results)


def build_gate_report(
    results: tuple[GateStepResult, ...],
    *,
    include_rag_matrix: bool,
) -> dict[str, object]:
    failed = sum(1 for result in results if not result.passed)
    return {
        "status": "passed" if failed == 0 else "failed",
        "generated_at": _utc_now(),
        "include_rag_matrix": include_rag_matrix,
        "total": len(results),
        "failed": failed,
        "steps": [result.to_dict() for result in results],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LangChain AI layer release gate")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    parser.add_argument("--summary", action="store_true", help="只输出摘要")
    parser.add_argument("--json-out", type=Path, help="写入 JSON 报告路径")
    parser.add_argument(
        "--include-rag-matrix",
        action="store_true",
        help="额外运行 RAG 检索矩阵，耗时较长",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    ensure_output_directories(include_rag_matrix=args.include_rag_matrix)
    steps = build_gate_steps(include_rag_matrix=args.include_rag_matrix)
    results = run_gate_steps(steps)
    report = build_gate_report(results, include_rag_matrix=args.include_rag_matrix)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.summary:
        print(
            "langchain_ai_layer_release_gate "
            f"status={report['status']} total={report['total']} failed={report['failed']}"
        )
    else:
        print_text_report(report)
    return 0 if report["status"] == "passed" else 1


def ensure_output_directories(*, include_rag_matrix: bool) -> None:
    DEFAULT_AGENT_EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPLY_PROBE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPLY_EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if include_rag_matrix:
        DEFAULT_RAG_MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)


def print_text_report(report: dict[str, object]) -> None:
    print("langchain_ai_layer_release_gate")
    print(
        f"status={report['status']} total={report['total']} failed={report['failed']}"
    )
    for step in report["steps"]:
        mark = "PASS" if step["passed"] else "FAIL"
        print(f"{mark} {step['name']}")


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


if __name__ == "__main__":
    raise SystemExit(main())
