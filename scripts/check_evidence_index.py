"""检查 Harness evidence index 结构是否可机器读取。"""

from __future__ import annotations

import argparse
import hashlib
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
FIELD_RE = re.compile(r"^-\s+([a-z_][a-z0-9_]*):\s*(.*)$")
FILE_REFERENCE_RE = re.compile(r"`([^`]+)`")
LEGACY_FILE_ALIASES = {
    "D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_reply_guard.py": "D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_mixed_reply.py",
    "D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_list_guard.py": "D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_order_lookup.py",
    "D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_llm_plan.py": "D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_planner.py",
    "D:/Project/YunxiBakeBot/tests/service/test_miniapp_order.py": "D:/Project/YunxiBakeBot/tests/service/test_order.py",
    "D:/Project/YunxiBakeBot/tests/service/test_miniapp_chat.py": "D:/Project/YunxiBakeBot/tests/api/test_miniapp_chat_api.py",
    "D:/Project/YunxiBakeBot/tests/service/llm": "D:/Project/YunxiBakeBot/tests/service/test_llm_provider.py",
    "D:/Project/YunxiBakeBot/tests/service/agents": "D:/Project/YunxiBakeBot/tests/service/agents/test_llm_factory.py",
}
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
ALLOWED_EVIDENCE_STATUSES = frozenset({"active", "retired"})
ALLOWED_STORAGE_SCOPES = frozenset({"repository", "local", "external"})
REFERENCE_PREFIXES = ("repo:", "local:", "production:", "external:")
PREFLIGHT_CONTRACT_EVIDENCE_ID = "E-20260706-001"
PREFLIGHT_CONTRACT_REQUIRED_SNIPPETS = (
    "check_preflight_business_contracts.py",
    "preflight-contract-check-20260706-232901.json",
    "business_contracts.static_checks",
)
# 本地留存工件：gitignore 的本地报告/证据输出。缺失（如干净 clone / CI）时不阻断，
# 仅登记名称、哈希与保留策略；仓内必需证据（其余路径）缺失仍阻断。
LOCAL_ARTIFACT_PREFIXES = ("reports/harness",)


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
    file_integrity: tuple[dict[str, str | bool], ...] = ()


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


