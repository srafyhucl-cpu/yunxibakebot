"""
DeepSeek API 调用层。

封装 OpenAI SDK，提供异步聊天补全接口。
所有 LLM 调用异常统一抛出 LLMError，由上层处理降级兜底。
"""

from collections.abc import Sequence

from openai import AsyncOpenAI

from app.config import settings
from app.exceptions import LLMError
from app.logger import setup_logger

logger = setup_logger()

# 聊天补全接口的默认 token 上限
DEFAULT_CHAT_MAX_TOKENS = 2048

# 全局单例客户端，避免重复创建连接
_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """获取或初始化 DeepSeek 异步客户端（单例模式）。"""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=settings.DEEPSEEK_TIMEOUT_SECONDS,
        )
    return _client


async def chat_completion(
    messages: Sequence[dict],
    tools: list | None = None,
    temperature: float = 0.7,
    max_tokens: int = DEFAULT_CHAT_MAX_TOKENS,
) -> str:
    """
    调用 DeepSeek 聊天补全接口。

    参数：
        messages: 消息列表（system + user + assistant + tool）
        tools: Function Calling 工具定义
    返回：
        LLM 原始响应的 JSON 字符串
    异常：
        LLMError: API 调用失败时抛出
    """
    client = get_client()
    kwargs: dict = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        kwargs["tools"] = tools

    try:
        response = await client.chat.completions.create(**kwargs)
    except Exception as exc:
        logger.error("DeepSeek API 调用失败: %s", exc)
        raise LLMError("DeepSeek API 调用失败") from exc

    return response.model_dump_json()
