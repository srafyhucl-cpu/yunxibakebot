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

logger = setup_logger()

QA_REVIEW_SYSTEM_PROMPT = (
    "你是芸熙烘焙客服质检员。请只输出 JSON："
    '{"quality_score": 0-100, "issues": ["问题1"]}。'
    "评分依据包括是否答准、是否答漏、态度是否友好、是否存在食品安全风险。"
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
        self._reviewer_model = reviewer_model or settings.MIMO_CHAT_MODEL
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
        response = await llm_chat(
            [
                {"role": "system", "content": QA_REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": format_dialog(messages)},
            ],
            tools=None,
            temperature=0,
            max_tokens=512,
            model=self._reviewer_model,
        )
        content = response.choices[0].message.content or "{}"
        return _parse_review_json(content)


def _parse_review_json(content: str) -> ParsedQaReview:
    """解析质检 JSON，格式不合规则让调用方按单会话失败处理。"""
    try:
        payload = json.loads(content)
        raw_score = int(payload.get("quality_score", 0))
        issues = payload.get("issues", [])
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise LLMError("质检结果不是有效 JSON") from exc

    if not isinstance(issues, list):
        issues = []
    score = max(0, min(raw_score, 100))
    issues_text = [str(item) for item in issues if str(item).strip()]
    return ParsedQaReview(
        quality_score=score,
        issues_json=json.dumps(issues_text, ensure_ascii=False),
    )
