"""Agent Eval 脚本测试。"""

from __future__ import annotations

import json

import pytest

from app.service.agents.evaluation import (
    AgentEvalAssertion,
    AgentEvalCase,
    AgentEvalResult,
)
from scripts import eval_customer_agent, eval_employee_agent, report_agent_eval


def test_customer_eval_result_uses_golden_cases() -> None:
    result = eval_customer_agent.build_customer_eval_result()

    assert result.status == "passed"
    assert result.total == 9
    assert {case.group for case in result.cases} >= {
        "product_consultation",
        "delivery",
        "refund_after_sales",
        "human_transfer",
    }


@pytest.mark.asyncio
async def test_employee_eval_result_includes_planner_and_contracts() -> None:
    result = await eval_employee_agent.build_employee_eval_result()

    assert result.status == "passed"
    assert result.total == 49
    assert result.cases[0].case_id == "employee.capability_contracts"


@pytest.mark.asyncio
async def test_report_agent_eval_outputs_combined_json(monkeypatch, capsys) -> None:
    customer = AgentEvalResult(
        agent="customer",
        cases=(
            AgentEvalCase(
                case_id="customer-ok",
                agent="customer",
                query="ok",
                assertions=(AgentEvalAssertion("shape", True),),
            ),
        ),
    )
    employee = AgentEvalResult(
        agent="employee",
        cases=(
            AgentEvalCase(
                case_id="employee-ok",
                agent="employee",
                query="ok",
                assertions=(AgentEvalAssertion("shape", True),),
            ),
        ),
    )

    monkeypatch.setattr(
        report_agent_eval,
        "build_customer_eval_result",
        lambda: customer,
    )

    async def fake_employee_result() -> AgentEvalResult:
        return employee

    monkeypatch.setattr(
        report_agent_eval,
        "build_employee_eval_result",
        fake_employee_result,
    )

    exit_code = await report_agent_eval.main(["--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "passed"
    assert payload["total"] == 2
