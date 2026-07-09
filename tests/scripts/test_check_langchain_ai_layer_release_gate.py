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
