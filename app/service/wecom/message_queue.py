"""企微异步消息队列 + 后台 Worker。

职责：
- 接收入队请求，立即返回（<1ms），满足企微回调 5s 超时要求
- 后台循环消费队列，调用 ChatService 处理
- 异常隔离：单条消息失败不影响其他消息

使用方式：
    lifespan startup:  wecom_queue.start_worker(chat_service)
    callback 入队:      wecom_queue.enqueue(WeComIncomingMessage(...))
    lifespan shutdown:   await wecom_queue.stop()
"""

import asyncio
from dataclasses import dataclass

from app.logger import setup_logger

logger = setup_logger()

# 队列容量上限（满队列时新消息被丢弃）
QUEUE_MAX_SIZE = 1000


@dataclass(frozen=True)
class WeComIncomingMessage:
    """企微入队消息（不可变数据对象）。"""

    external_user_id: str
    content: str
    channel_msg_id: str


class WeComMessageQueue:
    """企微异步消息队列 + 后台 Worker。"""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[WeComIncomingMessage] = asyncio.Queue(
            maxsize=QUEUE_MAX_SIZE
        )
        self._worker_task: asyncio.Task[None] | None = None
        self._chat_service = None  # 延迟注入（lifespan 启动时设置）

    async def enqueue(self, msg: WeComIncomingMessage) -> bool:
        """
        入队（非阻塞）。
        返回 True 表示入队成功，False 表示队列已满。
        """
        try:
            self._queue.put_nowait(msg)
            return True
        except asyncio.QueueFull:
            logger.warning(
                "企微消息队列已满（%d），丢弃消息 user=%s",
                QUEUE_MAX_SIZE,
                msg.external_user_id,
            )
            return False

    def start_worker(self, chat_service) -> None:
        """
        启动后台消费任务。

        参数：
            chat_service: ChatService 实例，用于处理消息和发送回复
        必须在事件循环中调用（通常在 lifespan startup 阶段）。
        """
        if self._worker_task is not None and not self._worker_task.done():
            logger.warning("Worker 已在运行，跳过重复启动")
            return

        self._chat_service = chat_service
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("企微消息队列 Worker 已启动")

    async def stop(self) -> None:
        """停止后台 Worker（应用关闭时调用）。"""
        if self._worker_task is None or self._worker_task.done():
            return

        self._worker_task.cancel()
        try:
            await self._worker_task
        except asyncio.CancelledError:
            pass
        self._worker_task = None
        logger.info("企微消息队列 Worker 已停止")

    @property
    def queue_size(self) -> int:
        """当前队列中待处理的消息数量（用于监控）。"""
        return self._queue.qsize()

    async def _worker_loop(self) -> None:
        """后台循环：持续从队列取消息并处理。"""
        logger.info("企微消息队列 Worker 开始运行")
        while True:
            try:
                # 阻塞等待下一条消息
                msg = await self._queue.get()
            except (asyncio.CancelledError, GeneratorExit):
                break

            try:
                await self._process_one(msg)
            except Exception as exc:
                # 异常隔离：单条失败不影响后续处理
                logger.error(
                    "企微消息处理异常 user=%s msg_id=%s err=%s",
                    msg.external_user_id,
                    msg.channel_msg_id,
                    exc,
                )
            finally:
                self._queue.task_done()

    async def _process_one(self, msg: WeComIncomingMessage) -> None:
        """
        处理单条企微消息的完整流程：
        1. 调用 ChatService 进行 AI 对话
        2. 如果有回复，通过企微 API 发送给客户
        """
        if self._chat_service is None:
            logger.error("ChatService 未注入，无法处理消息")
            return

        # 1. 调用 ChatService 进行 AI 对话
        reply = await self._chat_service.handle_message(
            channel="wecom_1on1",
            user_id=msg.external_user_id,
            content=msg.content,
            channel_msg_id=msg.channel_msg_id,
        )

        # 2. 如果有回复，发送给客户
        if reply:
            from app.service.wecom.client import get_wecom_client

            client = get_wecom_client()
            result = await client.send_text(msg.external_user_id, reply)
            if result.get("errcode") != 0:
                logger.error(
                    "企微回复发送失败 user=%s err=%s",
                    msg.external_user_id,
                    result.get("errmsg"),
                )


# ── 全局单例 ────────────────────────────────────────────────
wecom_queue = WeComMessageQueue()
