"""Agent Eval 脚本测试。"""

from __future__ import annotations

import json
from pathlib import Path

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
    assert result.total == 71
    assert {case.group for case in result.cases} >= {
        "product_consultation",
        "delivery",
        "refund_after_sales",
        "human_transfer",
    }
    sensitive_cases = [
        case for case in result.cases if case.metadata.get("sensitive_scenarios")
    ]
    assert len(sensitive_cases) >= 30
    assert {
        scenario
        for case in sensitive_cases
        for scenario in case.metadata["sensitive_scenarios"]
    } >= {"order", "refund", "after_sales", "inventory", "price", "human_transfer"}
    order_case = next(
        case for case in result.cases if case.case_id == "customer-order-sensitive-004"
    )
    assert {assertion.name for assertion in order_case.assertions} >= {
        "sensitive_policy.order",
        "sensitive_policy.human_transfer",
        "forbidden_reply_patterns.present",
    }
    assert "已为您查到订单" in order_case.metadata["forbidden_reply_patterns"]


@pytest.mark.asyncio
async def test_employee_eval_result_includes_planner_and_contracts() -> None:
    result = await eval_employee_agent.build_employee_eval_result()

    assert result.status == "passed"
    assert result.total == 62
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
                metadata={"sensitive_scenarios": ["order"]},
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
    assert payload["sensitive_scenarios"] == [
        {
            "scenario": "order",
            "total": 1,
            "failed": 0,
            "passed": 1,
            "pass_rate": 1.0,
        }
    ]


@pytest.mark.asyncio
async def test_report_agent_eval_filters_agent_case_and_writes_json(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    customer = AgentEvalResult(
        agent="customer",
        cases=(
            AgentEvalCase(
                case_id="customer-keep",
                agent="customer",
                query="ok",
                assertions=(AgentEvalAssertion("shape", True),),
            ),
            AgentEvalCase(
                case_id="customer-drop",
                agent="customer",
                query="drop",
                assertions=(AgentEvalAssertion("shape", True),),
            ),
        ),
    )

    monkeypatch.setattr(
        report_agent_eval,
        "build_customer_eval_result",
        lambda: customer,
    )
    output_path = tmp_path / "agent-eval.json"

    exit_code = await report_agent_eval.main(
        [
            "--agent",
            "customer",
            "--case-id",
            "customer-keep",
            "--json-out",
            str(output_path),
            "--summary",
        ]
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "agent_eval status=passed total=1 failed=0" in capsys.readouterr().out
    assert payload["metadata"]["agent_filter"] == "customer"
    assert payload["agents"][0]["cases"][0]["id"] == "customer-keep"


def test_customer_eval_main_supports_json_out_case_filter(
    tmp_path: Path,
    capsys,
) -> None:
    output_path = tmp_path / "customer-eval.json"

    exit_code = eval_customer_agent.main(
        [
            "--case-id",
            "customer-product-001",
            "--json-out",
            str(output_path),
            "--summary",
        ]
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "customer_agent_eval status=passed total=1" in capsys.readouterr().out
    assert payload["cases"][0]["id"] == "customer-product-001"


@pytest.mark.asyncio
async def test_employee_eval_main_supports_json_out_case_filter(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    employee = AgentEvalResult(
        agent="employee",
        cases=(
            AgentEvalCase(
                case_id="employee-keep",
                agent="employee",
                query="ok",
                assertions=(AgentEvalAssertion("shape", True),),
            ),
            AgentEvalCase(
                case_id="employee-drop",
                agent="employee",
                query="drop",
                assertions=(AgentEvalAssertion("shape", True),),
            ),
        ),
    )

    async def fake_employee_result() -> AgentEvalResult:
        return employee

    monkeypatch.setattr(
        eval_employee_agent,
        "build_employee_eval_result",
        fake_employee_result,
    )
    output_path = tmp_path / "employee-eval.json"

    exit_code = await eval_employee_agent.main(
        [
            "--case-id",
            "employee-keep",
            "--json-out",
            str(output_path),
            "--summary",
        ]
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "employee_agent_eval status=passed total=1" in capsys.readouterr().out
    assert payload["cases"][0]["id"] == "employee-keep"
