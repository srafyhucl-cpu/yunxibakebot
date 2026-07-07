"""ChatService 的 LLM 工具轮次边界。"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.service.chat_context_budget import record_tool_context_budget_delta
from app.service.chat_tools import ToolExecutionContext, process_tool_calls
from app.service.chat_llm_request import (
    LLM_FAILURE_REASON_KEY,
    LlmChoiceResult,
    LlmRequestContext,
    request_llm_choice,
    select_llm_model,
)
from app.service.llm.functions import MAX_TOOL_ROUNDS

__all__ = [
    "LlmChoiceResult",
    "LlmRequestContext",
    "LlmToolLoopContext",
    "complete_llm_tool_conversation",
    "request_llm_choice",
    "select_llm_model",
]

LLM_FAILURE_REASON_TOOL_ROUND_LIMIT = "tool_round_limit"


@dataclass(frozen=True)
class LlmToolLoopContext:
    messages: list[dict]
    timing: dict | None
    has_image: bool
    fallback_reply: str
    timeout_reply: str
    failure_alerter: Callable[[str], Awaitable[None]]
    tool_context: ToolExecutionContext


async def complete_llm_tool_conversation(context: LlmToolLoopContext) -> str:
    tool_round = 0
    first_llm_started_at: float | None = None

    while tool_round <= MAX_TOOL_ROUNDS:
        llm_result = await request_llm_choice(
            LlmRequestContext(
                messages=context.messages,
                timing=context.timing,
                first_llm_started_at=first_llm_started_at,
                has_image=context.has_image,
                fallback_reply=context.fallback_reply,
                failure_alerter=context.failure_alerter,
            )
        )
        first_llm_started_at = llm_result.first_llm_started_at
        if llm_result.fallback_reply is not None:
            return llm_result.fallback_reply

        choice = llm_result.choice
        msg = llm_result.message
        assert choice is not None
        assert msg is not None

        finish_reason = choice.finish_reason or "stop"

        if finish_reason == "stop":
            _record_tool_rounds(context.timing, tool_round)
            return msg.content or ""

        if finish_reason == "tool_calls" and tool_round < MAX_TOOL_ROUNDS:
            message_count_before_tools = len(context.messages)
            await process_tool_calls(
                msg.tool_calls or [],
                context.messages,
                context.tool_context,
            )
            record_tool_context_budget_delta(
                context.timing,
                context.messages[message_count_before_tools:],
            )
            tool_round += 1
            continue

        break

    _record_tool_rounds(context.timing, tool_round)
    _record_tool_round_limit(context.timing)
    return context.timeout_reply


def _record_tool_rounds(timing: dict | None, tool_round: int) -> None:
    if timing is not None:
        timing["tool_rounds"] = tool_round


def _record_tool_round_limit(timing: dict | None) -> None:
    if timing is not None:
        timing[LLM_FAILURE_REASON_KEY] = LLM_FAILURE_REASON_TOOL_ROUND_LIMIT
