"""双机器人 Agent Eval 聚合报告。"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import APP_VERSION  # noqa: E402
from app.service.agents.evaluation import combine_agent_eval_results  # noqa: E402
from scripts.eval_customer_agent import build_customer_eval_result  # noqa: E402
from scripts.eval_employee_agent import build_employee_eval_result  # noqa: E402


async def build_agent_eval_report() -> dict[str, object]:
    customer_result = build_customer_eval_result()
    employee_result = await build_employee_eval_result()
    return combine_agent_eval_results(
        (customer_result, employee_result),
        metadata={
            "generated_at": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            "project_root": str(ROOT_DIR),
            "app_version": APP_VERSION,
            "llm": "disabled",
        },
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report combined agent eval")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    parser.add_argument("--summary", action="store_true", help="只输出摘要")
    parser.add_argument(
        "--latest",
        action="store_true",
        help="输出当前最新 eval 文本报告；与默认行为一致，便于计划命令稳定",
    )
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    payload = await build_agent_eval_report()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.summary:
        print(
            "agent_eval "
            f"status={payload['status']} total={payload['total']} "
            f"failed={payload['failed']} pass_rate={payload['pass_rate']}"
        )
    else:
        print_text_report(payload)
    return 0 if payload["status"] == "passed" else 1


def print_text_report(payload: dict[str, object]) -> None:
    print("agent_eval")
    print(
        f"status={payload['status']} total={payload['total']} "
        f"failed={payload['failed']} pass_rate={payload['pass_rate']}"
    )
    for agent in payload["agents"]:
        print(
            "{agent}: status={status} total={total} failed={failed} "
            "pass_rate={pass_rate}".format(**agent)
        )


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
