from __future__ import annotations

from pathlib import Path
import hashlib

from scripts import check_evidence_index as evidence_check


def _valid_entry(entry_id: str = evidence_check.PREFLIGHT_CONTRACT_EVIDENCE_ID) -> str:
    return (
        f"## {entry_id}：预检业务合约证据复核\n\n"
        "- trace_id: 20260706-preflight-contract-evidence-check\n"
        "- generated_at: 2026-07-06\n"
        "- evidence_type: local/preflight-business-contract-evidence\n"
        "- file: `scripts/check_preflight_business_contracts.py`; "
        "`reports/preflight-contract-check-20260706-232901.json`\n"
        "- command: `python scripts/check_preflight_business_contracts.py "
        '"reports\\preflight-contract-check-20260706-232901.json" --summary`\n'
        "- result: pass\n"
        "- related_logbook: 2026-07-06 - chore(preflight): 新增预检业务合约证据复核脚本\n"
        "- related_adr: none\n"
        "- contains_sensitive_data: no\n"
        "- retention_note: 不记录密钥、客户数据或订单明细。\n"
        "- summary: 校验 `business_contracts.static_checks` 包含四类业务合约状态。\n"
    )


def _write_referenced_files(tmp_path: Path) -> tuple[Path, Path]:
    checker_path = tmp_path / "scripts" / "check_preflight_business_contracts.py"
    report_path = tmp_path / "reports" / "preflight-contract-check-20260706-232901.json"
    checker_path.parent.mkdir()
    report_path.parent.mkdir()
    checker_path.write_text("checker", encoding="utf-8")
    report_path.write_text("report", encoding="utf-8")
    return checker_path, report_path


def test_complete_evidence_index_passes(tmp_path: Path) -> None:
    _write_referenced_files(tmp_path)
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text("# Evidence Index\n\n" + _valid_entry(), encoding="utf-8")

    result = evidence_check.check_evidence_index(evidence_file)

    assert result.passed is True
    assert len(result.entries) == 1
    assert result.entries[0].entry_id == evidence_check.PREFLIGHT_CONTRACT_EVIDENCE_ID


def test_missing_required_field_fails(tmp_path: Path) -> None:
    _write_referenced_files(tmp_path)
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text(
        "# Evidence Index\n\n" + _valid_entry().replace("- command:", "- missing:"),
        encoding="utf-8",
    )

    result = evidence_check.check_evidence_index(evidence_file)

    assert result.passed is False
    assert any("missing field `command`" in issue for issue in result.issues)


def test_invalid_result_and_sensitive_flag_fail(tmp_path: Path) -> None:
    _write_referenced_files(tmp_path)
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text(
        "# Evidence Index\n\n"
        + _valid_entry()
        .replace("- result: pass", "- result: ok")
        .replace("- contains_sensitive_data: no", "- contains_sensitive_data: false"),
        encoding="utf-8",
    )

    result = evidence_check.check_evidence_index(evidence_file)

    assert result.passed is False
    assert any("invalid result" in issue for issue in result.issues)
    assert any("invalid contains_sensitive_data" in issue for issue in result.issues)


def test_retired_missing_evidence_is_explicitly_excluded(tmp_path: Path) -> None:
    evidence_file = tmp_path / "evidence-index.md"
    entry = _valid_entry().replace(
        "- result: pass",
        "- result: pass\n- evidence_status: retired\n",
    )
    evidence_file.write_text("# Evidence Index\n\n" + entry, encoding="utf-8")

    result = evidence_check.check_evidence_index(evidence_file)
    report = evidence_check.build_json_report(result, evidence_file)

    assert result.passed is True
    assert report["retired"] == 1
    assert report["verified_files"] == 0


def test_invalid_evidence_status_fails(tmp_path: Path) -> None:
    _write_referenced_files(tmp_path)
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text(
        "# Evidence Index\n\n"
        + _valid_entry().replace(
            "- result: pass",
            "- result: pass\n- evidence_status: archived",
        ),
        encoding="utf-8",
    )

    result = evidence_check.check_evidence_index(evidence_file)

    assert result.passed is False
    assert any("invalid evidence_status" in issue for issue in result.issues)


