"""检查 Harness evidence index 结构是否可机器读取。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_EVIDENCE_INDEX = (
    ROOT_DIR / "docs" / "harness-engineering" / "core" / "evidence-index.md"
)
ENTRY_HEADING_RE = re.compile(r"^##\s+(E-\d{8}-\d{3})：(.+)$")
SECOND_LEVEL_HEADING_RE = re.compile(r"^##\s+")
FIELD_RE = re.compile(r"^-\s+([a-z_]+):\s*(.*)$")
REQUIRED_FIELDS = (
    "trace_id",
    "generated_at",
    "evidence_type",
    "file",
    "command",
    "result",
    "related_logbook",
    "contains_sensitive_data",
    "retention_note",
    "summary",
)
ALLOWED_RESULTS = frozenset({"pass", "fail", "partial", "partial-pass"})
ALLOWED_SENSITIVE_FLAGS = frozenset({"yes", "no"})
PREFLIGHT_CONTRACT_EVIDENCE_ID = "E-20260706-001"
PREFLIGHT_CONTRACT_REQUIRED_SNIPPETS = (
    "check_preflight_business_contracts.py",
    "preflight-contract-check-20260706-232901.json",
    "business_contracts.static_checks",
)


@dataclass(frozen=True)
class EvidenceEntry:
    entry_id: str
    title: str
    fields: dict[str, str]


@dataclass(frozen=True)
class EvidenceCheckResult:
    passed: bool
    entries: tuple[EvidenceEntry, ...]
    issues: tuple[str, ...]


def parse_entries(content: str) -> tuple[EvidenceEntry, ...]:
    entries: list[EvidenceEntry] = []
    current_id = ""
    current_title = ""
    current_fields: dict[str, str] = {}
    for raw_line in content.splitlines():
        heading_match = ENTRY_HEADING_RE.match(raw_line)
        if heading_match:
            if current_id:
                entries.append(
                    EvidenceEntry(current_id, current_title, dict(current_fields))
                )
            current_id = heading_match.group(1)
            current_title = heading_match.group(2).strip()
            current_fields = {}
            continue
        if current_id and SECOND_LEVEL_HEADING_RE.match(raw_line):
            entries.append(
                EvidenceEntry(current_id, current_title, dict(current_fields))
            )
            current_id = ""
            current_title = ""
            current_fields = {}
            continue
        if not current_id:
            continue
        field_match = FIELD_RE.match(raw_line)
        if field_match:
            current_fields[field_match.group(1)] = field_match.group(2).strip()
    if current_id:
        entries.append(EvidenceEntry(current_id, current_title, dict(current_fields)))
    return tuple(entries)


def validate_entry(entry: EvidenceEntry) -> list[str]:
    issues: list[str] = []
    for field_name in REQUIRED_FIELDS:
        value = entry.fields.get(field_name, "")
        if not value:
            issues.append(f"{entry.entry_id}: missing field `{field_name}`")
    result = entry.fields.get("result")
    if result and result not in ALLOWED_RESULTS:
        issues.append(f"{entry.entry_id}: invalid result `{result}`")
    sensitive_flag = entry.fields.get("contains_sensitive_data")
    if sensitive_flag and sensitive_flag not in ALLOWED_SENSITIVE_FLAGS:
        issues.append(
            f"{entry.entry_id}: invalid contains_sensitive_data `{sensitive_flag}`"
        )
    return issues


def validate_preflight_contract_entry(entry: EvidenceEntry) -> list[str]:
    combined_text = "\n".join(entry.fields.values())
    issues: list[str] = []
    if entry.fields.get("result") != "pass":
        issues.append(f"{entry.entry_id}: preflight contract evidence result must pass")
    for snippet in PREFLIGHT_CONTRACT_REQUIRED_SNIPPETS:
        if snippet not in combined_text:
            issues.append(
                f"{entry.entry_id}: missing preflight contract reference `{snippet}`"
            )
    return issues


def validate_entries(entries: tuple[EvidenceEntry, ...]) -> list[str]:
    issues: list[str] = []
    seen_ids: set[str] = set()
    for entry in entries:
        if entry.entry_id in seen_ids:
            issues.append(f"{entry.entry_id}: duplicate evidence id")
        seen_ids.add(entry.entry_id)
        issues.extend(validate_entry(entry))
        if entry.entry_id == PREFLIGHT_CONTRACT_EVIDENCE_ID:
            issues.extend(validate_preflight_contract_entry(entry))
    if not any(entry.entry_id == PREFLIGHT_CONTRACT_EVIDENCE_ID for entry in entries):
        issues.append(f"missing evidence entry `{PREFLIGHT_CONTRACT_EVIDENCE_ID}`")
    return issues


def check_evidence_index(path: Path = DEFAULT_EVIDENCE_INDEX) -> EvidenceCheckResult:
    if not path.exists():
        return EvidenceCheckResult(False, (), (f"evidence index not found: {path}",))
    content = path.read_text(encoding="utf-8-sig")
    entries = parse_entries(content)
    if not entries:
        return EvidenceCheckResult(False, (), ("evidence index has no entries",))
    issues = validate_entries(entries)
    return EvidenceCheckResult(not issues, entries, tuple(issues))


def build_json_report(result: EvidenceCheckResult, path: Path) -> dict[str, object]:
    return {
        "status": "passed" if result.passed else "failed",
        "path": str(path),
        "total": len(result.entries),
        "failed": len(result.issues),
        "issues": list(result.issues),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="检查 Harness evidence index 结构")
    parser.add_argument("--path", default=str(DEFAULT_EVIDENCE_INDEX), help="索引路径")
    parser.add_argument("--summary", action="store_true", help="只输出摘要")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    index_path = Path(args.path)
    result = check_evidence_index(index_path)
    report = build_json_report(result, index_path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if result.passed else 1
    if args.summary:
        print(
            "evidence_index "
            f"status={report['status']} total={report['total']} failed={report['failed']}"
        )
        return 0 if result.passed else 1
    if result.passed:
        print(f"[evidence-index] ok entries={len(result.entries)}")
        return 0
    print("[evidence-index] failed")
    for issue in result.issues:
        print(f"  - {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
