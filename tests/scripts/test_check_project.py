import subprocess
import sys

from scripts import check_project


def test_business_contract_checks_are_registered() -> None:
    commands = [" ".join(command) for command in check_project.CONTRACT_COMMANDS]

    assert any(
        "check_employee_agent_capability_contracts.py" in command
        for command in commands
    )
    assert any("check_customer_rag_golden_cases.py" in command for command in commands)
    assert any("check_knowledge_governance_plan.py" in command for command in commands)
    assert any(
        "check_customer_memory_governance_plan.py" in command for command in commands
    )
    assert any(
        "check_customer_observability_contract.py" in command for command in commands
    )
    assert any("check_miniapp_page_api_contract.py" in command for command in commands)
    assert any(
        "check_github_reference_implementation_plan.py" in command
        for command in commands
    )


def test_project_contract_checks_pass() -> None:
    results = check_project.run_contract_checks()

    assert results
    assert all(result.passed for result in results)


def test_run_command_sets_fake_embedding_for_quality_commands(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs["env"])
        return subprocess.CompletedProcess(args[0], 0, stdout="ok", stderr="")

    monkeypatch.setattr(check_project.subprocess, "run", fake_run)

    result = check_project.run_command(
        (sys.executable, "scripts/report_rag_shadow_observability.py", "--summary")
    )

    assert result.passed is True
    assert captured["PYTHONUTF8"] == "1"
    assert captured["YUNXI_USE_FAKE_EMBEDDING"] == "1"


def test_contract_checks_cache_read_only_results(monkeypatch) -> None:
    calls = 0

    def fake_run_command(_command):
        nonlocal calls
        calls += 1
        return check_project.CheckResult("contract", True, [])

    monkeypatch.setattr(check_project, "run_command", fake_run_command)
    check_project.run_contract_checks.cache_clear()

    first = check_project.run_contract_checks()
    second = check_project.run_contract_checks()

    assert first == second
    assert calls == len(check_project.CONTRACT_COMMANDS)
    check_project.run_contract_checks.cache_clear()


def test_doc_guard_flags_stale_causal_ordering(tmp_path) -> None:
    doc = tmp_path / "spec.md"
    doc.write_text(
        "# 测试\n\n新模型按 `(occurred_at, id)` 单调排序。\n", encoding="utf-8"
    )
    result = check_project.check_contract_doc_legacy_terms((tmp_path,))
    assert not result.passed
    assert "旧因果排序口径" in result.details[0]


def test_doc_guard_allows_prohibition_statements(tmp_path) -> None:
    doc = tmp_path / "spec.md"
    doc.write_text(
        "# 测试\n\n禁止以 `(occurred_at, id)` 承担因果语义。\n", encoding="utf-8"
    )
    result = check_project.check_contract_doc_legacy_terms((tmp_path,))
    assert result.passed


def test_doc_guard_flags_stale_terms(tmp_path) -> None:
    doc = tmp_path / "spec.md"
    doc.write_text(
        "# 测试\n\n收回不足为 manual_review + 冻结额度。\n"
        "币种 fee_type=CNY。\n"
        "| 其他绕过统一入口的写路径 | — |\n",
        encoding="utf-8",
    )
    result = check_project.check_contract_doc_legacy_terms((tmp_path,))
    assert not result.passed
    assert len(result.details) == 3


def test_doc_guard_passes_on_active_contract_docs() -> None:
    result = check_project.check_contract_doc_legacy_terms()
    assert result.passed, result.details
