"""LangChain 消息转换工具。"""

from typing import Any


def to_langchain_messages(messages: list[dict]) -> list[Any]:
    """把项目内 OpenAI 字典消息转换为 LangChain 消息。"""
    from langchain_core.messages import convert_to_messages

    return list(convert_to_messages(messages))
