"""客户机器人 LangGraph 节点。"""

from typing import Any
import json

from app.service.agents.customer.contracts import CustomerGraphDependencies
from app.service.agents.customer.state import CustomerAgentState
from app.service.agents.customer.constants import CUSTOMER_TOOL_ROUND_LIMIT
from app.service.agents.customer.memory import load_customer_memory_block
from app.service.agents.tools.customer import CustomerToolContext
from app.service.agents.tools.registry import build_tools
from app.service.agents.customer.support import (
    build_transfer_handler,
    extend_guard_source_with_tool_outputs,
    record_tool_round_limit,
    record_tool_rounds,
)
from app.service.chat_context import prepare_ai_conversation_messages
from app.service.chat_context_budget import record_tool_context_budget_delta
from app.service.agents.customer.model import (
    CustomerModelRequest,
    request_customer_model_with_tools,
)
from app.service.agents.observability import (
    append_trace_event,
    build_node_trace_event,
)
from app.service.agents.customer.tool_messages import (
    ToolExecutionContext,
    append_tool_result_messages,
    get_tool_call_args,
    get_tool_call_name,
)
from app.service.llm.intent import IntentType


class CustomerAgentNodes:
    """客户机器人 LangGraph 节点集合。"""

    def __init__(self, dependencies: CustomerGraphDependencies) -> None:
        self._dependencies = dependencies

    async def load_session_context(
        self,
        state: CustomerAgentState,
    ) -> CustomerAgentState:
        """加载会话上下文、RAG 上下文和工具上下文。"""
        memory_block = await load_customer_memory_block(
            summary_repo=self._dependencies.conversation_summary_repo,
            session_id=state["session"].id,
            customer_profile=state.get("customer_profile"),
        )
        messages, history_text = await prepare_ai_conversation_messages(
            session_mgr=self._dependencies.session_mgr,
            knowledge=self._dependencies.knowledge,
            session=state["session"],
            user_query=state.get("user_query", ""),
            intent=state.get("intent", IntentType.PRODUCT_CONSULTATION),
            timing=state.get("timing"),
            history=state.get("history"),
            history_text=state.get("history_text", ""),
            image_base64=state.get("image_base64"),
            customer_profile=memory_block.customer_profile,
            conversation_summary_text=memory_block.conversation_summary_text,
        )
        tool_context = ToolExecutionContext(
            session=state["session"],
            history_text=history_text,
            transfer_mgr=self._dependencies.transfer_mgr,
            session_repo=self._dependencies.session_repo,
            knowledge=self._dependencies.knowledge,
            youzan_client=self._dependencies.youzan_client,
        )
        return {
            **state,
            "messages": messages,
            "history_text": history_text,
            "memory_block": memory_block,
            "tool_context": tool_context,
            "has_image": bool(state.get("image_base64")),
            "fallback_reply": self._dependencies.fallback_reply,
            "timeout_reply": self._dependencies.timeout_reply,
            "failure_alerter": self._dependencies.failure_alerter,
            "first_llm_started_at": None,
            "tool_round": 0,
            "trace_events": [_build_memory_trace_event(memory_block)],
        }

    async def model_with_tools(
        self,
        state: CustomerAgentState,
    ) -> CustomerAgentState:
        """请求模型并记录本轮 finish_reason。"""
        tools_by_name = self._tools_by_name(state)
        llm_result = await request_customer_model_with_tools(
            CustomerModelRequest(
                messages=state["messages"],
                tools=list(tools_by_name.values()),
                timing=state.get("timing"),
                first_llm_started_at=state.get("first_llm_started_at"),
                has_image=state["has_image"],
                fallback_reply=state["fallback_reply"],
                failure_alerter=state["failure_alerter"],
            )
        )
        if llm_result.fallback_reply is not None:
            return {
                **state,
                "reply": llm_result.fallback_reply,
                "first_llm_started_at": llm_result.first_llm_started_at,
                "trace_events": append_trace_event(
                    state.get("trace_events"),
                    "model_with_tools",
                    finish_reason="fallback",
                ),
            }
        message = llm_result.message
        assert message is not None
        return {
            **state,
            "finish_reason": llm_result.finish_reason,
            "llm_message": message,
            "tools_by_name": tools_by_name,
            "first_llm_started_at": llm_result.first_llm_started_at,
            "trace_events": append_trace_event(
                state.get("trace_events"),
                "model_with_tools",
                finish_reason=llm_result.finish_reason,
            ),
        }

    async def execute_tools(self, state: CustomerAgentState) -> CustomerAgentState:
        """执行 LangChain customer tools 并追加 OpenAI tool 消息。"""
        message_count_before_tools = len(state["messages"])
        for tool_call in state["llm_message"].tool_calls or []:
            await self._execute_tool_call(tool_call, state)
        record_tool_context_budget_delta(
            state.get("timing"),
            state["messages"][message_count_before_tools:],
        )
        tool_round = state.get("tool_round", 0) + 1
        return {
            **state,
            "tool_round": tool_round,
            "trace_events": append_trace_event(
                state.get("trace_events"),
                "execute_tools",
                tool_round=tool_round,
            ),
        }

    async def finalize_reply(self, state: CustomerAgentState) -> CustomerAgentState:
        """生成最终回复并记录工具轮次。"""
        reply = state.get("reply", "")
        if not reply:
            message = state.get("llm_message")
            reply = str(message.content or "") if message is not None else ""
        record_tool_rounds(state.get("timing"), state.get("tool_round", 0))
        return {
            **state,
            "reply": reply,
            "trace_events": append_trace_event(
                state.get("trace_events"),
                "finalize_reply",
            ),
        }

    async def tool_round_limit(
        self,
        state: CustomerAgentState,
    ) -> CustomerAgentState:
        """工具轮次超限时返回超时兜底。"""
        record_tool_rounds(state.get("timing"), state.get("tool_round", 0))
        record_tool_round_limit(state.get("timing"))
        return {
            **state,
            "reply": state["timeout_reply"],
            "trace_events": append_trace_event(
                state.get("trace_events"),
                "tool_round_limit",
            ),
        }

    async def record_trace(self, state: CustomerAgentState) -> CustomerAgentState:
        """结束前补充 guard source。"""
        extend_guard_source_with_tool_outputs(
            state.get("timing"),
            state.get("messages", []),
        )
        return {
            **state,
            "trace_events": append_trace_event(
                state.get("trace_events"),
                "record_trace",
            ),
        }

    async def _execute_tool_call(
        self,
        tool_call: Any,
        state: CustomerAgentState,
    ) -> None:
        tool_name = get_tool_call_name(tool_call)
        tool_args = get_tool_call_args(tool_call)
        tool = self._tools_by_name(state).get(tool_name)
        if tool is None:
            result = json.dumps(
                {"status": "error", "message": f"未知工具: {tool_name}"},
                ensure_ascii=False,
            )
        else:
            result = await tool.ainvoke(tool_args)
        append_tool_result_messages(
            state["messages"],
            tool_call,
            tool_name,
            tool_args,
            str(result),
        )

    def _tools_by_name(self, state: CustomerAgentState) -> dict[str, Any]:
        tools_by_name = state.get("tools_by_name")
        if tools_by_name is not None:
            return tools_by_name
        return self._build_tools(state["tool_context"])

    def _build_tools(self, tool_context: ToolExecutionContext) -> dict[str, Any]:
        context = CustomerToolContext(
            session=tool_context.session,
            knowledge_retriever=tool_context.knowledge,
            youzan_client=tool_context.youzan_client,
            transfer_handler=build_transfer_handler(tool_context),
        )
        return {
            tool.name: tool
            for tool in build_tools("customer", customer_context=context)
        }


def route_after_model(state: CustomerAgentState) -> str:
    """根据模型返回决定继续工具轮次或结束。"""
    if state.get("reply"):
        return "finalize"
    if state.get("finish_reason") == "stop":
        return "finalize"
    if (
        state.get("finish_reason") == "tool_calls"
        and state.get("tool_round", 0) < CUSTOMER_TOOL_ROUND_LIMIT
    ):
        return "tools"
    return "limit"


def _build_memory_trace_event(memory_block: Any) -> dict[str, Any]:
    return build_node_trace_event(
        "load_session_context",
        memory={
            "conversation_summary": memory_block.has_conversation_summary,
            "customer_profile": memory_block.has_customer_profile,
        },
    )
