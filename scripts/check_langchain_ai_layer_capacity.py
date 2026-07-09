"""LangChain AI 应用层容量门禁。"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import APP_VERSION  # noqa: E402
from app.service.agents.evaluation import write_json_report  # noqa: E402
from app.service.agents.trace_report import parse_trace_runs  # noqa: E402
from scripts import probe_agent_traces  # noqa: E402
from scripts.check_langsmith_production_rollout import (  # noqa: E402
    MAX_DEFAULT_SAMPLE_RATE,
    build_langsmith_production_rollout_report,
)
from scripts.report_langchain_observability_evidence import (  # noqa: E402
    COLD_IMPORT_TARGETS,
    build_cold_import_summary,
)

DEFAULT_OUTPUT_PATH = (
    ROOT_DIR / "reports" / "agent-traces" / "langchain-ai-layer-capacity.json"
)
DEFAULT_TRACE_OUTPUT_PATH = (
    ROOT_DIR / "reports" / "agent-traces" / "langchain-capacity-trace-probe.json"
)
DEFAULT_MAX_TRACE_PROBE_LATENCY_MS = 5000
DEFAULT_MAX_TRACE_PAYLOAD_BYTES = 200_000
DEFAULT_MAX_EVENTS_PER_RUN = 20


def build_capacity_report(
    *,
    trace_input_path: Path | None = None,
    run_trace_probe: bool = True,
    trace_output_path: Path = DEFAULT_TRACE_OUTPUT_PATH,
    max_trace_probe_latency_ms: int = DEFAULT_MAX_TRACE_PROBE_LATENCY_MS,
    max_trace_payload_bytes: int = DEFAULT_MAX_TRACE_PAYLOAD_BYTES,
    max_events_per_run: int = DEFAULT_MAX_EVENTS_PER_RUN,
) -> dict[str, object]:
    trace_probe = build_trace_probe_metrics(
        trace_input_path=trace_input_path,
        run_trace_probe=run_trace_probe,
        trace_output_path=trace_output_path,
    )
    cold_imports = [build_cold_import_summary(target) for target in COLD_IMPORT_TARGETS]
    rollout = build_langsmith_production_rollout_report()
    assertions = build_assertions(
        trace_probe=trace_probe,
        cold_imports=cold_imports,
        rollout=rollout,
        max_trace_probe_latency_ms=max_trace_probe_latency_ms,
        max_trace_payload_bytes=max_trace_payload_bytes,
        max_events_per_run=max_events_per_run,
    )
    failed = sum(1 for passed in assertions.values() if not passed)
    return {
        "status": "passed" if failed == 0 else "failed",
        "generated_at": utc_now(),
        "app_version": APP_VERSION,
        "failed": failed,
        "thresholds": {
            "max_trace_probe_latency_ms": max_trace_probe_latency_ms,
            "max_trace_payload_bytes": max_trace_payload_bytes,
            "max_events_per_run": max_events_per_run,
            "max_langsmith_sample_rate": MAX_DEFAULT_SAMPLE_RATE,
        },
        "trace_probe": trace_probe,
        "cold_imports": cold_imports,
        "langsmith_rollout": {
            "status": rollout["status"],
            "enabled": rollout["rollout"]["enabled"],
            "sample_rate": rollout["rollout"]["sample_rate"],
            "max_default_sample_rate": rollout["rollout"]["max_default_sample_rate"],
        },
        "assertions": assertions,
        "missing_actions": build_missing_actions(assertions),
        "boundaries": {
            "production_load_test": False,
            "production_hot_path_changed": False,
            "external_llm_called": False,
            "langsmith_external_export": False,
            "business_database_read": False,
            "contains_sensitive_data": False,
        },
    }


def build_trace_probe_metrics(
    *,
    trace_input_path: Path | None,
    run_trace_probe: bool,
    trace_output_path: Path,
) -> dict[str, object]:
    started_at = perf_counter()
    trace_path = resolve_trace_path(
        trace_input_path=trace_input_path,
        run_trace_probe=run_trace_probe,
        trace_output_path=trace_output_path,
    )
    latency_ms = round((perf_counter() - started_at) * 1000, 2)
    if trace_path is None or not trace_path.exists():
        return {
            "status": "no_traces",
            "path": "" if trace_path is None else str(trace_path),
            "latency_ms": latency_ms,
            "payload_bytes": 0,
            "total_runs": 0,
            "total_events": 0,
            "max_events_per_run": 0,
        }
    payload_text = trace_path.read_text(encoding="utf-8-sig")
    runs = parse_trace_runs(json.loads(payload_text))
    event_counts = [len(run.trace_events) for run in runs]
    return {
        "status": "ok" if runs else "no_traces",
        "path": str(trace_path),
        "latency_ms": latency_ms,
        "payload_bytes": len(payload_text.encode("utf-8")),
        "total_runs": len(runs),
        "total_events": sum(event_counts),
        "max_events_per_run": max(event_counts, default=0),
    }


def resolve_trace_path(
    *,
    trace_input_path: Path | None,
    run_trace_probe: bool,
    trace_output_path: Path,
) -> Path | None:
    if trace_input_path is not None:
        return trace_input_path
    if not run_trace_probe:
        return None
    return asyncio.run(probe_agent_traces.main_async(trace_output_path))


def build_assertions(
    *,
    trace_probe: dict[str, object],
    cold_imports: list[dict[str, object]],
    rollout: dict[str, object],
    max_trace_probe_latency_ms: int,
    max_trace_payload_bytes: int,
    max_events_per_run: int,
) -> dict[str, bool]:
    rollout_data = rollout["rollout"]
    return {
        "trace_probe.ok": trace_probe["status"] == "ok",
        "trace_probe.latency_within_limit": float(trace_probe["latency_ms"])
        <= max_trace_probe_latency_ms,
        "trace_probe.payload_within_limit": int(trace_probe["payload_bytes"])
        <= max_trace_payload_bytes,
        "trace_probe.events_within_limit": int(trace_probe["max_events_per_run"])
        <= max_events_per_run,
        "cold_imports.passed": all(
            item.get("status") == "passed" for item in cold_imports
        ),
        "langsmith_rollout.closed_by_default": rollout_data["enabled"] is False
        and rollout_data["sample_rate"] == 0.0,
        "langsmith_rollout.sample_rate_within_limit": float(rollout_data["sample_rate"])
        <= MAX_DEFAULT_SAMPLE_RATE,
        "langsmith_rollout.passed": rollout["status"] == "passed",
    }


def build_missing_actions(assertions: dict[str, bool]) -> list[str]:
    actions = []
    if not assertions["trace_probe.ok"]:
        actions.append("fix_agent_trace_probe_before_capacity_gate")
    if not assertions["trace_probe.latency_within_limit"]:
        actions.append("reduce_langchain_graph_probe_latency")
    if not assertions["trace_probe.payload_within_limit"]:
        actions.append("reduce_trace_payload_size_or_redaction_scope")
    if not assertions["trace_probe.events_within_limit"]:
        actions.append("inspect_agent_graph_event_count_growth")
    if not assertions["cold_imports.passed"]:
        actions.append("fix_heavy_import_before_production_rollout")
    if not assertions["langsmith_rollout.closed_by_default"]:
        actions.append("keep_langsmith_external_export_disabled_by_default")
    if not assertions["langsmith_rollout.sample_rate_within_limit"]:
        actions.append("lower_langsmith_sample_rate_to_safe_default")
    return actions


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check LangChain AI layer capacity and cost guardrails"
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    parser.add_argument("--summary", action="store_true", help="只输出摘要")
    parser.add_argument(
        "--json-out",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="写入容量门禁 JSON 路径",
    )
    parser.add_argument("--trace-input", type=Path, help="读取指定 trace JSON")
    parser.add_argument(
        "--trace-output",
        type=Path,
        default=DEFAULT_TRACE_OUTPUT_PATH,
        help="运行 trace probe 时写入的 trace JSON 路径",
    )
    parser.add_argument(
        "--skip-trace-probe",
        action="store_true",
        help="不运行 trace probe，只检查冷导入和 LangSmith 默认状态",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_capacity_report(
        trace_input_path=args.trace_input,
        run_trace_probe=not args.skip_trace_probe,
        trace_output_path=args.trace_output,
    )
    if args.json_out is not None:
        write_json_report(report, args.json_out)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.summary:
        print(
            "langchain_ai_layer_capacity "
            f"status={report['status']} failed={report['failed']} "
            f"trace_latency_ms={report['trace_probe']['latency_ms']} "
            f"payload_bytes={report['trace_probe']['payload_bytes']}"
        )
    else:
        print_text_report(report)
    return 0 if report["status"] == "passed" else 1


def print_text_report(report: dict[str, object]) -> None:
    trace_probe = report["trace_probe"]
    print("langchain_ai_layer_capacity")
    print(
        f"status={report['status']} failed={report['failed']} "
        f"trace_latency_ms={trace_probe['latency_ms']} "
        f"payload_bytes={trace_probe['payload_bytes']}"
    )
    for action in report["missing_actions"]:
        print(f"NEXT {action}")


def utc_now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


if __name__ == "__main__":
    raise SystemExit(main())
