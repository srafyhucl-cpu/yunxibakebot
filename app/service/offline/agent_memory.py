"""离线顾客记忆固化 Agent。"""

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
from app.repository.customer_profile_repo import CustomerProfileRepo
from app.repository.message_repo import MessageRepo
from app.repository.offline_session_repo import OfflineSessionRepo
from app.service.llm.client import chat_completion as llm_chat
from app.service.offline.agent_shared import format_dialog

logger = setup_logger()

MEMORY_SYSTEM_PROMPT = (
    "你是芸熙烘焙顾客画像整理助手。请只输出 JSON："
    '{"display_name": "", "preferences": {}, "order_summary": {}, "allergens": [], '
    '"consent_status": "unknown"}。'
    "只抽取对后续服务有帮助的偏好、最近订单摘要和过敏提醒；不要保存电话、地址等隐私。"
    "过敏信息只能作为提醒核对事实，不能写成能否食用的结论。"
)

ALLOWED_CONSENT_STATUS = {
    MemoryConsentStatus.UNKNOWN.value,
    MemoryConsentStatus.GRANTED.value,
    MemoryConsentStatus.REVOKED.value,
}


@dataclass
class ParsedCustomerMemory:
    """LLM 抽取出的顾客画像。"""

    display_name: str
    preferences_json: str
    order_summary_json: str
    allergens_json: str
    consent_status: str


class MemoryAgent:
    """基于近期会话固化顾客长期记忆。"""

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
        """执行一轮记忆固化，单会话失败不影响后续。"""
        sessions = await self._session_repo.list_memory_candidates(self._max_sessions)
        profiles: list[CustomerProfile] = []
        for session in sessions:
            try:
                messages = await self._message_repo.get_by_session(session.id)
                if not messages:
                    continue
                parsed = await self._extract_memory(messages)
                profiles.append(await self._save_profile(session, parsed))
            except Exception as exc:
                logger.error("离线记忆固化失败 session=%s err=%s", session.id, exc)
        return profiles

    async def _extract_memory(self, messages: list) -> ParsedCustomerMemory:
        response = await llm_chat(
            [
                {"role": "system", "content": MEMORY_SYSTEM_PROMPT},
                {"role": "user", "content": format_dialog(messages)},
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
                allergens_json=_memory_value(
                    memory.allergens_json,
                    _existing_value(existing, "allergens_json"),
                    "[]",
                ),
                consent_status=memory.consent_status,
                source_evidence_json=json.dumps(
                    {"session_ids": [session.id]},
                    ensure_ascii=False,
                ),
                last_interaction_at=session.updated_at or session.created_at,
            )
        )


def _existing_value(profile: CustomerProfile | None, field_name: str) -> str:
    """读取已有画像字段，缺失时返回空字符串。"""
    return str(getattr(profile, field_name, "")) if profile is not None else ""


def _memory_value(new_value: str, existing_value: str, empty_value: str) -> str:
    """LLM 未抽到字段时保留已有画像。"""
    return existing_value if new_value == empty_value and existing_value else new_value


def _parse_memory_json(content: str) -> ParsedCustomerMemory:
    """解析画像 JSON，格式不合规则按单会话失败处理。"""
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
        allergens_json=_dump_json_list(payload.get("allergens", [])),
        consent_status=consent_status,
    )


def _dump_json_object(value: object) -> str:
    """只保留 JSON 对象形态。"""
    payload = value if isinstance(value, dict) else {}
    return json.dumps(payload, ensure_ascii=False)


def _dump_json_list(value: object) -> str:
    """只保留 JSON 数组形态。"""
    payload = value if isinstance(value, list) else []
    return json.dumps(payload, ensure_ascii=False)
