import json
from datetime import date

from app.models.employee_agent import AgentIntent, AgentPlan
from scripts import check_wecom_employee_agent_plans as plan_check


async def test_run_plan_checks_covers_free_form_queries() -> None:
    checks = await plan_check.run_plan_checks(date(2026, 7, 3))
    report = plan_check.build_json_report(checks)

    assert report["status"] == "passed"
    assert report["total"] == 13
    assert report["failed"] == 0
    assert {check.name for check in checks} == {
        "today-order-summary",
        "pending-shipment-list",
        "missing-logistics-list",
        "product-order-summary",
        "top-products",
        "order-product-inventory",
        "casual-inventory",
        "delivery-knowledge",
        "ops-status",
        "handoff-pending",
        "customer-lookup",
        "group-campaign-summary",
        "offline-review-summary",
    }


def test_evaluate_probe_reports_field_mismatch() -> None:
    probe = plan_check.AgentPlanProbe(
        "wrong-intent",
        "今天一共多少订单",
        "order_query",
        ("order_dynamic_query",),
    )

    check = plan_check.evaluate_probe(
        probe,
        AgentPlan(intent=AgentIntent.KNOWLEDGE_ANSWER, tools=("knowledge_answer",)),
    )

    assert check.passed is False
    assert "intent" in check.detail
    assert "tools" in check.detail


async def test_main_json_output_can_be_written_to_file(
    monkeypatch,
    tmp_path,
) -> None:
    async def fake_run_plan_checks():
        return [
            plan_check.AgentPlanCheck(
                name="ok",
                query="今天一共多少订单",
                passed=True,
                intent="order_query",
                tools=("order_dynamic_query",),
                kind="summary",
                date_from="2026-07-03",
                date_to="2026-07-03",
                statuses=(),
                keyword="",
                missing_logistics=False,
            )
        ]

    monkeypatch.setattr(plan_check, "run_plan_checks", fake_run_plan_checks)
    report_path = tmp_path / "reports" / "employee-agent-plans.json"

    exit_code = await plan_check.main(["--json", "--output", str(report_path)])

    assert exit_code == 0
    assert report_path.read_bytes().startswith(plan_check.UTF8_BOM)
    payload = json.loads(report_path.read_text(encoding="utf-8-sig"))
    assert payload["status"] == "passed"
    assert payload["checks"][0]["tools"] == ["order_dynamic_query"]


async def test_main_rejects_output_without_json(capsys) -> None:
    exit_code = await plan_check.main(["--output", "report.json"])

    assert exit_code == 2
    assert "--output" in capsys.readouterr().err
