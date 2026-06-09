"""AI 对话循环编排边界。"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.models.session import Session
from app.models.customer_profile import CustomerProfile
from app.repository.session_repo import SessionRepo
from app.service.chat_context import prepare_ai_conversation_messages
from app.service.chat_llm import LlmToolLoopContext, complete_llm_tool_conversation
from app.service.chat_tools import ToolExecutionContext
from app.service.knowledge_retriever import KnowledgeRetriever
from app.service.llm.intent import IntentType
from app.service.session_manager import SessionManager
from app.service.transfer_manager import TransferManager
from app.service.youzan.client import YouzanClient


@dataclass(frozen=True)
class AiConversationLoopDependencies:
    session_mgr: SessionManager
    knowledge: KnowledgeRetriever
    transfer_mgr: TransferManager
    session_repo: SessionRepo
    youzan_client: YouzanClient
    fallback_reply: str
    timeout_reply: str
    failure_alerter: Callable[[str], Awaitable[None]]


@dataclass(frozen=True)
class AiConversationLoopRequest:
    session: Session
    user_query: str = ""
    intent: IntentType = IntentType.PRODUCT_CONSULTATION
    timing: dict | None = None
    history: list[dict] | None = None
    history_text: str = ""
    image_base64: str | None = None
    customer_profile: CustomerProfile | None = None


async def run_ai_conversation_loop(
    dependencies: AiConversationLoopDependencies,
    request: AiConversationLoopRequest,
) -> str | None:
    messages, history_text = await prepare_ai_conversation_messages(
        session_mgr=dependencies.session_mgr,
        knowledge=dependencies.knowledge,
        session=request.session,
        user_query=request.user_query,
        intent=request.intent,
        timing=request.timing,
        history=request.history,
        history_text=request.history_text,
        image_base64=request.image_base64,
        customer_profile=request.customer_profile,
    )

    reply = await complete_llm_tool_conversation(
        LlmToolLoopContext(
            messages=messages,
            timing=request.timing,
            has_image=bool(request.image_base64),
            fallback_reply=dependencies.fallback_reply,
            timeout_reply=dependencies.timeout_reply,
            failure_alerter=dependencies.failure_alerter,
            tool_context=ToolExecutionContext(
                session=request.session,
                history_text=history_text,
                transfer_mgr=dependencies.transfer_mgr,
                session_repo=dependencies.session_repo,
                knowledge=dependencies.knowledge,
                youzan_client=dependencies.youzan_client,
            ),
        )
    )
    _extend_guard_source_with_tool_outputs(request.timing, messages)
    return reply


def _extend_guard_source_with_tool_outputs(
    timing: dict | None,
    messages: list[dict],
) -> None:
    if timing is None:
        return
    tool_outputs = [
        str(message.get("content", ""))
        for message in messages
        if message.get("role") == "tool"
    ]
    if tool_outputs:
        existing = str(timing.get("guard_source_text") or "")
        timing["guard_source_text"] = "\n".join([existing, *tool_outputs]).strip()
