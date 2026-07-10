"""生成 LangChain 外部证据交接汇总包。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import APP_VERSION  # noqa: E402
from app.service.agents.evaluation import write_json_report  # noqa: E402
from scripts import build_langchain_portfolio_evidence_packet as portfolio_packet  # noqa: E402
from scripts import build_rag_shadow_log_intake_packet as rag_packet  # noqa: E402
from scripts import build_real_conversation_replay_intake_packet as replay_packet  # noqa: E402

TRACE_ID = "20260709-langchain-ai-layer-production-enhancement"
DEFAULT_OUTPUT_PATH = (
    ROOT_DIR / "reports" / "harness" / "langchain-external-evidence-handoff.json"
)
DEFAULT_HANDOFF_EVIDENCE_ID = "E-LANGCHAIN-EXTERNAL-EVIDENCE-HANDOFF"


def build_external_evidence_handoff_packet(
    *,
    operator: str = "manual_reviewer",
    handoff_evidence_id: str = DEFAULT_HANDOFF_EVIDENCE_ID,
    real_replay_evidence_id: str = "E-P17B-REAL-REPLAY-INTAKE",
    rag_shadow_log_evidence_id: str = "E-P19C-RAG-SHADOW-LOG-INTAKE",
    portfolio: dict[str, object] | None = None,
) -> dict[str, object]:
    real_replay = replay_packet.build_real_replay_intake_packet(
        operator=operator,
        evidence_id=real_replay_evidence_id,
    )
    rag_shadow_log = rag_packet.build_rag_shadow_log_intake_packet(
        operator=operator,
        evidence_id=rag_shadow_log_evidence_id,
    )
    portfolio_report = portfolio
    if portfolio_report is None:
        portfolio_report = portfolio_packet.build_portfolio_evidence_packet()

    stage_readiness = dict_value(portfolio_report, "stage_readiness")
    assertions = build_assertions(
        operator=operator,
        handoff_evidence_id=handoff_evidence_id,
        real_replay=real_replay,
        rag_shadow_log=rag_shadow_log,
        portfolio_report=portfolio_report,
    )
    failed = sum(1 for passed in assertions.values() if not passed)
    return {
        "status": "passed" if failed == 0 else "failed",
        "generated_at": utc_now(),
        "trace_id": TRACE_ID,
        "app_version": APP_VERSION,
        "failed": failed,
        "operator": operator,
        "handoff_evidence_id": handoff_evidence_id,
        "external_evidence_complete": portfolio_report.get(
            "external_evidence_complete", False
        ),
        "portfolio_complete": portfolio_report.get("portfolio_complete", False),
        "assertions": assertions,
        "missing_actions": list(portfolio_report.get("missing_actions", [])),
        "required_external_inputs": build_required_external_inputs(stage_readiness),
        "handoff_packets": {
            "real_replay": summarize_real_replay_packet(real_replay),
            "rag_shadow_log": summarize_rag_shadow_log_packet(rag_shadow_log),
        },
        "handoff_sequence": build_handoff_sequence(
            real_replay=real_replay,
            rag_shadow_log=rag_shadow_log,
            portfolio_report=portfolio_report,
        ),
        "boundaries": build_boundaries(),
        "next_gate": (
            "python scripts\\build_langchain_portfolio_evidence_packet.py "
            "--require-complete --summary"
        ),
    }


def build_assertions(
    *,
    operator: str,
    handoff_evidence_id: str,
    real_replay: dict[str, object],
    rag_shadow_log: dict[str, object],
    portfolio_report: dict[str, object],
) -> dict[str, bool]:
    return {
        "operator.present": bool(operator.strip()),
        "handoff_evidence_id.present": bool(handoff_evidence_id.strip()),
        "real_replay_intake_packet.passed": real_replay.get("status") == "passed",
        "rag_shadow_log_intake_packet.passed": rag_shadow_log.get("status") == "passed",
        "portfolio_verified_evidence_ready": portfolio_report.get(
            "verified_evidence_ready"
        )
        is True,
        "external_missing_actions_visible": bool(
            portfolio_report.get("external_evidence_complete") is True
            or portfolio_report.get("missing_actions")
        ),
    }


def build_required_external_inputs(
    stage_readiness: dict[str, object],
) -> list[dict[str, object]]:
    external_inputs: list[dict[str, object]] = []
    for stage_name, stage in stage_readiness.items():
        stage_payload = dict_value_from_object(stage)
        if stage_payload.get("ready") is True:
            continue
        external_inputs.append(
            {
                "stage": stage_name,
                "ready": False,
                "action": stage_payload.get("action", ""),
                "human_input_required": True,
            }
        )
    return external_inputs


def summarize_real_replay_packet(report: dict[str, object]) -> dict[str, object]:
    return {
        "status": report.get("status", "missing"),
        "target_count": report.get("target_count", 0),
        "required_scenarios": report.get("required_scenarios", []),
        "handoff_template": report.get("handoff_template", {}),
        "commands": report.get("commands", []),
        "boundaries": report.get("boundaries", {}),
        "next_gate": report.get("next_gate", ""),
        "readiness": {
            "candidate_ready": False,
            "real_sample_ready": False,
            "reason": "external_redacted_real_replay_input_not_provided_by_handoff",
        },
    }


def summarize_rag_shadow_log_packet(report: dict[str, object]) -> dict[str, object]:
    return {
        "status": report.get("status", "missing"),
        "recommended_record_count": report.get("recommended_record_count", 0),
        "required_metadata_fields": report.get("required_metadata_fields", []),
        "required_record_fields": report.get("required_record_fields", []),
        "handoff_template": report.get("handoff_template", {}),
        "commands": report.get("commands", []),
        "boundaries": report.get("boundaries", {}),
        "readiness": report.get("readiness", {}),
    }


def build_handoff_sequence(
    *,
    real_replay: dict[str, object],
    rag_shadow_log: dict[str, object],
    portfolio_report: dict[str, object],
) -> list[dict[str, object]]:
    return [
        {
            "step": "collect_real_replay_input_outside_repo",
            "source": "real_replay",
            "commands": real_replay.get("commands", []),
        },
        {
            "step": "collect_rag_shadow_log_input_outside_repo",
            "source": "rag_shadow_log",
            "commands": rag_shadow_log.get("commands", []),
        },
        {
            "step": "refresh_portfolio_completion_gate",
            "source": "portfolio",
            "commands": [
                {
                    "step": "verify_complete_portfolio_gate",
                    "command": (
                        "python scripts\\build_langchain_portfolio_evidence_packet.py "
                        "--require-complete --summary"
                    ),
                    "human_input_required": False,
                }
            ],
            "missing_actions": portfolio_report.get("missing_actions", []),
        },
    ]


def build_boundaries() -> dict[str, bool]:
    return {
        "raw_customer_conversation_read": False,
        "raw_rag_shadow_log_read": False,
        "real_customer_data_committed": False,
        "business_database_read": False,
        "business_database_written": False,
        "external_llm_called": False,
        "production_service_changed": False,
        "readiness_changed": False,
        "missing_external_evidence_treated_as_complete": False,
    }


def dict_value(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def dict_value_from_object(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def utc_now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 LangChain 外部证据交接汇总包")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    parser.add_argument("--summary", action="store_true", help="只输出摘要")
    parser.add_argument(
        "--json-out", type=Path, default=DEFAULT_OUTPUT_PATH, help="交接汇总包路径"
    )
    parser.add_argument("--operator", default="manual_reviewer", help="交接审核人")
    parser.add_argument(
        "--handoff-evidence-id",
        default=DEFAULT_HANDOFF_EVIDENCE_ID,
        help="交接汇总证据 ID",
    )
    parser.add_argument(
        "--real-replay-evidence-id",
        default="E-P17B-REAL-REPLAY-INTAKE",
        help="真实 replay 接入证据 ID",
    )
    parser.add_argument(
        "--rag-shadow-log-evidence-id",
        default="E-P19C-RAG-SHADOW-LOG-INTAKE",
        help="真实 RAG shadow log 接入证据 ID",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_external_evidence_handoff_packet(
        operator=args.operator,
        handoff_evidence_id=args.handoff_evidence_id,
        real_replay_evidence_id=args.real_replay_evidence_id,
        rag_shadow_log_evidence_id=args.rag_shadow_log_evidence_id,
    )
    write_json_report(report, args.json_out)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.summary:
        print_summary(report)
    else:
        print_text_report(report)
    return 0 if report["status"] == "passed" else 1


def print_summary(report: dict[str, object]) -> None:
    print(
        "langchain_external_evidence_handoff "
        f"status={report['status']} failed={report['failed']} "
        f"external_evidence_complete="
        f"{str(report['external_evidence_complete']).lower()} "
        f"portfolio_complete={str(report['portfolio_complete']).lower()}"
    )


def print_text_report(report: dict[str, object]) -> None:
    print_summary(report)
    for action in report["missing_actions"]:
        print(f"NEXT {action}")


if __name__ == "__main__":
    raise SystemExit(main())
