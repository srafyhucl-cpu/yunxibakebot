"""离线质检调度器。"""

import asyncio
from collections.abc import Callable
from typing import AsyncContextManager

from app.logger import setup_logger
from app.service.offline.orchestrator import OfflineReviewOrchestrator

logger = setup_logger()


class OfflineReviewScheduler:
    """以固定间隔触发离线 Agent 编排器。"""

    def __init__(
        self,
        orchestrator: OfflineReviewOrchestrator,
        interval_hours: float,
        scope_factory: Callable[[], AsyncContextManager[object]] | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._interval_seconds = max(interval_hours, 0.01) * 3600
        self._scope_factory = scope_factory
        self._task: asyncio.Task[None] | None = None

    def start(self) -> asyncio.Task[None]:
        """启动后台调度任务，并返回任务强引用。"""
        if self._task is not None and not self._task.done():
            logger.warning("离线质检调度器已在运行，跳过重复启动")
            return self._task
        self._task = asyncio.create_task(self._loop())
        logger.info("离线质检调度器已启动 interval_seconds=%s", self._interval_seconds)
        return self._task

    async def stop(self) -> None:
        """停止后台调度任务。"""
        if self._task is None or self._task.done():
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("离线质检调度器已停止")

    async def _loop(self) -> None:
        while True:
            try:
                if self._scope_factory is not None:
                    async with self._scope_factory():
                        await self._orchestrator.run_once()
                else:
                    await self._orchestrator.run_once()
            except Exception as exc:
                logger.error("离线质检调度轮次失败 err=%s", exc)
            await asyncio.sleep(self._interval_seconds)
