"""脱敏真实会话 replay 样本池准入检查测试。"""

from __future__ import annotations

import json
from pathlib import Path

from scripts import check_real_conversation_replay_pool


def test_real_replay_pool_manifest_sample_passes_without_real_claim() -> None:
    report = check_real_conversation_replay_pool.build_real_replay_pool_report()

    assert report["status"] == "passed"
    assert report["total"] == 1
    assert report["failed"] == 0
    assert report["real_entries"] == 0
    assert report["synthetic_entries"] == 1
    assert report["real_pool_ready"] is False
    assert report["entries"][0]["coverage"]["status"] == "passed"


def test_real_replay_pool_require_real_rejects_synthetic_only_manifest() -> None:
    report = check_real_conversation_replay_pool.build_real_replay_pool_report(
        require_real=True
    )

    assert report["status"] == "failed"
    assert report["failed"] == 1
    assert report["real_pool_ready"] is False


def test_real_replay_pool_can_mark_real_entry_ready(tmp_path: Path) -> None:
    manifest_path = tmp_path / "pool.json"
    manifest_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "source": "unit_test_real_pool",
                    "contains_real_customer_data": True,
                },
                "entries": [
                    {
                        "name": "approved_real_pool",
                        "fixture": "tests/fixtures/customer_real_replay_coverage_sample.json",
                        "enabled": True,
                        "is_real_customer_data": True,
                        "purpose": "approved_redacted_regression",
                        "min_per_scenario": 5,
                        "evidence_id": "E-UNIT-REAL",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = check_real_conversation_replay_pool.build_real_replay_pool_report(
        manifest_path=manifest_path,
        require_real=True,
    )

    assert report["status"] == "passed"
    assert report["real_entries"] == 1
    assert report["real_pool_ready"] is True


def test_real_replay_pool_rejects_sensitive_fixture(tmp_path: Path) -> None:
    fixture_path = tmp_path / "sensitive.json"
    manifest_path = tmp_path / "pool.json"
    fixture_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "source": "bad_fixture",
                    "contains_sensitive_data": True,
                },
                "cases": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "metadata": {"source": "unit_test_pool"},
                "entries": [
                    {
                        "name": "bad_fixture",
                        "fixture": str(fixture_path),
                        "enabled": True,
                        "is_real_customer_data": True,
                        "purpose": "bad",
                        "min_per_scenario": 5,
                        "evidence_id": "E-UNIT-BAD",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = check_real_conversation_replay_pool.build_real_replay_pool_report(
        manifest_path=manifest_path
    )

    assert report["status"] == "failed"
    assert (
        report["entries"][0]["assertions"]["fixture.contains_sensitive_data_false"]
        is False
    )


def test_real_replay_pool_cli_writes_json(tmp_path: Path) -> None:
    output_path = tmp_path / "pool-report.json"

    exit_code = check_real_conversation_replay_pool.main(
        ["--json-out", str(output_path), "--summary"]
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["status"] == "passed"
    assert payload["real_pool_ready"] is False
