from __future__ import annotations

from pathlib import Path

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


def test_complete_evidence_index_passes(tmp_path: Path) -> None:
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text("# Evidence Index\n\n" + _valid_entry(), encoding="utf-8")

    result = evidence_check.check_evidence_index(evidence_file)

    assert result.passed is True
    assert len(result.entries) == 1
    assert result.entries[0].entry_id == evidence_check.PREFLIGHT_CONTRACT_EVIDENCE_ID


def test_missing_required_field_fails(tmp_path: Path) -> None:
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text(
        "# Evidence Index\n\n" + _valid_entry().replace("- command:", "- missing:"),
        encoding="utf-8",
    )

    result = evidence_check.check_evidence_index(evidence_file)

    assert result.passed is False
    assert any("missing field `command`" in issue for issue in result.issues)


def test_invalid_result_and_sensitive_flag_fail(tmp_path: Path) -> None:
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


def test_preflight_contract_entry_requires_checker_and_report_refs(
    tmp_path: Path,
) -> None:
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
    evidence_file = tmp_path / "evidence-index.md"
    evidence_file.write_text(
        "# Evidence Index\n\n" + _valid_entry() + "\n" + _valid_entry(),
        encoding="utf-8",
    )

    result = evidence_check.check_evidence_index(evidence_file)

    assert result.passed is False
    assert any("duplicate evidence id" in issue for issue in result.issues)


def test_main_outputs_summary_and_json(tmp_path: Path, capsys) -> None:
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
