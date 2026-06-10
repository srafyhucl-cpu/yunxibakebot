"""Offline customer memory consolidation agent."""

import json
from dataclasses import dataclass

from app.config import settings
from app.exceptions import LLMError
from app.logger import setup_logger
from app.models.customer_profile import (
    CustomerProfile,
    CustomerProfileUpsert,
    MemoryConsentStatus,
)
from app.models.session import Session
from app.models.session_scope import SessionScopeSnapshot, snapshot_session_scope
from app.repository.customer_profile_repo import CustomerProfileRepo
from app.repository.message_repo import MessageRepo
from app.repository.offline_session_repo import OfflineSessionRepo
from app.service.llm.client import chat_completion as llm_chat
from app.service.offline.agent_shared import format_dialog

logger = setup_logger()

MEMORY_SYSTEM_PROMPT = (
    "你是芸熙烘焙顾客画像整理助手。只输出 JSON："
    '{"display_name": "", "preferences": {}, "order_summary": {}, '
    '"special_dates": [], "allergens": [], "consent_status": "unknown"}。'
    "只抽取对后续服务有帮助的偏好、最近订单摘要、特殊日期和过敏提醒；"
    "不要保存电话、地址等隐私。"
    "生日、结婚纪念日、周年纪念等特殊日期很关键，但只记录顾客主动明确提到的事实；"
    "special_dates 是数组，允许同时记录多个家人的生日和多个纪念日，不要只保留一条；"
    "每项建议包含 type/date/date_known/person/usage/evidence，"
    "日期不确定时 date 为空且 date_known=false，不要推测。"
    "过敏信息只能作为提醒核对事实，不能写成能否食用的结论。"
    "如果 session_scope 是 bot_then_handoff_partial，说明转人工后的人工对话不完整可见；"
    "此时不能把机器人阶段的意向写成最终确认事实。"
    "如果 human_messages_available 为 true，可将带有 [人工客服] 标记的消息视为人工阶段可见材料。"
)

ALLOWED_CONSENT_STATUS = {
    MemoryConsentStatus.UNKNOWN.value,
    MemoryConsentStatus.GRANTED.value,
    MemoryConsentStatus.REVOKED.value,
}


@dataclass
class ParsedCustomerMemory:
    """Customer memory parsed from the LLM response."""

    display_name: str
    preferences_json: str
    order_summary_json: str
    special_dates_json: str
    allergens_json: str
    consent_status: str


class MemoryAgent:
    """Consolidate recent finished sessions into long-term customer memory."""

    def __init__(
        self,
        session_repo: OfflineSessionRepo,
        message_repo: MessageRepo,
        profile_repo: CustomerProfileRepo,
        max_sessions: int = 200,
        reviewer_model: str = "",
    ) -> None:
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._profile_repo = profile_repo
        self._max_sessions = max_sessions
        self._reviewer_model = reviewer_model or settings.MIMO_CHAT_MODEL

    async def run(self) -> list[CustomerProfile]:
        """Run one memory consolidation pass."""
        sessions = await self._session_repo.list_memory_candidates(self._max_sessions)
        profiles: list[CustomerProfile] = []
        for session in sessions:
            try:
                messages = await self._message_repo.get_by_session(session.id)
                if not messages:
                    continue
                scope = snapshot_session_scope(session.extra_info)
                parsed = await self._extract_memory(messages, scope)
                profiles.append(await self._save_profile(session, parsed, scope))
            except Exception as exc:
                logger.error("离线记忆固化失败 session=%s err=%s", session.id, exc)
        return profiles

    async def _extract_memory(
        self,
        messages: list,
        scope: SessionScopeSnapshot,
    ) -> ParsedCustomerMemory:
        response = await llm_chat(
            [
                {"role": "system", "content": MEMORY_SYSTEM_PROMPT},
                {"role": "user", "content": _build_memory_input(messages, scope)},
            ],
            tools=None,
            temperature=0,
            max_tokens=768,
            model=self._reviewer_model,
        )
        content = response.choices[0].message.content or "{}"
        return _parse_memory_json(content)

    async def _save_profile(
        self,
        session: Session,
        memory: ParsedCustomerMemory,
        scope: SessionScopeSnapshot,
    ) -> CustomerProfile:
        existing = await self._profile_repo.get(session.channel, session.user_id)
        return await self._profile_repo.upsert(
            CustomerProfileUpsert(
                channel=session.channel,
                user_id=session.user_id,
                display_name=memory.display_name
                or _existing_value(existing, "display_name"),
                preferences_json=_memory_value(
                    memory.preferences_json,
                    _existing_value(existing, "preferences_json"),
                    "{}",
                ),
                order_summary_json=_memory_value(
                    memory.order_summary_json,
                    _existing_value(existing, "order_summary_json"),
                    "{}",
                ),
                special_dates_json=_merge_json_lists(
                    memory.special_dates_json,
                    _existing_value(existing, "special_dates_json"),
                ),
                allergens_json=_memory_value(
                    memory.allergens_json,
                    _existing_value(existing, "allergens_json"),
                    "[]",
                ),
                consent_status=memory.consent_status,
                source_evidence_json=json.dumps(
                    {
                        "session_ids": [session.id],
                        "session_scope": scope.session_scope,
                        "handoff_occurred": scope.handoff_occurred,
                        "human_messages_available": scope.human_messages_available,
                    },
                    ensure_ascii=False,
                ),
                last_interaction_at=session.updated_at or session.created_at,
            )
        )


