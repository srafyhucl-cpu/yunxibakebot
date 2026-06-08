"""ChatService 的 LLM 调用边界。"""

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.exceptions import LLMError
from app.logger import setup_logger
from app.service.llm.client import chat_completion as llm_chat
from app.service.llm.functions import FUNCTION_DEFINITIONS

logger = setup_logger()


@dataclass(frozen=True)
class LlmChoiceResult:
    choice: Any | None
    message: Any | None
    fallback_reply: str | None = None
    first_llm_started_at: float | None = None


def select_llm_model(has_image: bool) -> str:
    if not has_image:
        return ""
    return settings.MIMO_VISION_MODEL or settings.MIMO_CHAT_MODEL


async def request_llm_choice(
    messages: list[dict],
    timing: dict | None,
    first_llm_started_at: float | None,
    has_image: bool,
    fallback_reply: str,
    failure_alerter: Callable[[str], Awaitable[None]],
) -> LlmChoiceResult:
    try:
        if first_llm_started_at is None:
            first_llm_started_at = time.monotonic()
        response = await llm_chat(
            messages,
            tools=FUNCTION_DEFINITIONS,
            model=select_llm_model(has_image),
        )
        if timing is not None and "llm_ms" not in timing:
            timing["llm_ms"] = round((time.monotonic() - first_llm_started_at) * 1000)
        choice = response.choices[0]
        return LlmChoiceResult(
            choice=choice,
            message=choice.message,
            first_llm_started_at=first_llm_started_at,
        )
    except LLMError:
        logger.error("LLM 调用失败，返回兜底回复")
        await failure_alerter("LLMError: chat.py handle_message 返回兜底回复")
        return LlmChoiceResult(
            choice=None,
            message=None,
            fallback_reply=fallback_reply,
            first_llm_started_at=first_llm_started_at,
        )
    except (KeyError, IndexError) as exc:
        logger.error("LLM 响应解析失败，返回兜底回复: %s", exc)
        await failure_alerter(f"LLM 响应解析失败: {exc}")
        return LlmChoiceResult(
            choice=None,
            message=None,
            fallback_reply=fallback_reply,
            first_llm_started_at=first_llm_started_at,
        )
