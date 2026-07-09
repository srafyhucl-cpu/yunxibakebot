from __future__ import annotations

import json
from pathlib import Path

from scripts import build_real_conversation_replay_intake_packet as intake_packet


def test_intake_packet_contains_external_operator_command_chain() -> None:
    report = intake_packet.build_real_replay_intake_packet(
        source_description="external_helpdesk_export_2026_07",
        operator="reviewer_a",
        evidence_id="E-REAL-001",
    )

    assert report["status"] == "passed"
    assert report["failed"] == 0
    assert report["boundaries"]["raw_customer_conversation_read"] is False
    assert report["boundaries"]["real_customer_data_committed"] is False
    assert "order" in report["required_scenarios"]
    assert "refund" in report["required_scenarios"]

    command_steps = [item["step"] for item in report["commands"]]
    assert command_steps == [
        "export_redacted_fixture",
        "check_replay_contract",
        "check_sensitive_scenario_coverage",
        "prepare_pool_entry_draft",
        "verify_pool_strict_gate",
        "verify_intake_strict_gate",
    ]
    assert any("--require-real" in item["command"] for item in report["commands"])


def test_intake_packet_rejects_insufficient_target_count() -> None:
    report = intake_packet.build_real_replay_intake_packet(target_count=1)

    assert report["status"] == "failed"
    assert report["assertions"]["target_count.covers_required_scenarios"] is False


def test_intake_packet_cli_writes_json(tmp_path: Path) -> None:
    output_path = tmp_path / "packet.json"

    exit_code = intake_packet.main(
        [
            "--operator",
            "reviewer_b",
            "--evidence-id",
            "E-REAL-002",
            "--json-out",
            str(output_path),
            "--summary",
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["status"] == "passed"
    assert payload["operator"] == "reviewer_b"
    assert payload["evidence_id"] == "E-REAL-002"
