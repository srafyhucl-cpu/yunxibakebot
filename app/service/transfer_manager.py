"""
转人工管理服务。

管理从"客户请求转人工"到"客服处理完毕"的完整生命周期。
"""

from app.logger import setup_logger
from app.models.transfer import HumanTransfer, TransferStatus
from app.repository.transfer_repo import TransferRepo

logger = setup_logger()

# 转人工工单超时时间（超过此时间无人接单则自动关闭）
TRANSFER_TIMEOUT_MINUTES = 30


class TransferManager:
    """转人工管理器：创建工单、接单、关闭、查询排队。"""

    def __init__(self, repo: TransferRepo) -> None:
        self._repo = repo

    async def request_transfer(self, session_id: str, user_id: str,
                               reason: str = "", summary: str = "") -> HumanTransfer:
        """创建转人工工单，返回工单信息。"""
        transfer = await self._repo.create(session_id, user_id, reason, summary)
        logger.info("转人工工单已创建: %s 原因=%s", transfer.id, reason)
        return transfer

    async def accept_transfer(self, transfer_id: str, staff_id: str) -> None:
        """客服接单，标记为已接入。"""
        await self._repo.update_status(transfer_id, TransferStatus.ACCEPTED, staff_id)
        logger.info("转人工已接单: %s 客服=%s", transfer_id, staff_id)

    async def close_transfer(self, transfer_id: str) -> None:
        """客服结单，关闭工单。"""
        await self._repo.update_status(transfer_id, TransferStatus.CLOSED)
        logger.info("转人工已关闭: %s", transfer_id)

    async def get_pending(self) -> list[HumanTransfer]:
        """获取所有待接单的工单列表。"""
        return await self._repo.get_pending()