def test_preflight_contract_entry_requires_checker_and_report_refs(
    tmp_path: Path,
) -> None:
    _write_referenced_files(tmp_path)
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text(
        "# Evidence Index\n\n"
        + _valid_entry()
        .replace("scripts/check_preflight_business_contracts.py", "scripts/other.py")
        .replace(
            "reports/preflight-contract-check-20260706-232901.json",
            "reports/other.json",
        )
        .replace(
            "reports\\preflight-contract-check-20260706-232901.json",
            "reports\\other.json",
        ),
        encoding="utf-8",
    )

    result = evidence_check.check_evidence_index(evidence_file)

    assert result.passed is False
    assert any(
        "check_preflight_business_contracts.py" in issue for issue in result.issues
    )
    assert any(
        "preflight-contract-check-20260706-232901.json" in issue
        for issue in result.issues
    )


def test_duplicate_evidence_id_fails(tmp_path: Path) -> None:
    _write_referenced_files(tmp_path)
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text(
        "# Evidence Index\n\n" + _valid_entry() + "\n" + _valid_entry(),
        encoding="utf-8",
    )

    result = evidence_check.check_evidence_index(evidence_file)

    assert result.passed is False
    assert any("duplicate evidence id" in issue for issue in result.issues)


def test_main_outputs_summary_and_json(tmp_path: Path, capsys) -> None:
    checker_path, report_path = _write_referenced_files(tmp_path)
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text("# Evidence Index\n\n" + _valid_entry(), encoding="utf-8")

    summary_exit_code = evidence_check.main(["--path", str(evidence_file), "--summary"])
    summary_output = capsys.readouterr().out
    json_exit_code = evidence_check.main(["--path", str(evidence_file), "--json"])
    json_output = capsys.readouterr().out

    assert summary_exit_code == 0
    assert "evidence_index status=passed" in summary_output
    assert json_exit_code == 0
    assert '"status": "passed"' in json_output
    assert '"verified_files": 2' in json_output
    assert hashlib.sha256(checker_path.read_bytes()).hexdigest() in json_output
    assert hashlib.sha256(report_path.read_bytes()).hexdigest() in json_output


def test_missing_evidence_file_fails(tmp_path: Path) -> None:
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text("# Evidence Index\n\n" + _valid_entry(), encoding="utf-8")

    result = evidence_check.check_evidence_index(evidence_file)

    assert result.passed is False
    assert any("evidence path missing" in issue for issue in result.issues)


def test_local_artifact_missing_does_not_block(tmp_path: Path) -> None:
    _write_referenced_files(tmp_path)
    evidence_file = tmp_path / "evidence-index.md"
    entry = _valid_entry() + (
        "\n## E-20260814-099：本地留存工件缺失容忍\n\n"
        "- trace_id: 20260814-local-artifact-test\n"
        "- generated_at: 2026-08-14\n"
        "- evidence_type: governance/secret-scan-gate-finalize\n"
        "- file: `reports/harness/missing-local-artifact-20260814.json`; "
        "`scripts/check_preflight_business_contracts.py`\n"
        "- command: `python -m pre_commit run detect-secrets --all-files`\n"
        "- result: pass\n"
        "- related_logbook: 2026-08-14 - docs(governance): 本地工件语义测试\n"
        "- related_adr: none\n"
        "- contains_sensitive_data: no\n"
        "- retention_note: 本地留存工件缺失不阻断新环境。\n"
        "- summary: 校验本地留存工件缺失时不阻断提交门禁。\n"
    )
    evidence_file.write_text("# Evidence Index\n\n" + entry, encoding="utf-8")

    result = evidence_check.check_evidence_index(evidence_file)
    report = evidence_check.build_json_report(result, evidence_file)

    assert result.passed is True
    assert any(
        item["kind"] == "local-artifact-missing" for item in report["file_integrity"]
    )
    assert not any("missing" in issue for issue in result.issues)


