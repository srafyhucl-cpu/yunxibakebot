"""RAG 真实检索日志 shadow 观测入口。"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import APP_VERSION  # noqa: E402
from app.service.agents.evaluation import write_json_report  # noqa: E402
from scripts import eval_retrieval  # noqa: E402
from scripts import report_retrieval_eval_matrix as eval_matrix  # noqa: E402
from scripts import report_retrieval_shadow_compare as shadow_compare  # noqa: E402

DEFAULT_DB_PATH = ROOT_DIR / "data" / "bot.db"
DEFAULT_OUTPUT_PATH = (
    ROOT_DIR / "reports" / "retrieval-shadow" / "rag-shadow-log-observability.json"
)
DEFAULT_K = 5
DEFAULT_RERANK_CANDIDATE_MULTIPLIER = eval_retrieval.DEFAULT_RERANK_CANDIDATE_MULTIPLIER
REQUIRED_RECORD_FIELDS = (
    "id",
    "query",
    "baseline_top_keys",
)
REDACTION_REQUIREMENTS = (
    "input metadata 必须声明 contains_sensitive_data=false",
    "query 必须是已脱敏文本，不得包含手机号、地址、open_id、完整订单号或客户姓名",
    "报告默认只输出 query_hash，不输出 query 原文",
    "原始生产日志只能保存在仓库外，不得提交到 git",
)


def build_rag_shadow_log_observability_report(
    *,
    input_path: Path | None = None,
    db_path: Path = DEFAULT_DB_PATH,
    k: int = DEFAULT_K,
    require_input: bool = False,
    include_queries: bool = False,
) -> dict[str, object]:
    if input_path is None:
        return build_missing_input_report(
            require_input=require_input, db_path=db_path, k=k
        )
    payload = load_input_payload(input_path)
    records = list(payload.get("records", []))
    input_assertions = build_input_assertions(payload=payload, records=records)
    if any(not passed for passed in input_assertions.values()):
        return build_invalid_input_report(
            input_path=input_path,
            db_path=db_path,
            k=k,
            input_assertions=input_assertions,
        )
    shadow_records = build_shadow_records(
        records=records,
        db_path=db_path,
        k=k,
    )
    summary = summarize_shadow_records(shadow_records)
    assertions = {
        **input_assertions,
        "shadow_log.records_present": bool(records),
        "shadow_log.candidates_present": all(
            bool(record["candidates"]) for record in shadow_records
        ),
    }
    failed = sum(1 for passed in assertions.values() if not passed)
    report: dict[str, object] = {
        "status": "passed" if failed == 0 else "failed",
        "generated_at": utc_now(),
        "app_version": APP_VERSION,
        "failed": failed,
        "shadow_log_ready": failed == 0,
        "metadata": {
            "input": str(input_path),
            "db": str(db_path),
            "k": k,
            "record_count": len(records),
            "source_type": payload.get("metadata", {}).get("source_type", ""),
        },
        "summary": summary,
        "records": sanitize_shadow_records(
            shadow_records, include_queries=include_queries
        ),
        "assertions": assertions,
        "missing_actions": build_missing_actions(assertions),
        "boundaries": {
            "production_hot_path_changed": False,
            "rag_retrieval_mode_changed": False,
            "external_llm_called": False,
            "business_database_written": False,
            "contains_user_query_text": include_queries,
            "raw_production_log_committed": False,
        },
    }
    return report


def build_missing_input_report(
    *,
    require_input: bool,
    db_path: Path,
    k: int,
) -> dict[str, object]:
    return {
        "status": "failed" if require_input else "passed",
        "generated_at": utc_now(),
        "app_version": APP_VERSION,
        "failed": 1 if require_input else 0,
        "shadow_log_ready": False,
        "metadata": {
            "input": "",
            "db": str(db_path),
            "k": k,
            "record_count": 0,
            "source_type": "",
        },
        "required_record_fields": list(REQUIRED_RECORD_FIELDS),
        "redaction_requirements": list(REDACTION_REQUIREMENTS),
        "commands": {
            "build_input": (
                "导出仓库外生产 knowledge_retrieval_logs，人工脱敏 query 后写入 "
                "reports\\retrieval-shadow\\rag-shadow-log-input.json"
            ),
            "check_input": (
                "python scripts\\report_rag_shadow_log_observability.py "
                "--input reports\\retrieval-shadow\\rag-shadow-log-input.json --summary"
            ),
            "strict_gate": (
                "python scripts\\report_rag_shadow_log_observability.py "
                "--input reports\\retrieval-shadow\\rag-shadow-log-input.json "
                "--require-input --summary"
            ),
        },
        "assertions": {
            "shadow_log.input_present": False,
            "shadow_log.input_required": not require_input,
        },
        "missing_actions": ["provide_redacted_rag_shadow_log_input"],
        "boundaries": {
            "production_hot_path_changed": False,
            "rag_retrieval_mode_changed": False,
            "external_llm_called": False,
            "business_database_written": False,
            "contains_user_query_text": False,
            "raw_production_log_committed": False,
        },
    }


def load_input_payload(input_path: Path) -> dict[str, Any]:
    return json.loads(input_path.read_text(encoding="utf-8-sig"))


def build_input_assertions(
    *,
    payload: dict[str, Any],
    records: list[Any],
) -> dict[str, bool]:
    metadata = payload.get("metadata", {})
    return {
        "metadata.contains_sensitive_data_false": metadata.get(
            "contains_sensitive_data"
        )
        is False,
        "metadata.source_type.present": bool(str(metadata.get("source_type", ""))),
        "records.present": bool(records),
        "records.required_fields_present": all(
            isinstance(record, dict)
            and all(
                field in record and record[field] for field in REQUIRED_RECORD_FIELDS
            )
            for record in records
        ),
        "records.baseline_top_keys_list": all(
            isinstance(record.get("baseline_top_keys"), list) for record in records
        )
        if records
        else False,
    }


def build_invalid_input_report(
    *,
    input_path: Path,
    db_path: Path,
    k: int,
    input_assertions: dict[str, bool],
) -> dict[str, object]:
    failed = sum(1 for passed in input_assertions.values() if not passed)
    return {
        "status": "failed",
        "generated_at": utc_now(),
        "app_version": APP_VERSION,
        "failed": failed,
        "shadow_log_ready": False,
        "metadata": {
            "input": str(input_path),
            "db": str(db_path),
            "k": k,
            "record_count": 0,
            "source_type": "",
        },
        "assertions": input_assertions,
        "missing_actions": build_missing_actions(input_assertions),
        "boundaries": {
            "production_hot_path_changed": False,
            "rag_retrieval_mode_changed": False,
            "external_llm_called": False,
            "business_database_written": False,
            "contains_user_query_text": False,
            "raw_production_log_committed": False,
        },
    }


def build_shadow_records(
    *,
    records: list[Any],
    db_path: Path,
    k: int,
) -> list[dict[str, object]]:
    corpus = eval_retrieval.load_corpus(db_path)
    scenarios = (
        shadow_compare.DEFAULT_BASELINE,
        *shadow_compare.DEFAULT_CANDIDATES,
    )
    indexes = eval_matrix.build_search_indexes(scenarios, corpus)
    searchers = {
        scenario.name: eval_matrix.build_searcher(
            scenario,
            indexes,
            corpus,
            rerank_candidate_multiplier=DEFAULT_RERANK_CANDIDATE_MULTIPLIER,
        )
        for scenario in scenarios
    }
    return [
        build_shadow_record(record, searchers=searchers, k=k)
        for record in records
        if isinstance(record, dict)
    ]


def build_shadow_record(
    record: dict[str, Any],
    *,
    searchers: dict[str, Any],
    k: int,
) -> dict[str, object]:
    query = str(record["query"])
    baseline_top_keys = [str(key) for key in record.get("baseline_top_keys", [])]
    candidates = []
    for name, searcher in searchers.items():
        top_keys = [key for key, _score in searcher.search(query, limit=k)]
        if name == shadow_compare.DEFAULT_BASELINE.name:
            continue
        candidates.append(
            {
                "name": name,
                "top_keys": top_keys,
                "changed": top_keys != baseline_top_keys,
                "overlap_count": len(set(top_keys) & set(baseline_top_keys)),
            }
        )
    return {
        "id": str(record["id"]),
        "group": str(record.get("group", "ungrouped") or "ungrouped"),
        "query": query,
        "query_hash": hash_query(query),
        "baseline": {
            "name": shadow_compare.DEFAULT_BASELINE.name,
            "top_keys": baseline_top_keys,
        },
        "candidates": candidates,
    }


def sanitize_shadow_records(
    records: list[dict[str, object]],
    *,
    include_queries: bool,
) -> list[dict[str, object]]:
    sanitized = []
    for record in records:
        item = {key: value for key, value in record.items() if key != "query"}
        if include_queries:
            item["query"] = record["query"]
        sanitized.append(item)
    return sanitized


def summarize_shadow_records(records: list[dict[str, object]]) -> dict[str, object]:
    changed_by_candidate: dict[str, int] = {}
    changed_by_group: dict[str, int] = {}
    for record in records:
        group = str(record["group"])
        if any(candidate["changed"] for candidate in record["candidates"]):
            changed_by_group[group] = changed_by_group.get(group, 0) + 1
        for candidate in record["candidates"]:
            if candidate["changed"]:
                name = str(candidate["name"])
                changed_by_candidate[name] = changed_by_candidate.get(name, 0) + 1
    return {
        "total_records": len(records),
        "changed_by_candidate": changed_by_candidate,
        "changed_by_group": changed_by_group,
    }


def build_missing_actions(assertions: dict[str, bool]) -> list[str]:
    actions = []
    if not assertions.get("metadata.contains_sensitive_data_false", True):
        actions.append("mark_shadow_log_input_as_desensitized")
    if not assertions.get("records.present", True):
        actions.append("provide_redacted_rag_shadow_log_input")
    if not assertions.get("records.required_fields_present", True):
        actions.append("fix_shadow_log_input_required_fields")
    if not assertions.get("records.baseline_top_keys_list", True):
        actions.append("fix_shadow_log_input_baseline_top_keys")
    if not assertions.get("shadow_log.candidates_present", True):
        actions.append("rerun_shadow_candidates_for_log_input")
    return actions


def hash_query(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build RAG shadow log observability")
    parser.add_argument("--input", type=Path, help="脱敏 RAG shadow log input JSON")
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite 语料库"
    )
    parser.add_argument("--k", type=int, default=DEFAULT_K, help="Top-K 截断")
    parser.add_argument(
        "--require-input",
        action="store_true",
        help="要求提供真实脱敏 shadow log input",
    )
    parser.add_argument(
        "--include-queries",
        action="store_true",
        help="显式输出脱敏 query 文本；默认只输出 query_hash",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="写入 RAG shadow log 观测 JSON 路径",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    parser.add_argument("--summary", action="store_true", help="只输出摘要")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if not args.db.exists():
        print(f"[ERROR] 语料库不存在: {args.db}", file=sys.stderr)
        return 1
    report = build_rag_shadow_log_observability_report(
        input_path=args.input,
        db_path=args.db,
        k=args.k,
        require_input=args.require_input,
        include_queries=args.include_queries,
    )
    if args.json_out is not None:
        write_json_report(report, args.json_out)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.summary:
        print(
            "rag_shadow_log_observability "
            f"status={report['status']} failed={report['failed']} "
            f"shadow_log_ready={str(report['shadow_log_ready']).lower()}"
        )
    else:
        print_text_report(report)
    return 0 if report["status"] == "passed" else 1


def print_text_report(report: dict[str, object]) -> None:
    print("rag_shadow_log_observability")
    print(
        f"status={report['status']} failed={report['failed']} "
        f"shadow_log_ready={str(report['shadow_log_ready']).lower()}"
    )
    for action in report["missing_actions"]:
        print(f"NEXT {action}")


def utc_now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


if __name__ == "__main__":
    raise SystemExit(main())
