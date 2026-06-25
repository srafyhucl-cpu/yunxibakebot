"""离线会话质检 Agent。"""

import json
from dataclasses import dataclass

from app.config import settings
from app.exceptions import LLMError
from app.logger import setup_logger
from app.models.conversation_review import (
    ConversationReview,
    ConversationReviewCreate,
)
from app.models.message import Message
from app.repository.conversation_review_repo import ConversationReviewRepo
from app.repository.message_repo import MessageRepo
from app.repository.session_repo import SessionRepo
from app.service.llm.client import chat_completion as llm_chat
from app.service.offline.agent_shared import format_dialog
from app.service.offline.json_utils import parse_json_object
from app.service.offline.model_selection import select_offline_review_model

logger = setup_logger()

LOW_QUALITY_SCORE_THRESHOLD = 60
QA_REVIEW_SYSTEM_PROMPT = (
    "你是芸熙烘焙客服质检员。请只输出 JSON："
    '{"quality_score": 0-100, "issues": ["问题1"]}。'
    "评分依据包括是否答准、是否答漏、态度是否友好、是否存在食品安全风险。"
    "如果分数低于 60，issues 必须说明具体问题；禁止输出 0 分但 issues 为空。"
)
QA_REVIEW_REPAIR_PROMPT = (
    "上一次质检输出不合格。请重新检查同一段对话，只输出合法 JSON："
    '{"quality_score": 0-100, "issues": ["具体问题"]}。'
)


@dataclass
class ParsedQaReview:
    """LLM 质检输出的结构化结果。"""

    quality_score: int
    issues_json: str


class QaReviewAgent:
    """读取待质检会话，调用 LLM 后写入 conversation_reviews。"""

    def __init__(
        self,
        session_repo: SessionRepo,
        message_repo: MessageRepo,
        review_repo: ConversationReviewRepo,
        max_sessions: int = 200,
        reviewer_model: str = "",
    ) -> None:
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._review_repo = review_repo
        self._max_sessions = max_sessions
        self._reviewer_model = select_offline_review_model(reviewer_model)
        self.last_run_result: list[ConversationReview] = []

    async def run(self) -> list[ConversationReview]:
        """执行一轮会话质检，单会话失败不影响后续会话。"""
        sessions = await self._session_repo.list_review_candidates(self._max_sessions)
        reviews: list[ConversationReview] = []
        for session in sessions:
            try:
                messages = await self._message_repo.get_by_session(session.id)
                if not messages:
                    continue
                parsed = await self._review_messages(messages)
                reviews.append(
                    await self._review_repo.create(
                        ConversationReviewCreate(
                            session_id=session.id,
                            quality_score=parsed.quality_score,
                            issues_json=parsed.issues_json,
                            reviewer_model=self._reviewer_model,
                        )
                    )
                )
            except Exception as exc:
                logger.error("离线会话质检失败 session=%s err=%s", session.id, exc)
        self.last_run_result = reviews
        return reviews

    async def _review_messages(self, messages: list[Message]) -> ParsedQaReview:
        dialog = format_dialog(messages)
        last_content = ""
        max_attempts = settings.OFFLINE_LLM_REPAIR_RETRIES + 1
        for attempt in range(max_attempts):
            response = await llm_chat(
                _build_review_messages(dialog, last_content, attempt),
                tools=None,
                temperature=0,
                max_tokens=512,
                model=self._reviewer_model,
            )
            last_content = response.choices[0].message.content or "{}"
            try:
                return _parse_review_json(last_content)
            except LLMError:
                if attempt >= max_attempts - 1:
                    raise
        raise LLMError("质检结果修复失败")


def _build_review_messages(
    dialog: str,
    last_content: str,
    attempt: int,
) -> list[dict[str, str]]:
    if attempt == 0:
        return [
            {"role": "system", "content": QA_REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": dialog},
        ]
    return [
        {"role": "system", "content": QA_REVIEW_REPAIR_PROMPT},
        {
            "role": "user",
            "content": f"上一次输出：{last_content}\n\n对话内容：\n{dialog}",
        },
    ]


def _parse_review_json(content: str) -> ParsedQaReview:
    """解析质检 JSON，格式不合规则让调用方按单会话失败处理。"""
    try:
        payload = parse_json_object(content, "质检结果不是有效 JSON")
        raw_score = int(payload.get("quality_score", 0))
        issues = payload.get("issues", [])
    except (TypeError, ValueError, LLMError) as exc:
        raise LLMError("质检结果不是有效 JSON") from exc

    if not isinstance(issues, list):
        issues = []
    score = max(0, min(raw_score, 100))
    issues_text = [str(item) for item in issues if str(item).strip()]
    if score < LOW_QUALITY_SCORE_THRESHOLD and not issues_text:
        raise LLMError("低分质检必须说明具体问题")
    return ParsedQaReview(
        quality_score=score,
        issues_json=json.dumps(issues_text, ensure_ascii=False),
    )
