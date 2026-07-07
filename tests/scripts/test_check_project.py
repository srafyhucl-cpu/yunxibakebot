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
