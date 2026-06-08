"""ChatService 的回复后处理与埋点边界。"""

import json
from typing import Any

from app.logger import setup_logger
from app.models.session import Session
from app.service.llm.intent import IntentType
from app.service.llm.soothe import apply_soothe, needs_soothe
from app.utils import now_str

logger = setup_logger()


def postprocess_reply(reply: str | None, user_content: str) -> str | None:
    if not reply:
        return reply

    cleaned_reply = reply.replace("**", "").replace("*", "").replace("__", "")
    if needs_soothe(user_content):
        return apply_soothe(cleaned_reply)
    return cleaned_reply


async def record_reply_latency(
    analytics_repo: Any,
    session: Session,
    user_id: str,
    channel: str,
    intent: IntentType,
    intent_ms: int,
    timing: dict,
    loop_ms: int,
    total_ms: int,
) -> None:
    try:
        await analytics_repo.add_event(
            session_id=session.id,
            buyer_id=user_id,
            event_type="reply_latency",
            event_source="chat_pipeline",
            ref_id=session.id,
            meta_data=json.dumps(
                {
                    "intent": intent.name,
                    "intent_ms": intent_ms,
                    "rag_ms": timing.get("rag_ms"),
                    "llm_ms": timing.get("llm_ms"),
                    "tool_rounds": timing.get("tool_rounds", 0),
                    "loop_ms": loop_ms,
                    "total_ms": total_ms,
                    "channel": channel,
                }
            ),
            created_at=now_str(),
        )
    except Exception as exc:
        logger.warning("回复延迟埋点失败: %s", exc)
