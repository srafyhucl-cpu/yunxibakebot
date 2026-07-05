"""企微员工助手 Agent 编排服务。"""

from __future__ import annotations

from typing import Any

from app.models.employee_agent import AgentIntent, AgentPlan, ToolResult
from app.service.chat_reply import clean_plain_text_reply
from app.service.wecom.employee_agent_ops_plan import extract_campaign_id
from app.service.wecom.employee_agent_mixed_reply import build_mixed_tool_reply
from app.service.wecom.employee_agent_planner import EmployeeAgentPlanner

DEFAULT_AGENT_LIMIT = 5
UNSUPPORTED_REPLY = (
    "我还没理解这个问题。你可以直接问订单、商品库存、配送规则、待人工或系统状态。"
)


class EmployeeAgentService:
    """面向企微员工群的全业务 Agent 总编排。"""

    def __init__(
        self,
        *,
        business_tool_service: Any,
        ops_tool_service: Any,
        status_tool_service: Any,
        order_lookup_service: Any = None,
        planner: EmployeeAgentPlanner | None = None,
    ) -> None:
        self._business_tool_service = business_tool_service
        self._ops_tool_service = ops_tool_service
        self._status_tool_service = status_tool_service
        self._order_lookup_service = order_lookup_service
        self._planner = planner or EmployeeAgentPlanner()

    async def answer(self, query: str) -> str:
        """回答员工自然语言问题。"""
        plan = await self._planner.plan(query)
        tool_results = await self._execute_plan(query, plan)
        deterministic_reply = _deterministic_reply(query, plan, tool_results)
        return clean_plain_text_reply(deterministic_reply)

    async def _execute_plan(self, query: str, plan: AgentPlan) -> list[ToolResult]:
        if plan.intent == AgentIntent.ORDER_QUERY:
            return [await self._run_order_tool(query, plan)]
        if plan.intent == AgentIntent.PRODUCT_QUERY:
            return [await self._run_product_tool(query)]
        if plan.intent == AgentIntent.KNOWLEDGE_ANSWER:
            return [await self._run_knowledge_tool(query)]
        if plan.intent == AgentIntent.OPS_QUERY:
            return [await self._run_ops_tool(query, plan)]
        if plan.intent == AgentIntent.MULTI_TOOL:
            return await self._run_multi_tool(query, plan)
        return [ToolResult(ok=False, summary=UNSUPPORTED_REPLY)]

    async def _run_order_tool(self, query: str, plan: AgentPlan) -> ToolResult:
        if self._order_lookup_service is not None and plan.query_plan is not None:
            return await self._order_lookup_service.answer_agent_query(
                query,
                plan.query_plan,
            )
        payload = await self._business_tool_service.lookup_orders(_query_payload(query))
        return _tool_result_from_payload(payload)

    async def _run_product_tool(
        self,
        query: str,
        plan: AgentPlan | None = None,
    ) -> ToolResult:
        if plan is not None and plan.query_plan is not None and plan.query_plan.keyword:
            query = plan.query_plan.keyword
        payload = await self._business_tool_service.lookup_products(
            _query_payload(query)
        )
        return _tool_result_from_payload(payload)

    async def _run_knowledge_tool(self, query: str) -> ToolResult:
        payload = await self._business_tool_service.answer_knowledge(
            {"question": query, "limit": DEFAULT_AGENT_LIMIT}
        )
        return _tool_result_from_payload(payload)

    async def _run_ops_tool(self, query: str, plan: AgentPlan) -> ToolResult:
        if "customer_lookup" in plan.tools:
            payload = await self._ops_tool_service.lookup_customer(
                _query_payload(query)
            )
            return _tool_result_from_payload(payload)
        if "group_campaign_summary" in plan.tools:
            payload = await self._ops_tool_service.summarize_group_campaign(
                {
                    "campaignId": extract_campaign_id(query),
                    "query": query,
                    "limit": DEFAULT_AGENT_LIMIT,
                }
            )
            return _tool_result_from_payload(payload)
        if "handoff_pending" in plan.tools:
            payload = await self._ops_tool_service.list_pending_handoffs({})
            return _tool_result_from_payload(payload)
        if "offline_review_summary" in plan.tools:
            payload = await self._status_tool_service.summarize_offline_review(
                _query_payload(query)
            )
            return _tool_result_from_payload(payload)
        if "integration_status" in plan.tools:
            payload = await self._status_tool_service.summarize_integrations(
                _query_payload(query)
            )
            return _tool_result_from_payload(payload)
        payload = await self._status_tool_service.summarize_ops({})
        return _tool_result_from_payload(payload)

    async def _run_multi_tool(self, query: str, plan: AgentPlan) -> list[ToolResult]:
        results: list[ToolResult] = []
        if "order_dynamic_query" in plan.tools:
            results.append(await self._run_order_tool(query, plan))
        if "product_lookup" in plan.tools:
            results.append(await self._run_product_tool(query, plan))
        if "knowledge_answer" in plan.tools:
            results.append(await self._run_knowledge_tool(query))
        if not results:
            results.append(ToolResult(ok=False, summary=UNSUPPORTED_REPLY))
        return results


def _query_payload(query: str) -> dict[str, Any]:
    return {"query": query, "limit": DEFAULT_AGENT_LIMIT}


def _tool_result_from_payload(payload: dict[str, Any]) -> ToolResult:
    return ToolResult(
        ok=bool(payload.get("ok", False)),
        summary=str(
            payload.get("result")
            or payload.get("resultText")
            or payload.get("summary")
            or ""
        ),
        items=_extract_items(payload),
        metrics=_extract_metrics(payload),
        next_action=str(payload.get("nextAction", "")),
    )


def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("orders", "products", "sources", "addresses", "transfers", "webhooks"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _extract_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("counts") or payload.get("metrics")
    return value if isinstance(value, dict) else {}


def _deterministic_reply(
    query: str,
    plan: AgentPlan,
    tool_results: list[ToolResult],
) -> str:
    mixed_reply = build_mixed_tool_reply(query, plan, tool_results)
    if mixed_reply is not None:
        return mixed_reply
    lines = [result.summary for result in tool_results if result.summary.strip()]
    if not lines:
        return UNSUPPORTED_REPLY
    next_actions = [
        result.next_action for result in tool_results if result.next_action.strip()
    ]
    if next_actions:
        lines.append("下一步：" + "；".join(next_actions))
    return "\n".join(lines)
