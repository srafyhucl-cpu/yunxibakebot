"""企微员工助手 LLM 计划解析。"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from app.models.employee_agent import (
    AgentIntent,
    AgentPlan,
    AnswerStyle,
    OrderQueryKind,
    OrderQueryPlan,
)
from app.service.wecom.employee_agent_capabilities import AgentCapabilityCard
from app.service.wecom.employee_agent_order_query import extract_limit_from_value


def build_planner_prompt(
    query: str,
    capabilities: list[AgentCapabilityCard],
) -> str:
    """构造只输出 JSON 的规划提示。"""
    capability_text = "\n".join(
        f"- {card.name}: {card.description}；示例：{' / '.join(card.examples)}"
        for card in capabilities
    )
    return (
        "你是芸熙烘焙内部员工助手的规划器。只输出 JSON，不要输出解释。\n"
        "只能使用这些 intent: order_query, product_query, knowledge_answer, "
        "ops_query, multi_tool, unsupported。\n"
        "只能生成查询计划，不要生成 SQL。\n"
        f"可用能力：\n{capability_text or '无'}\n"
        f"员工问题：{query}\n"
        "JSON 字段：intent, tools, queryPlan, answerStyle。"
    )


def parse_llm_plan(raw_content: str, today: date) -> AgentPlan | None:
    """把 LLM JSON 输出转成安全 AgentPlan。"""
    try:
        parsed = json.loads(_strip_json_markdown(raw_content))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    intent = _safe_enum(AgentIntent, parsed.get("intent"), AgentIntent.UNSUPPORTED)
    answer_style = _safe_enum(
        AnswerStyle,
        parsed.get("answerStyle"),
        AnswerStyle.SUMMARY,
    )
    tools = tuple(
        str(tool) for tool in parsed.get("tools", []) if isinstance(tool, str)
    )
    query_plan = _parse_order_plan(parsed.get("queryPlan"))
    return AgentPlan(
        intent=intent,
        tools=tools,
        query_plan=query_plan,
        answer_style=answer_style,
    )


def _parse_order_plan(raw_plan: Any) -> OrderQueryPlan | None:
    if not isinstance(raw_plan, dict):
        return None
    kind = _safe_enum(OrderQueryKind, raw_plan.get("kind"), OrderQueryKind.LIST)
    statuses = raw_plan.get("statuses")
    safe_statuses = (
        tuple(str(status) for status in statuses if isinstance(status, str))
        if isinstance(statuses, list)
        else ()
    )
    return OrderQueryPlan(
        kind=kind,
        date_from=str(raw_plan.get("dateFrom") or ""),
        date_to=str(raw_plan.get("dateTo") or ""),
        date_field=_safe_date_field(raw_plan.get("dateField")),
        statuses=safe_statuses,
        keyword=str(raw_plan.get("keyword") or ""),
        needs_missing_logistics=bool(raw_plan.get("needsMissingLogistics")),
        needs_refund=bool(raw_plan.get("needsRefund")),
        needs_fulfillment_risk=bool(raw_plan.get("needsFulfillmentRisk")),
        delivery_time_start=str(raw_plan.get("deliveryTimeStart") or ""),
        delivery_time_end=str(raw_plan.get("deliveryTimeEnd") or ""),
        aggregate_by=str(raw_plan.get("aggregateBy") or ""),
        sort_by=str(raw_plan.get("sortBy") or "latest"),
        limit=extract_limit_from_value(raw_plan.get("limit")),
    )


def _safe_enum(enum_type: Any, value: Any, fallback: Any) -> Any:
    try:
        return enum_type(str(value))
    except ValueError:
        return fallback


def _safe_date_field(value: Any) -> str:
    raw_value = str(value or "order_time")
    return raw_value if raw_value in {"order_time", "delivery_time"} else "order_time"


def _strip_json_markdown(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```json"):
        stripped = stripped.removeprefix("```json")
    if stripped.endswith("```"):
        stripped = stripped.removesuffix("```")
    return stripped.strip()
