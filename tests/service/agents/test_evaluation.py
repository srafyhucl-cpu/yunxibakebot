"""Agent Eval 通用模型测试。"""

from app.service.agents.evaluation import (
    AgentEvalAssertion,
    AgentEvalCase,
    AgentEvalResult,
    combine_agent_eval_results,
)


def test_agent_eval_result_calculates_status_and_pass_rate() -> None:
    result = AgentEvalResult(
        agent="sample",
        cases=(
            AgentEvalCase(
                case_id="ok",
                agent="sample",
                query="ok",
                assertions=(AgentEvalAssertion("shape", True),),
            ),
            AgentEvalCase(
                case_id="fail",
                agent="sample",
                query="fail",
                assertions=(AgentEvalAssertion("shape", False, "bad"),),
            ),
        ),
    )

    payload = result.to_dict()

    assert result.status == "failed"
    assert result.failed == 1
    assert result.pass_rate == 0.5
    assert payload["failed_ids"] == ["fail"]


def test_combine_agent_eval_results() -> None:
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

    payload = combine_agent_eval_results((customer, employee))

    assert payload["status"] == "passed"
    assert payload["total"] == 2
    assert payload["pass_rate"] == 1.0
