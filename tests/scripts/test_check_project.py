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
