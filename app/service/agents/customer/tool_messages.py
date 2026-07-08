"""客户机器人 OpenAI tool message 辅助。"""

import json
from dataclasses import dataclass
from typing import Any

from app.logger import setup_logger
from app.models.session import Session

logger = setup_logger()


@dataclass(frozen=True)
class ToolExecutionContext:
    """客户工具执行所需上下文。"""

    session: Session
    history_text: str
    transfer_mgr: Any
    session_repo: Any
    knowledge: Any
    youzan_client: Any


def parse_tool_arguments(tool_name: str, raw_arguments: str) -> dict:
    """解析模型返回的 tool arguments。"""
    try:
        parsed = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError as exc:
        logger.error("工具参数解析失败，跳过 tool=%s err=%s", tool_name, exc)
        return {}

    if isinstance(parsed, dict):
        return parsed

    logger.error("工具参数不是 JSON 对象，跳过 tool=%s args=%s", tool_name, parsed)
    return {}


def append_tool_result_messages(
    messages: list[dict],
    tool_call: Any,
    tool_name: str,
    tool_args: dict,
    result: str,
) -> None:
    """追加 assistant tool_call 和 tool result 消息。"""
    messages.append(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(tool_args, ensure_ascii=False),
                    },
                }
            ],
        }
    )
    messages.append(
        {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result,
        }
    )