def _parse_sha256_map(text: str) -> dict[str, str]:
    """解析 sha256 映射格式 `file=sha256；file=sha256`。"""
    result: dict[str, str] = {}
    for part in text.split("；"):
        part = part.strip()
        if "=" in part:
            key, value = part.split("=", 1)
            key = key.strip().replace("\\", "/")
            value = value.strip()
            if re.fullmatch(r"[0-9a-f]{64}", value):
                result[key] = value
    return result


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
    evidence_status = entry.fields.get("evidence_status", "active")
    if evidence_status not in ALLOWED_EVIDENCE_STATUSES:
        issues.append(f"{entry.entry_id}: invalid evidence_status {evidence_status}")
    storage_scope = entry.fields.get("storage_scope")
    if storage_scope and storage_scope not in ALLOWED_STORAGE_SCOPES:
        issues.append(f"{entry.entry_id}: invalid storage_scope `{storage_scope}`")
    sha256 = entry.fields.get("sha256")
    is_pure_hex = bool(re.fullmatch(r"[0-9a-f]{64}", sha256 or ""))
    is_sha_map = bool(_parse_sha256_map(sha256 or ""))
    if sha256 and not is_pure_hex and not is_sha_map:
        issues.append(f"{entry.entry_id}: invalid sha256 `{sha256[:16] or sha256}`")
    if storage_scope:
        for reference in FILE_REFERENCE_RE.findall(entry.fields.get("file", "")):
            norm = reference.strip().replace("\\", "/")
            if norm.startswith(("http://", "https://")):
                continue
            if norm.startswith(REFERENCE_PREFIXES):
                continue
            if norm.startswith("/") or re.match(r"^[A-Za-z]:/", norm):
                issues.append(
                    f"{entry.entry_id}: storage_scope 条目 file 引用禁止裸绝对路径，"
                    f"须使用 repo:/local:/production:/external: 前缀：`{norm}`"
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


def _resolve_local_file_reference(reference: str, base_dir: Path) -> Path | None:
    normalized = reference.strip()
    normalized = (
        normalized.replace(chr(7) + "pp", "/app")
        .replace(chr(7) + "pi", "/api")
        .replace(chr(13) + "eadiness", "/readiness")
        .replace(chr(92), "/")
    )
    normalized = LEGACY_FILE_ALIASES.get(normalized, normalized)
    if normalized.startswith(("production:", "external:")):
        return None
    if normalized.startswith(("repo:", "local:")):
        rel = normalized.split(":", 1)[1].lstrip("/")
        return ROOT_DIR / rel
    if normalized.startswith("production ") or normalized.startswith("/opt/"):
        return None
    if normalized.startswith(("http://", "https://")):
        return None
    candidate = Path(normalized)
    return candidate if candidate.is_absolute() else base_dir / candidate


def _collect_file_integrity(
    entries: tuple[EvidenceEntry, ...], base_dir: Path
) -> tuple[tuple[dict[str, str | bool], ...], list[str]]:
    integrity: list[dict[str, str | bool]] = []
    issues: list[str] = []
    seen_paths: set[Path] = set()
    for entry in entries:
        if entry.fields.get("evidence_status", "active") == "retired":
            continue
        for reference in FILE_REFERENCE_RE.findall(entry.fields.get("file", "")):
            resolved_path = _resolve_local_file_reference(reference, base_dir)
            if resolved_path is None:
                continue
            resolved_path = resolved_path.resolve()
            if resolved_path in seen_paths:
                continue
            seen_paths.add(resolved_path)
            if not resolved_path.exists():
                posix_path = resolved_path.as_posix()
                is_local_artifact = (
                    any(
                        f"{prefix}/" in posix_path for prefix in LOCAL_ARTIFACT_PREFIXES
                    )
                    or entry.fields.get("storage_scope") == "local"
                )
                if is_local_artifact:
                    integrity.append(
                        {
                            "path": str(resolved_path),
                            "exists": False,
                            "sha256": "",
                            "kind": "local-artifact-missing",
                        }
                    )
                    continue
                issues.append(f"{entry.entry_id}: evidence path missing `{reference}`")
                integrity.append(
                    {
                        "path": str(resolved_path),
                        "exists": False,
                        "sha256": "",
                        "kind": "missing",
                    }
                )
                continue
            if resolved_path.is_dir():
                integrity.append(
                    {
                        "path": str(resolved_path),
                        "exists": True,
                        "sha256": "",
                        "kind": "directory",
                    }
                )
                continue
            digest = hashlib.sha256(resolved_path.read_bytes()).hexdigest()
            recorded_sha = entry.fields.get("sha256")
            if recorded_sha:
                ref_name = reference.strip().replace("\\", "/")
                base_name = Path(ref_name).name
                if re.fullmatch(r"[0-9a-f]{64}", recorded_sha):
                    if digest != recorded_sha:
                        issues.append(
                            f"{entry.entry_id}: sha256 mismatch for `{reference}` "
                            f"(recorded {recorded_sha[:12]}.., actual {digest[:12]}..)"
                        )
                else:
                    sha_map = _parse_sha256_map(recorded_sha)
                    expected = sha_map.get(base_name) or sha_map.get(ref_name)
                    if expected and expected != digest:
                        issues.append(
                            f"{entry.entry_id}: sha256 mismatch for `{reference}` "
                            f"(recorded {expected[:12]}.., actual {digest[:12]}..)"
                        )
            integrity.append(
                {
                    "path": str(resolved_path),
                    "exists": True,
                    "sha256": digest,
                    "kind": "file",
                }
            )
    return tuple(integrity), issues


def check_evidence_index(path: Path = DEFAULT_EVIDENCE_INDEX) -> EvidenceCheckResult:
    if not path.exists():
        return EvidenceCheckResult(False, (), (f"evidence index not found: {path}",))
    content = path.read_text(encoding="utf-8-sig")
    entries = parse_entries(content)
    if not entries:
        return EvidenceCheckResult(False, (), ("evidence index has no entries",))
    base_dir = (
        ROOT_DIR if path.resolve() == DEFAULT_EVIDENCE_INDEX.resolve() else path.parent
    )
    file_integrity, file_issues = _collect_file_integrity(entries, base_dir)
    issues = validate_entries(entries)
    issues.extend(file_issues)
    return EvidenceCheckResult(not issues, entries, tuple(issues), file_integrity)


def build_json_report(result: EvidenceCheckResult, path: Path) -> dict[str, object]:
    verified_files = sum(
        1
        for item in result.file_integrity
        if item.get("exists") is True and item.get("kind") == "file"
    )
    return {
        "status": "passed" if result.passed else "failed",
        "path": str(path),
        "total": len(result.entries),
        "retired": sum(
            1
            for entry in result.entries
            if entry.fields.get("evidence_status", "active") == "retired"
        ),
        "failed": len(result.issues),
        "issues": list(result.issues),
        "verified_files": verified_files,
        "file_integrity": list(result.file_integrity),
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
            f"status={report['status']} total={report['total']} "
            f"retired={report['retired']} failed={report['failed']} "
            f"verified_files={report['verified_files']}"
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
