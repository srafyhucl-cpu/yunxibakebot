"""
MiMo / DeepSeek API 调用层。

封装 OpenAI SDK，提供异步聊天补全接口。
主力使用小米 MiMo API（兼容 OpenAI 格式），
DeepSeek 配置保留但已废弃。

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

# 全局单例客户端（MiMo 主力），避免重复创建连接
_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """获取或初始化 MiMo 异步客户端（单例模式）。"""
    global _client
    if _client is None:
        # trust_env=False 禁止读取系统代理环境变量
        # MiMo 使用 api-key 认证头（非标准 Bearer），通过 default_headers 传入
        _client = AsyncOpenAI(
            api_key=settings.MIMO_API_KEY,
            base_url=settings.MIMO_BASE_URL,
            timeout=settings.MIMO_TIMEOUT_SECONDS,
            http_client=httpx.AsyncClient(trust_env=False),
            default_headers={"api-key": settings.MIMO_API_KEY},
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
    调用 MiMo 聊天补全接口。

    参数：
        messages: 消息列表（system + user + assistant + tool）
        tools: Function Calling 工具定义
        model: 可选模型名（为空则使用默认 MIMO_CHAT_MODEL，多模态场景可传 VISION 模型）
    返回：
        ChatCompletion SDK 原生响应对象
    异常：
        LLMError: API 调用失败时抛出
    """
    client = get_client()
    resolved_model = model or settings.MIMO_CHAT_MODEL
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
        logger.error("MiMo API 调用失败(model=%s): %s", resolved_model, exc)
        raise LLMError(f"MiMo API 调用失败({resolved_model})") from exc

    return response


async def asr_transcribe(
    audio_base64: str,
    mime_type: str = "audio/wav",
    language: str = "zh",
) -> str:
    """
    调用 MiMo ASR 模型将语音转为文字。

    参数：
        audio_base64: 音频的 base64 编码字符串（不含 data URI 前缀）
        mime_type: 音频 MIME 类型（audio/wav 或 audio/mpeg）
        language: 语种代码（zh/en/auto）
    返回：
        识别出的文字内容
    异常：
        LLMError: ASR 调用失败时抛出
    """
    client = get_client()
    audio_data_url = f"data:{mime_type};base64,{audio_base64}"

    try:
        response = await client.chat.completions.create(
            model=settings.MIMO_ASR_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {"data": audio_data_url},
                        }
                    ],
                }
            ],
            extra_body={
                "asr_options": {"language": language},
            },
            max_tokens=1024,
            temperature=0,
        )
        text = response.choices[0].message.content or ""
        logger.info("ASR 识别完成 长度=%d 语言=%s", len(text), language)
        return text
    except Exception as exc:
        logger.error("MiMo ASR 调用失败: %s", exc)
        raise LLMError("MiMo ASR 调用失败") from exc
