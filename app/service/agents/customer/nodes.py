"""客户机器人 LangGraph 节点。"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
import json

from app.models.customer_profile import CustomerProfile
from app.models.session import Session
from app.service.agents.customer.state import CustomerAgentState
from app.service.agents.customer.constants import CUSTOMER_TOOL_ROUND_LIMIT
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
from app.service.chat_llm_request import (
    LlmRequestContext,
    request_llm_choice,
)
from app.service.agents.customer.tool_messages import (
    ToolExecutionContext,
    append_tool_result_messages,
    parse_tool_arguments,
)
from app.service.conversation_summary_memory import (
    ConversationSummaryReader,
    load_active_conversation_summary_text,
)
from app.service.knowledge_retriever import KnowledgeRetriever
from app.service.llm.intent import IntentType
from app.service.session_manager import SessionManager
from app.service.transfer_manager import TransferManager
from app.service.youzan.client import YouzanClient


@dataclass(frozen=True)
class CustomerGraphDependencies:
    """客户机器人 graph 运行依赖。"""

    session_mgr: SessionManager
    knowledge: KnowledgeRetriever
    transfer_mgr: TransferManager
    session_repo: Any
    youzan_client: YouzanClient
    fallback_reply: str
    timeout_reply: str
    failure_alerter: Callable[[str], Awaitable[None]]
    conversation_summary_repo: ConversationSummaryReader | None = None


@dataclass(frozen=True)
class CustomerGraphRequest:
    """客户机器人 graph 单次请求。"""

    session: Session
    user_query: str = ""
    intent: IntentType = IntentType.PRODUCT_CONSULTATION
    timing: dict[str, Any] | None = None
    history: list[dict] | None = None
    history_text: str = ""
    image_base64: str | None = None
    customer_profile: CustomerProfile | None = None


class CustomerAgentNodes:
    """客户机器人 LangGraph 节点集合。"""

    def __init__(self, dependencies: CustomerGraphDependencies) -> None:
        self._dependencies = dependencies
        self._tools_by_name: dict[str, Any] | None = None

    async def load_session_context(
        self,
        state: CustomerAgentState,
    ) -> CustomerAgentState:
        """加载会话上下文、RAG 上下文和工具上下文。"""
        conversation_summary_text = await load_active_conversation_summary_text(
            self._dependencies.conversation_summary_repo,
            state["session"].id,
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
            customer_profile=state.get("customer_profile"),
            conversation_summary_text=conversation_summary_text,
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
            "tool_context": tool_context,
            "has_image": bool(state.get("image_base64")),
            "fallback_reply": self._dependencies.fallback_reply,
            "timeout_reply": self._dependencies.timeout_reply,
            "failure_alerter": self._dependencies.failure_alerter,
            "first_llm_started_at": None,
            "tool_round": 0,
            "trace_events": [{"node": "load_session_context"}],
        }

    async def model_with_tools(
        self,
        state: CustomerAgentState,
    ) -> CustomerAgentState:
        """请求模型并记录本轮 finish_reason。"""
        llm_result = await request_llm_choice(
            LlmRequestContext(
                messages=state["messages"],
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
                "trace_events": [
                    *state.get("trace_events", []),
                    {"node": "model_with_tools", "finish_reason": "fallback"},
                ],
            }
        choice = llm_result.choice
        message = llm_result.message
        assert choice is not None
        assert message is not None
        finish_reason = choice.finish_reason or "stop"
        return {
            **state,
            "finish_reason": finish_reason,
            "llm_message": message,
            "first_llm_started_at": llm_result.first_llm_started_at,
            "trace_events": [
                *state.get("trace_events", []),
                {"node": "model_with_tools", "finish_reason": finish_reason},
            ],
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
            "trace_events": [
                *state.get("trace_events", []),
                {"node": "execute_tools", "tool_round": tool_round},
            ],
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
            "trace_events": [
                *state.get("trace_events", []),
                {"node": "finalize_reply"},
            ],
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
            "trace_events": [
                *state.get("trace_events", []),
                {"node": "tool_round_limit"},
            ],
        }

    async def record_trace(self, state: CustomerAgentState) -> CustomerAgentState:
        """结束前补充 guard source。"""
        extend_guard_source_with_tool_outputs(
            state.get("timing"),
            state.get("messages", []),
        )
        return {
            **state,
            "trace_events": [
                *state.get("trace_events", []),
                {"node": "record_trace"},
            ],
        }

    async def _execute_tool_call(
        self,
        tool_call: Any,
        state: CustomerAgentState,
    ) -> None:
        tool_name = tool_call.function.name
        tool_args = parse_tool_arguments(tool_name, tool_call.function.arguments)
        tool = self._tools(state["tool_context"]).get(tool_name)
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

    def _tools(self, tool_context: ToolExecutionContext) -> dict[str, Any]:
        if self._tools_by_name is None:
            context = CustomerToolContext(
                session=tool_context.session,
                knowledge_retriever=tool_context.knowledge,
                youzan_client=tool_context.youzan_client,
                transfer_handler=build_transfer_handler(tool_context),
            )
            self._tools_by_name = {
                tool.name: tool
                for tool in build_tools("customer", customer_context=context)
            }
        return self._tools_by_name


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


def initial_customer_state(request: CustomerGraphRequest) -> CustomerAgentState:
    """把请求转换为 LangGraph 初始状态。"""
    return {
        "session": request.session,
        "user_query": request.user_query,
        "intent": request.intent,
        "timing": request.timing,
        "history": request.history,
        "history_text": request.history_text,
        "image_base64": request.image_base64,
        "customer_profile": request.customer_profile,
    }
