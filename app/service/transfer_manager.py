"""
转人工管理服务。

管理从"客户请求转人工"到"客服处理完毕"的完整生命周期。
"""

import time
import httpx

from app.config import settings
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

    async def notify_staff_emergency(self, session_id: str, last_message: str) -> None:
        """向值班店员的企微客户端异步推送紧急呼叫消息。"""
        call_time = time.strftime("%Y-%m-%d %H:%M:%S")
        markdown_content = (
            f"### 🚨 真人客服紧急呼叫\n"
            f"- **会话 ID**: `{session_id}`\n"
            f"- **客户留言**: `{last_message}`\n"
            f"- **呼叫时间**: `{call_time}`\n"
            f"- **处理提示**: 请值班客服尽快接入处理。"
        )

        # 1. 异步推送群机器人 (如果配置了 WECOM_ROBOT_WEBHOOK)
        if settings.WECOM_ROBOT_WEBHOOK:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        settings.WECOM_ROBOT_WEBHOOK,
                        json={
                            "msgtype": "markdown",
                            "markdown": {
                                "content": markdown_content
                            }
                        }
                    )
                    logger.info("企微群机器人呼叫成功: %s", resp.text)
            except Exception as exc:
                logger.error("企微群机器人呼叫失败: %s", exc)

        # 2. 异步推送应用消息 (给特定值班客服 WECOM_STAFF_ID)
        if settings.WECOM_CORP_ID and settings.WECOM_SECRET and settings.WECOM_STAFF_ID:
            try:
                from app.service.wecom.client import get_wecom_client
                wecom_client = get_wecom_client()
                token = await wecom_client.get_token()

                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        "https://qyapi.weixin.qq.com/cgi-bin/message/send",
                        params={"access_token": token},
                        json={
                            "touser": settings.WECOM_STAFF_ID,
                            "msgtype": "markdown",
                            "agentid": int(settings.WECOM_AGENT_ID or 0),
                            "markdown": {
                                "content": markdown_content
                            },
                        }
                    )
                    logger.info("企微客服应用呼叫成功: %s", resp.text)
            except Exception as exc:
                logger.error("企微客服应用呼叫失败: %s", exc)

    async def request_transfer(self, session_id: str, user_id: str,
                               reason: str = "", summary: str = "") -> HumanTransfer:
        """创建转人工工单，返回工单信息。"""
        transfer = await self._repo.create(session_id, user_id, reason, summary)
        logger.info("转人工工单已创建: %s 原因=%s", transfer.id, reason)

        # 联动触发真人紧急呼叫通知中心
        await self.notify_staff_emergency(session_id, reason or summary)

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