def _storage_scope_entry(file_ref: str, sha256: str | None = None) -> str:
    sha_line = f"- sha256: {sha256}\n" if sha256 else ""
    return (
        "\n## E-20260814-098：storage_scope 语义测试\n\n"
        "- trace_id: 20260814-storage-scope-test\n"
        "- generated_at: 2026-08-14\n"
        "- evidence_type: governance/storage-scope-test\n"
        f"- file: `{file_ref}`\n"
        "- command: `python scripts/check_evidence_index.py`\n"
        "- result: pass\n"
        "- related_logbook: 2026-08-14 - docs(governance): storage_scope 测试\n"
        "- related_adr: none\n"
        "- contains_sensitive_data: no\n"
        "- retention_note: 测试条目。\n"
        "- storage_scope: local\n"
        f"{sha_line}"
        "- summary: 校验 storage_scope 语义。\n"
    )


def test_storage_scope_local_sha256_match_passes(tmp_path: Path) -> None:
    _write_referenced_files(tmp_path)
    artifact = tmp_path / "reports" / "artifact.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("artifact", encoding="utf-8")
    digest = hashlib.sha256(b"artifact").hexdigest()
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text(
        "# Evidence Index\n\n"
        + _valid_entry()
        + _storage_scope_entry("reports/artifact.json", digest),
        encoding="utf-8",
    )

    result = evidence_check.check_evidence_index(evidence_file)

    assert result.passed is True


def test_storage_scope_local_sha256_mismatch_fails(tmp_path: Path) -> None:
    _write_referenced_files(tmp_path)
    artifact = tmp_path / "reports" / "artifact.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("artifact", encoding="utf-8")
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text(
        "# Evidence Index\n\n"
        + _valid_entry()
        + _storage_scope_entry("reports/artifact.json", "0" * 64),
        encoding="utf-8",
    )

    result = evidence_check.check_evidence_index(evidence_file)

    assert result.passed is False
    assert any("sha256 mismatch" in issue for issue in result.issues)


def test_storage_scope_absolute_path_requires_prefix_fails(tmp_path: Path) -> None:
    _write_referenced_files(tmp_path)
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text(
        "# Evidence Index\n\n"
        + _valid_entry()
        + _storage_scope_entry(r"D:\Project\foo\artifact.json"),
        encoding="utf-8",
    )

    result = evidence_check.check_evidence_index(evidence_file)

    assert result.passed is False
    assert any(
        "storage_scope 条目 file 引用禁止裸绝对路径" in issue for issue in result.issues
    )


def test_storage_scope_prefixed_path_allowed(tmp_path: Path) -> None:
    _write_referenced_files(tmp_path)
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text(
        "# Evidence Index\n\n"
        + _valid_entry()
        + _storage_scope_entry("local:reports/harness/dsecrets-test-20260814.json"),
        encoding="utf-8",
    )

    result = evidence_check.check_evidence_index(evidence_file)

    assert result.passed is True


def test_sha256_map_format_checks_each_file(tmp_path: Path) -> None:
    _write_referenced_files(tmp_path)
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text("aaa", encoding="utf-8")
    b.write_text("bbb", encoding="utf-8")
    ha = hashlib.sha256(b"aaa").hexdigest()
    hb = hashlib.sha256(b"bbb").hexdigest()
    entry = (
        "\n## E-20260814-097：sha256 映射格式\n\n"
        "- trace_id: 20260814-sha-map-test\n"
        "- generated_at: 2026-08-14\n"
        "- evidence_type: governance/sha-map-test\n"
        "- file: `a.json`; `b.json`\n"
        "- command: `python scripts/check_evidence_index.py`\n"
        "- result: pass\n"
        "- related_logbook: 2026-08-14 - x\n"
        "- related_adr: none\n"
        "- contains_sensitive_data: no\n"
        "- retention_note: 测试。\n"
        f"- sha256: a.json={ha}；b.json={hb}\n"
        "- summary: 校验多文件映射哈希。\n"
    )
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text(
        "# Evidence Index\n\n" + _valid_entry() + entry, encoding="utf-8"
    )
    assert evidence_check.check_evidence_index(evidence_file).passed is True
    broken = entry.replace(hb, "0" * 64)
    evidence_file.write_text(
        "# Evidence Index\n\n" + _valid_entry() + broken, encoding="utf-8"
    )
    result = evidence_check.check_evidence_index(evidence_file)
    assert result.passed is False
    assert any("sha256 mismatch" in issue for issue in result.issues)
