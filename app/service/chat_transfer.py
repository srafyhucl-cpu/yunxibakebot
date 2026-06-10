"""ChatService 的转人工请求边界。"""

from dataclasses import dataclass
from typing import Any

from app.logger import setup_logger
from app.models.session import Session, SessionStatus
from app.models.session_scope import mark_handoff_started

logger = setup_logger()

TRANSFER_SUMMARY_LENGTH = 200
TRANSFER_SUMMARY_LINE_LIMIT = 6
TRANSFER_SUMMARY_LINE_LENGTH = 80


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
        summary = build_transfer_summary(context.reason, context.history_text)
        await context.transfer_mgr.request_transfer(
            context.session.id,
            context.user_id,
            reason=context.reason,
            summary=summary,
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


def build_transfer_summary(reason: str, history_text: str) -> str:
    """构造给人工客服看的简明上下文摘要。"""
    parts: list[str] = []
    compact_reason = _compact_line(reason)
    if compact_reason:
        parts.append(f"转人工触发：{compact_reason}")

    recent_lines = [
        compact
        for compact in (_compact_line(line) for line in history_text.splitlines())
        if compact
    ][-TRANSFER_SUMMARY_LINE_LIMIT:]
    if recent_lines:
        parts.append("最近对话：")
        parts.extend(f"- {line}" for line in recent_lines)

    summary = "\n".join(parts).strip()
    if not summary:
        summary = "转人工触发：用户请求人工客服"
    return summary[-TRANSFER_SUMMARY_LENGTH:]


def _compact_line(text: str) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= TRANSFER_SUMMARY_LINE_LENGTH:
        return compact
    return compact[: TRANSFER_SUMMARY_LINE_LENGTH - 1] + "…"
