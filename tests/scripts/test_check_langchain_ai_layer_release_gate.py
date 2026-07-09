"""LangChain AI 应用层发布门禁测试。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scripts import check_langchain_ai_layer_release_gate as release_gate


def test_build_gate_steps_keeps_rag_matrix_optional() -> None:
    steps = release_gate.build_gate_steps(include_rag_matrix=False)

    assert [step.name for step in steps] == [
        "agent_eval_default",
        "customer_reply_replay_probe",
        "agent_eval_with_reply_replay",
    ]


def test_build_gate_steps_can_include_rag_matrix() -> None:
    steps = release_gate.build_gate_steps(include_rag_matrix=True)

    assert steps[-1].name == "rag_eval_matrix"
    assert "scripts/report_retrieval_eval_matrix.py" in steps[-1].command


def test_build_gate_steps_keeps_production_smoke_optional() -> None:
    steps = release_gate.build_gate_steps(include_production_smoke=False)

    assert "production_smoke" not in [step.name for step in steps]
    assert "production_employee_callback_probe" not in [step.name for step in steps]


def test_build_gate_steps_can_include_production_smoke() -> None:
    steps = release_gate.build_gate_steps(
        include_production_smoke=True,
        production_base_url="https://example.com",
    )

    step_by_name = {step.name: step for step in steps}
    smoke_step = step_by_name["production_smoke"]
    callback_step = step_by_name["production_employee_callback_probe"]

    assert "scripts/smoke_test.py" in smoke_step.command
    assert "scripts/check_wecom_employee_agent_callback.py" in callback_step.command
    assert "https://example.com" in smoke_step.command
    assert "https://example.com" in callback_step.command
    assert "--http-only" in smoke_step.command
    assert "--json" in smoke_step.command
    assert "--output" in callback_step.command


def test_run_gate_steps_stops_on_failure(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(command, **_kwargs):
        calls.append(tuple(command))
        return SimpleNamespace(
            returncode=1 if len(calls) == 2 else 0,
            stdout="ok",
            stderr="failed",
        )

    monkeypatch.setattr(release_gate.subprocess, "run", fake_run)

    results = release_gate.run_gate_steps(
        (
            release_gate.GateStep("first", ("python", "first.py")),
            release_gate.GateStep("second", ("python", "second.py")),
            release_gate.GateStep("third", ("python", "third.py")),
        )
    )

    assert [result.name for result in results] == ["first", "second"]
    assert results[-1].passed is False


def test_gate_step_result_tolerates_missing_streams() -> None:
    result = release_gate.GateStepResult(
        name="encoding-noise",
        command=("python", "noisy.py"),
        returncode=0,
        stdout=None,
        stderr=None,
    )

    payload = result.to_dict()

    assert payload["stdout"] == ""
    assert payload["stderr"] == ""


def test_main_writes_json_summary(monkeypatch, tmp_path: Path, capsys) -> None:
    def fake_run_gate_steps(_steps):
        return (
            release_gate.GateStepResult(
                name="agent_eval_default",
                command=("python", "scripts/report_agent_eval.py"),
                returncode=0,
                stdout="agent_eval status=passed total=133 failed=0",
                stderr="",
            ),
        )

    monkeypatch.setattr(release_gate, "run_gate_steps", fake_run_gate_steps)
    output_path = tmp_path / "gate.json"

    exit_code = release_gate.main(["--json-out", str(output_path), "--summary"])

    assert exit_code == 0
    assert output_path.exists()
    assert "langchain_ai_layer_release_gate status=passed" in capsys.readouterr().out


def test_main_records_production_smoke_options(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    captured_steps: list[release_gate.GateStep] = []

    def fake_run_gate_steps(steps):
        captured_steps.extend(steps)
        return (
            release_gate.GateStepResult(
                name="production_smoke",
                command=("python", "scripts/smoke_test.py"),
                returncode=0,
                stdout="{}",
                stderr="",
            ),
        )

    monkeypatch.setattr(release_gate, "run_gate_steps", fake_run_gate_steps)
    output_path = tmp_path / "gate.json"

    exit_code = release_gate.main(
        [
            "--include-production-smoke",
            "--production-base-url",
            "https://example.com",
            "--json-out",
            str(output_path),
            "--summary",
        ]
    )

    payload = release_gate.json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert any(step.name == "production_smoke" for step in captured_steps)
    assert payload["include_production_smoke"] is True
    assert payload["production_base_url"] == "https://example.com"
    assert "langchain_ai_layer_release_gate status=passed" in capsys.readouterr().out


def test_ensure_output_directories_creates_rag_parent(
    tmp_path: Path, monkeypatch
) -> None:
    rag_path = tmp_path / "rag-eval" / "latest.json"
    monkeypatch.setattr(release_gate, "DEFAULT_RAG_MATRIX_PATH", rag_path)
    monkeypatch.setattr(
        release_gate,
        "DEFAULT_AGENT_EVAL_PATH",
        tmp_path / "agent-eval" / "latest.json",
    )
    monkeypatch.setattr(
        release_gate,
        "DEFAULT_REPLY_PROBE_PATH",
        tmp_path / "agent-eval" / "reply-probe.json",
    )
    monkeypatch.setattr(
        release_gate,
        "DEFAULT_REPLY_EVAL_PATH",
        tmp_path / "agent-eval" / "reply-eval.json",
    )

    release_gate.ensure_output_directories(include_rag_matrix=True)

    assert rag_path.parent.exists()


def test_ensure_output_directories_creates_production_report_parents(
    tmp_path: Path, monkeypatch
) -> None:
    smoke_path = tmp_path / "smoke" / "prod.json"
    callback_path = tmp_path / "wecom-employee-agent" / "callback.json"
    monkeypatch.setattr(
        release_gate,
        "DEFAULT_AGENT_EVAL_PATH",
        tmp_path / "agent-eval" / "latest.json",
    )
    monkeypatch.setattr(
        release_gate,
        "DEFAULT_REPLY_PROBE_PATH",
        tmp_path / "agent-eval" / "reply-probe.json",
    )
    monkeypatch.setattr(
        release_gate,
        "DEFAULT_REPLY_EVAL_PATH",
        tmp_path / "agent-eval" / "reply-eval.json",
    )
    monkeypatch.setattr(release_gate, "DEFAULT_PRODUCTION_SMOKE_PATH", smoke_path)
    monkeypatch.setattr(
        release_gate,
        "DEFAULT_PRODUCTION_CALLBACK_PATH",
        callback_path,
    )

    release_gate.ensure_output_directories(
        include_rag_matrix=False,
        include_production_smoke=True,
    )

    assert smoke_path.parent.exists()
    assert callback_path.parent.exists()
