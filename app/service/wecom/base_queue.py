"""微信消息队列的通用后台 Worker 基类。"""

import asyncio
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from app.logger import setup_logger

logger = setup_logger()

MessageT = TypeVar("MessageT")


class BaseWeComMessageQueue(ABC, Generic[MessageT]):
    """封装队列 Worker 的启动、停止和异常隔离流程。"""

    def __init__(self, queue_max_size: int, queue_name: str) -> None:
        self._queue: asyncio.Queue[MessageT] = asyncio.Queue(maxsize=queue_max_size)
        self._worker_task: asyncio.Task[None] | None = None
        self._chat_service = None
        self._queue_name = queue_name

    def start_worker(self, chat_service) -> None:
        """启动后台消费任务。"""
        if self._worker_task is not None and not self._worker_task.done():
            logger.warning("%s Worker 已在运行，跳过重复启动", self._queue_name)
            return

        self._chat_service = chat_service
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("%s Worker 已启动", self._queue_name)

    async def stop(self) -> None:
        """停止后台 Worker。"""
        if self._worker_task is None or self._worker_task.done():
            return

        self._worker_task.cancel()
        try:
            await self._worker_task
        except asyncio.CancelledError:
            pass
        self._worker_task = None
        logger.info("%s Worker 已停止", self._queue_name)

    @property
    def queue_size(self) -> int:
        """当前队列中的待处理消息数量。"""
        return self._queue.qsize()

    async def _worker_loop(self) -> None:
        """持续消费队列，单条异常不影响后续消息。"""
        logger.info("%s Worker 开始运行", self._queue_name)
        while True:
            try:
                msg = await self._queue.get()
            except (asyncio.CancelledError, GeneratorExit):
                break

            try:
                await self._process_one(msg)
            except Exception as exc:
                logger.error(
                    "%s 消息处理异常 %s err=%s",
                    self._queue_name,
                    self._message_log_context(msg),
                    exc,
                )
            finally:
                self._queue.task_done()

    @abstractmethod
    async def _process_one(self, msg: MessageT) -> None:
        """处理单条消息。"""

    @abstractmethod
    def _message_log_context(self, msg: MessageT) -> str:
        """返回异常日志中的消息上下文。"""
