"""LangChain 聊天模型工厂。"""

from typing import Any, Literal

import httpx

from app.config import settings

LLMProvider = Literal["mimo", "deepseek"]


def get_langchain_chat_model(
    *,
    provider: LLMProvider = "mimo",
    model: str = "",
    temperature: float = 0.0,
    timeout_seconds: float | None = None,
) -> Any:
    """延迟构造 LangChain ChatOpenAI，避免应用启动阶段加载重依赖。"""
    from langchain_openai import ChatOpenAI

    if provider == "mimo":
        return ChatOpenAI(
            api_key=settings.MIMO_API_KEY,
            base_url=settings.MIMO_BASE_URL,
            model=model or settings.MIMO_CHAT_MODEL,
            temperature=temperature,
            timeout=timeout_seconds or settings.MIMO_TIMEOUT_SECONDS,
            http_client=httpx.Client(trust_env=False),
            http_async_client=httpx.AsyncClient(trust_env=False),
            default_headers={"api-key": settings.MIMO_API_KEY},
        )

    return ChatOpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        model=model or settings.DEEPSEEK_MODEL,
        temperature=temperature,
        timeout=timeout_seconds or settings.DEEPSEEK_TIMEOUT_SECONDS,
        http_client=httpx.Client(trust_env=False),
        http_async_client=httpx.AsyncClient(trust_env=False),
    )
