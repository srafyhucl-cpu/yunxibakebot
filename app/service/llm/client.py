"""
DeepSeek API 调用层。

封装 OpenAI SDK，提供异步聊天补全接口。
所有 LLM 调用异常统一抛出 LLMError，由上层处理降级兜底。
"""

from collections.abc import Sequence

from openai.types.chat import ChatCompletion

import httpx
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
        # trust_env=False 禁止读取系统代理环境变量，避免无效端口导致请求失败
        _client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=settings.DEEPSEEK_TIMEOUT_SECONDS,
            http_client=httpx.AsyncClient(trust_env=False),
        )
    return _client


async def chat_completion(
    messages: Sequence[dict],
    tools: list | None = None,
    temperature: float = 0.7,
    max_tokens: int = DEFAULT_CHAT_MAX_TOKENS,
    model: str = "",
) -> ChatCompletion:
    """
    调用 DeepSeek 聊天补全接口。

    参数：
        messages: 消息列表（system + user + assistant + tool）
        tools: Function Calling 工具定义
        model: 可选模型名（为空则使用默认 DEEPSEEK_MODEL，多模态场景可传 VISION 模型）
    返回：
        ChatCompletion SDK 原生响应对象
    异常：
        LLMError: API 调用失败时抛出
    """
    client = get_client()
    # 优先使用传入的模型，否则回退到配置的视觉模型或默认模型
    resolved_model = model or settings.DEEPSEEK_MODEL
    kwargs: dict = {
        "model": resolved_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        kwargs["tools"] = tools

    try:
        response = await client.chat.completions.create(**kwargs)
    except Exception as exc:
        logger.error("DeepSeek API 调用失败(model=%s): %s", resolved_model, exc)
        raise LLMError("DeepSeek API 调用失败") from exc

    return response
