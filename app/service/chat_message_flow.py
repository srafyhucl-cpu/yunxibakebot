"""用户消息处理主流程边界。"""

import time
from dataclasses import dataclass

from app.logger import setup_logger
from app.models.message import Message, MessageRole
from app.models.session import Session, SessionCreate, SessionStatus
from app.repository.analytics_repo import AnalyticsRepo
from app.repository.message_repo import MessageRepo
from app.repository.session_repo import SessionRepo
from app.service.chat_ai_loop import (
    AiConversationLoopDependencies,
    AiConversationLoopRequest,
    run_ai_conversation_loop,
)
from app.service.chat_intent import IntentDetectionResult, detect_intent_with_timing
from app.service.chat_reply import (
    postprocess_reply,
    record_reply_latency,
    save_assistant_reply,
)
from app.service.chat_transfer import HumanTransferContext, request_human_transfer
from app.service.llm.intent_types import is_transfer_intent
from app.service.session_manager import SessionManager
from app.service.transfer_manager import TransferManager

logger = setup_logger()


@dataclass(frozen=True)
class ChatMessageFlowDependencies:
    session_mgr: SessionManager
    session_repo: SessionRepo
    message_repo: MessageRepo
    transfer_mgr: TransferManager
    analytics_repo: AnalyticsRepo
    ai_loop_dependencies: AiConversationLoopDependencies
    fallback_reply: str
    transfer_reply: str


@dataclass(frozen=True)
class ChatMessageRequest:
    channel: str
    user_id: str
    content: str
    staff_id: str = ""
    channel_msg_id: str = ""
    image_base64: str | None = None


async def handle_chat_message(
    dependencies: ChatMessageFlowDependencies,
    request: ChatMessageRequest,
) -> str | None:
    if await is_duplicate_message(dependencies.message_repo, request.channel_msg_id):
        logger.debug("消息已处理，跳过: %s", request.channel_msg_id)
        return None

    session = await prepare_session_and_save_user_message(dependencies, request)
    if is_human_service_session(session):
        logger.info("会话 %s 处于人工服务状态，跳过 AI", session.id)
        return None

    intent_result = await detect_intent_with_timing(
        dependencies.session_mgr, session, request.content
    )
    if is_transfer_intent(intent_result.intent):
        return await handle_transfer_intent(
            dependencies=dependencies,
            session=session,
            user_id=request.user_id,
            reason=request.content,
            history_text=intent_result.history_text,
        )

    return await complete_ai_reply(dependencies, request, session, intent_result)


async def is_duplicate_message(
    message_repo: MessageRepo,
    channel_msg_id: str,
) -> bool:
    return bool(channel_msg_id and await message_repo.exists(channel_msg_id))


async def prepare_session_and_save_user_message(
    dependencies: ChatMessageFlowDependencies,
    request: ChatMessageRequest,
) -> Session:
    session = await dependencies.session_repo.get_or_create(
        SessionCreate(
            id="",
            channel=request.channel,
            user_id=request.user_id,
            staff_id=request.staff_id,
        ),
    )
    user_msg = Message(
        id="",
        session_id=session.id,
        role=MessageRole.USER,
        content=request.content,
        channel_msg_id=request.channel_msg_id,
    )
    await dependencies.message_repo.save(user_msg)
    return session


def is_human_service_session(session: Session) -> bool:
    return session.status in (
        SessionStatus.TRANSFER_PENDING,
        SessionStatus.HUMAN_SERVICE,
    )


async def handle_transfer_intent(
    dependencies: ChatMessageFlowDependencies,
    session: Session,
    user_id: str,
    reason: str,
    history_text: str,
) -> str:
    transfer_created = await request_human_transfer(
        HumanTransferContext(
            session=session,
            user_id=user_id,
            reason=reason,
            history_text=history_text,
            transfer_mgr=dependencies.transfer_mgr,
            session_repo=dependencies.session_repo,
        )
    )
    if not transfer_created:
        return dependencies.fallback_reply

    await save_assistant_reply(
        dependencies.message_repo, session.id, dependencies.transfer_reply
    )
    return dependencies.transfer_reply


async def complete_ai_reply(
    dependencies: ChatMessageFlowDependencies,
    request: ChatMessageRequest,
    session: Session,
    intent_result: IntentDetectionResult,
) -> str | None:
    timing: dict = {}
    reply = await run_ai_conversation_loop(
        dependencies.ai_loop_dependencies,
        AiConversationLoopRequest(
            session=session,
            user_query=request.content,
            intent=intent_result.intent,
            timing=timing,
            history=intent_result.history,
            history_text=intent_result.history_text,
            image_base64=request.image_base64,
        ),
    )
    finished_at = time.monotonic()
    loop_ms = round((finished_at - intent_result.finished_at) * 1000)
    total_ms = round((finished_at - intent_result.started_at) * 1000)

    reply = postprocess_reply(reply, user_content=request.content)
    await save_assistant_reply(dependencies.message_repo, session.id, reply)
    await record_reply_latency(
        analytics_repo=dependencies.analytics_repo,
        session=session,
        user_id=request.user_id,
        channel=request.channel,
        intent=intent_result.intent,
        intent_ms=intent_result.intent_ms,
        timing=timing,
        loop_ms=loop_ms,
        total_ms=total_ms,
    )
    return reply
