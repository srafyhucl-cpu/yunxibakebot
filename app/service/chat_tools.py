"""ChatService 的工具调用执行边界。"""

import json
from dataclasses import dataclass
from typing import Any

from app.logger import setup_logger
from app.models.session import Session
from app.service.chat_transfer import HumanTransferContext, request_human_transfer
from app.service.llm.functions import dispatch_tool

logger = setup_logger()

TRANSFER_TOOL_NAME = "transfer_to_human"
TRANSFER_TOOL_DEFAULT_REASON = "用户通过工具请求转人工"
TRANSFER_TOOL_SUCCESS_MESSAGE = "已为您转接人工客服，请稍候"
TRANSFER_TOOL_ERROR_MESSAGE = "转接失败，请稍后重试"


@dataclass(frozen=True)
class ToolExecutionContext:
    session: Session
    history_text: str
    transfer_mgr: Any
    session_repo: Any
    knowledge: Any
    youzan_client: Any


def parse_tool_arguments(tool_name: str, raw_arguments: str) -> dict:
    try:
        parsed = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError as exc:
        logger.error("工具参数解析失败，跳过 tool=%s err=%s", tool_name, exc)
        return {}

    if isinstance(parsed, dict):
        return parsed

    logger.error("工具参数不是 JSON 对象，跳过 tool=%s args=%s", tool_name, parsed)
    return {}


async def process_tool_calls(
    tool_calls: list,
    messages: list[dict],
    context: ToolExecutionContext,
) -> None:
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        tool_args = parse_tool_arguments(tool_name, tool_call.function.arguments)
        logger.info("工具调用: %s args=%s", tool_name, tool_args)

        if tool_name == TRANSFER_TOOL_NAME:
            result = await _transfer_to_human(tool_args, context)
        else:
            result = await dispatch_tool(
                tool_name,
                tool_args,
                context.session,
                context.knowledge,
                context.youzan_client,
            )

        append_tool_result_messages(messages, tool_call, tool_name, tool_args, result)


async def _transfer_to_human(
    tool_args: dict,
    context: ToolExecutionContext,
) -> str:
    reason = tool_args.get("reason", TRANSFER_TOOL_DEFAULT_REASON)
    transfer_created = await request_human_transfer(
        HumanTransferContext(
            session=context.session,
            user_id=context.session.user_id,
            reason=reason,
            history_text=context.history_text,
            transfer_mgr=context.transfer_mgr,
            session_repo=context.session_repo,
        )
    )
    if transfer_created:
        return json.dumps(
            {"status": "success", "message": TRANSFER_TOOL_SUCCESS_MESSAGE},
            ensure_ascii=False,
        )
    return json.dumps(
        {"status": "error", "message": TRANSFER_TOOL_ERROR_MESSAGE},
        ensure_ascii=False,
    )


def append_tool_result_messages(
    messages: list[dict],
    tool_call: Any,
    tool_name: str,
    tool_args: dict,
    result: str,
) -> None:
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
