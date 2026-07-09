from __future__ import annotations

import json
from pathlib import Path

from scripts import check_langchain_ai_layer_capacity as capacity


def _write_trace(path: Path, event_count: int = 2) -> None:
    path.write_text(
        json.dumps(
            {
                "traces": [
                    {
                        "agent": "customer",
                        "trace_events": [
                            {"node": f"node_{index}", "event": "node"}
                            for index in range(event_count)
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_capacity_report_passes_with_small_trace(monkeypatch, tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.json"
    _write_trace(trace_path)
    monkeypatch.setattr(
        capacity,
        "build_cold_import_summary",
        lambda module_name: {
            "module": module_name,
            "status": "passed",
            "heavy_loaded": [],
        },
    )

    report = capacity.build_capacity_report(
        trace_input_path=trace_path,
        run_trace_probe=False,
    )

    assert report["status"] == "passed"
    assert report["trace_probe"]["status"] == "ok"
    assert report["trace_probe"]["total_runs"] == 1
    assert report["boundaries"]["production_load_test"] is False
    assert report["boundaries"]["external_llm_called"] is False
    assert report["langsmith_rollout"]["enabled"] is False


def test_capacity_report_rejects_payload_over_limit(
    monkeypatch,
    tmp_path: Path,
) -> None:
    trace_path = tmp_path / "trace.json"
    _write_trace(trace_path)
    monkeypatch.setattr(
        capacity,
        "build_cold_import_summary",
        lambda module_name: {
            "module": module_name,
            "status": "passed",
            "heavy_loaded": [],
        },
    )

    report = capacity.build_capacity_report(
        trace_input_path=trace_path,
        run_trace_probe=False,
        max_trace_payload_bytes=1,
    )

    assert report["status"] == "failed"
    assert report["assertions"]["trace_probe.payload_within_limit"] is False
    assert "reduce_trace_payload_size_or_redaction_scope" in report["missing_actions"]


def test_capacity_report_requires_trace_when_probe_skipped() -> None:
    report = capacity.build_capacity_report(run_trace_probe=False)

    assert report["status"] == "failed"
    assert report["assertions"]["trace_probe.ok"] is False
    assert "fix_agent_trace_probe_before_capacity_gate" in report["missing_actions"]


def test_capacity_report_detects_cold_import_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    trace_path = tmp_path / "trace.json"
    _write_trace(trace_path)
    monkeypatch.setattr(
        capacity,
        "build_cold_import_summary",
        lambda module_name: {
            "module": module_name,
            "status": "failed",
            "heavy_loaded": ["langsmith"],
        },
    )

    report = capacity.build_capacity_report(
        trace_input_path=trace_path,
        run_trace_probe=False,
    )

    assert report["status"] == "failed"
    assert report["assertions"]["cold_imports.passed"] is False
    assert "fix_heavy_import_before_production_rollout" in report["missing_actions"]


def test_capacity_cli_writes_json(monkeypatch, tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.json"
    output_path = tmp_path / "capacity.json"
    _write_trace(trace_path)
    monkeypatch.setattr(
        capacity,
        "build_cold_import_summary",
        lambda module_name: {
            "module": module_name,
            "status": "passed",
            "heavy_loaded": [],
        },
    )

    exit_code = capacity.main(
        [
            "--trace-input",
            str(trace_path),
            "--json-out",
            str(output_path),
            "--summary",
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["status"] == "passed"
    assert payload["trace_probe"]["total_runs"] == 1
