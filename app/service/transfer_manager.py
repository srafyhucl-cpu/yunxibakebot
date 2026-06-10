"""转人工管理服务。"""

import time

import httpx

from app.config import settings
from app.logger import setup_logger
from app.models.transfer import HumanTransfer, TransferStatus
from app.repository.transfer_repo import TransferRepo

logger = setup_logger()

TRANSFER_TIMEOUT_MINUTES = 30
NOTIFY_HTTP_TIMEOUT_SECONDS = 10.0


class TransferManager:
    """管理转人工工单的创建、接单、关闭和通知。"""

    def __init__(self, repo: TransferRepo) -> None:
        self._repo = repo

    async def notify_staff_emergency(self, session_id: str, last_message: str) -> None:
        """向值班客服推送转人工摘要通知。"""
        call_time = time.strftime("%Y-%m-%d %H:%M:%S")
        markdown_content = (
            "### 转人工提醒\n"
            f"- **会话 ID**: `{session_id}`\n"
            f"- **对话摘要**:\n{last_message}\n"
            f"- **呼叫时间**: `{call_time}`\n"
            "- **处理提示**: 请值班客服尽快接入处理。"
        )

        await self._notify_robot(markdown_content)
        await self._notify_staff_app(markdown_content)

    async def _notify_robot(self, markdown_content: str) -> None:
        if not settings.WECOM_ROBOT_WEBHOOK:
            return
        try:
            async with httpx.AsyncClient(timeout=NOTIFY_HTTP_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    settings.WECOM_ROBOT_WEBHOOK,
                    json={
                        "msgtype": "markdown",
                        "markdown": {"content": markdown_content},
                    },
                )
                logger.info("企微群机器人呼叫成功: %s", resp.text)
        except Exception as exc:
            logger.error("企微群机器人呼叫失败: %s", exc)

    async def _notify_staff_app(self, markdown_content: str) -> None:
        if not settings.WECOM_CORP_ID or not settings.WECOM_SECRET:
            return
        staff_id = await self._resolve_staff_id()
        if not staff_id:
            logger.warning(
                "转人工摘要未推送：未配置 WECOM_STAFF_ID 且未找到客服接待人员"
            )
            return

        try:
            from app.service.wecom.client import WECOM_API_BASE, get_wecom_client

            wecom_client = get_wecom_client()
            token = await wecom_client.get_token()

            async with httpx.AsyncClient(timeout=NOTIFY_HTTP_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    f"{WECOM_API_BASE}/message/send",
                    params={"access_token": token},
                    json={
                        "touser": staff_id,
                        "msgtype": "markdown",
                        "agentid": int(settings.WECOM_AGENT_ID or 0),
                        "markdown": {"content": markdown_content},
                    },
                )
                logger.info(
                    "企微客服应用摘要通知结果 user=%s resp=%s", staff_id, resp.text
                )
        except Exception as exc:
            logger.error("企微客服应用摘要通知失败: %s", exc)

    async def _resolve_staff_id(self) -> str:
        if settings.WECOM_STAFF_ID:
            return settings.WECOM_STAFF_ID
        try:
            from app.service.wecom.client import get_wecom_client

            wecom_client = get_wecom_client()
            getter = getattr(wecom_client, "_get_first_servicer", None)
            if getter is None:
                return ""
            return str(await getter() or "")
        except Exception as exc:
            logger.error("自动获取客服接待人员失败: %s", exc)
            return ""

    async def request_transfer(
        self, session_id: str, user_id: str, reason: str = "", summary: str = ""
    ) -> HumanTransfer:
        """创建转人工工单，并推送摘要通知。"""
        transfer = await self._repo.create(session_id, user_id, reason, summary)
        logger.info("转人工工单已创建: %s 原因=%s", transfer.id, reason)

        await self.notify_staff_emergency(session_id, summary or reason)

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
        """获取所有待接单工单。"""
        return await self._repo.get_pending()