def _existing_value(profile: CustomerProfile | None, field_name: str) -> str:
    """Read a string field from an existing profile."""
    return str(getattr(profile, field_name, "")) if profile is not None else ""


def _memory_value(new_value: str, existing_value: str, empty_value: str) -> str:
    """Keep existing memory when the current extraction is empty."""
    return existing_value if new_value == empty_value and existing_value else new_value


def _merge_json_lists(new_value: str, existing_value: str) -> str:
    """Merge list-shaped memory fields without dropping older facts."""
    existing_items = _loads_list(existing_value)
    new_items = _loads_list(new_value)
    if not new_items:
        return existing_value or "[]"
    merged: list[object] = []
    seen: set[str] = set()
    for item in [*existing_items, *new_items]:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        merged.append(item)
        seen.add(key)
    return json.dumps(merged, ensure_ascii=False)


def _build_memory_input(messages: list, scope: SessionScopeSnapshot) -> str:
    """Build memory extraction input with visible-scope metadata."""
    scope_payload = {
        "session_scope": scope.session_scope,
        "handoff_occurred": scope.handoff_occurred,
        "human_messages_available": scope.human_messages_available,
    }
    return (
        "会话可见范围："
        + json.dumps(scope_payload, ensure_ascii=False)
        + "\n\n对话内容：\n"
        + format_dialog(messages)
    )


def _parse_memory_json(content: str) -> ParsedCustomerMemory:
    """Parse memory JSON from the LLM response."""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMError("记忆固化结果不是有效 JSON") from exc
    consent_status = str(payload.get("consent_status", "unknown")).strip()
    if consent_status not in ALLOWED_CONSENT_STATUS:
        consent_status = MemoryConsentStatus.UNKNOWN.value
    return ParsedCustomerMemory(
        display_name=str(payload.get("display_name", "")).strip(),
        preferences_json=_dump_json_object(payload.get("preferences", {})),
        order_summary_json=_dump_json_object(payload.get("order_summary", {})),
        special_dates_json=_dump_json_list(payload.get("special_dates", [])),
        allergens_json=_dump_json_list(payload.get("allergens", [])),
        consent_status=consent_status,
    )


def _dump_json_object(value: object) -> str:
    """Keep only JSON object shaped values."""
    payload = value if isinstance(value, dict) else {}
    return json.dumps(payload, ensure_ascii=False)


def _dump_json_list(value: object) -> str:
    """Keep only JSON list shaped values."""
    payload = value if isinstance(value, list) else []
    return json.dumps(payload, ensure_ascii=False)


def _loads_list(raw_json: str) -> list[object]:
    try:
        parsed = json.loads(raw_json or "[]")
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []
