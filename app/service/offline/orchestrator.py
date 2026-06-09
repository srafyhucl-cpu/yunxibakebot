"""离线 Agent 编排器。"""

from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.logger import setup_logger
from app.models.conversation_review import ConversationReview
from app.service.offline.agent_qa_review import QaReviewAgent

logger = setup_logger()

ResultT = TypeVar("ResultT")


class OfflineReviewOrchestrator:
    """按顺序调度离线 Agent，并隔离单 Agent 异常。"""

    def __init__(self, qa_review_agent: QaReviewAgent) -> None:
        self._qa_review_agent = qa_review_agent

    async def run_once(self) -> list[ConversationReview]:
        """执行一轮 P2 离线质检。"""
        reviews = await _safe_run("qa_review", self._qa_review_agent.run)
        return reviews or []


async def _safe_run(
    agent_name: str,
    runner: Callable[[], Awaitable[ResultT]],
) -> ResultT | None:
    """捕获单个 Agent 异常，避免拖垮整轮离线任务。"""
    try:
        return await runner()
    except Exception as exc:
        logger.error("离线 Agent 执行失败 agent=%s err=%s", agent_name, exc)
        return None
