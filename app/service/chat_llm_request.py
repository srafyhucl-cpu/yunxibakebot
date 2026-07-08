"""LLM 单次请求与兜底处理。"""

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.exceptions import LLMError
from app.logger import setup_logger
from app.service.agents.tools.customer import build_customer_openai_tool_definitions
from app.service.llm.client import chat_completion as llm_chat

logger = setup_logger()

LLM_FAILURE_REASON_KEY = "llm_failure_reason"
LLM_FAILURE_REASON_API_ERROR = "llm_api_error"
LLM_FAILURE_REASON_RESPONSE_PARSE = "llm_response_parse_error"


@dataclass(frozen=True)
class LlmChoiceResult:
    choice: Any | None
    message: Any | None
    fallback_reply: str | None = None
    first_llm_started_at: float | None = None


@dataclass(frozen=True)
class LlmRequestContext:
    messages: list[dict]
    timing: dict | None
    first_llm_started_at: float | None
    has_image: bool
    fallback_reply: str
    failure_alerter: Callable[[str], Awaitable[None]]


def select_llm_model(has_image: bool) -> str:
    if not has_image:
        return ""
    return settings.MIMO_VISION_MODEL or settings.MIMO_CHAT_MODEL


async def request_llm_choice(context: LlmRequestContext) -> LlmChoiceResult:
    first_llm_started_at = _ensure_llm_started_at(context.first_llm_started_at)
    try:
        response = await _request_llm_response(context.messages, context.has_image)
        _record_llm_latency(context.timing, first_llm_started_at)
        choice = response.choices[0]
        return LlmChoiceResult(
            choice=choice,
            message=choice.message,
            first_llm_started_at=first_llm_started_at,
        )
    except LLMError:
        _record_llm_failure_reason(context.timing, LLM_FAILURE_REASON_API_ERROR)
        logger.error("LLM 调用失败，返回兜底回复")
        await context.failure_alerter("LLMError: chat.py handle_message 返回兜底回复")
        return _fallback_choice_result(context.fallback_reply, first_llm_started_at)
    except (KeyError, IndexError) as exc:
        _record_llm_failure_reason(context.timing, LLM_FAILURE_REASON_RESPONSE_PARSE)
        logger.error("LLM 响应解析失败，返回兜底回复: %s", exc)
        await context.failure_alerter(f"LLM 响应解析失败: {exc}")
        return _fallback_choice_result(context.fallback_reply, first_llm_started_at)


def _ensure_llm_started_at(first_llm_started_at: float | None) -> float:
    if first_llm_started_at is not None:
        return first_llm_started_at
    return time.monotonic()


async def _request_llm_response(messages: list[dict], has_image: bool) -> Any:
    return await llm_chat(
        messages,
        tools=build_customer_openai_tool_definitions(),
        model=select_llm_model(has_image),
    )


def _record_llm_latency(timing: dict | None, first_llm_started_at: float) -> None:
    if timing is not None and "llm_ms" not in timing:
        timing["llm_ms"] = round((time.monotonic() - first_llm_started_at) * 1000)


def _record_llm_failure_reason(timing: dict | None, reason: str) -> None:
    if timing is not None:
        timing[LLM_FAILURE_REASON_KEY] = reason


def _fallback_choice_result(
    fallback_reply: str,
    first_llm_started_at: float,
) -> LlmChoiceResult:
    return LlmChoiceResult(
        choice=None,
        message=None,
        fallback_reply=fallback_reply,
        first_llm_started_at=first_llm_started_at,
    )
