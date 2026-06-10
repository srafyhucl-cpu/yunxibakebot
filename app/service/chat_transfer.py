"""ChatService 的转人工请求边界。"""

from dataclasses import dataclass
from typing import Any

from app.logger import setup_logger
from app.models.session import Session, SessionStatus
from app.models.session_scope import mark_handoff_started

logger = setup_logger()

TRANSFER_SUMMARY_LENGTH = 200


@dataclass(frozen=True)
class HumanTransferContext:
    session: Session
    user_id: str
    reason: str
    history_text: str
    transfer_mgr: Any
    session_repo: Any


async def request_human_transfer(context: HumanTransferContext) -> bool:
    try:
        await context.transfer_mgr.request_transfer(
            context.session.id,
            context.user_id,
            reason=context.reason,
            summary=context.history_text[-TRANSFER_SUMMARY_LENGTH:],
        )
        await context.session_repo.update_status(
            context.session.id, SessionStatus.TRANSFER_PENDING
        )
        if hasattr(context.session_repo, "update_extra"):
            await context.session_repo.update_extra(
                context.session.id,
                mark_handoff_started(context.session.extra_info),
            )
        return True
    except Exception as exc:
        logger.error("创建转人工工单失败: session=%s err=%s", context.session.id, exc)
        return False
