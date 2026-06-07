"""微信客服 API 方法集（Mixin 基类，供 WeComClient 继承）。

职责：
- 调用微信客服专用接口（send_msg / sync_msg）
- 与自建应用的 /message/send 完全独立的 API 体系

使用方式：
    class WeComClient(KfClientMixin): ...
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.config import settings
from app.logger import setup_logger
from app.service.wecom.constants import WECOM_API_BASE

if TYPE_CHECKING:
    from app.service.wecom.client import WeComClient

logger = setup_logger()


class KfClientMixin:
    """微信客服 API 方法集。"""

    async def send_kf_text(
        self: WeComClient,
        external_userid: str,
        content: str,
        msgid: str = "",
    ) -> dict:
        """
        发送微信客服文本消息。

        使用 /cgi-bin/kf/send_msg 接口，与自建应用的 /message/send 完全独立。
        """
        token = await self.get_token()
        open_kfid = settings.WECOM_KF_ID

        body: dict[str, Any] = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgtype": "text",
            "text": {"content": content},
        }
        if msgid:
            body["msgid"] = msgid

        resp = await self._client.post(
            f"{WECOM_API_BASE}/kf/send_msg",
            params={"access_token": token},
            json=body,
        )
        response_data = resp.json()

        if response_data.get("errcode") == 0:
            logger.info(
                "客服文本消息已发送 to=%s len=%d", external_userid, len(content)
            )
        else:
            logger.error(
                "客服文本消息发送失败 to=%s err=%s",
                external_userid,
                response_data.get("errmsg"),
            )
        return response_data

    async def send_kf_link(
        self: WeComClient,
        external_userid: str,
        title: str,
        url: str,
        desc: str = "",
        thumb_media_id: str = "",
        msgid: str = "",
    ) -> dict:
        """发送微信客服图文链接消息（用于商品卡片）。"""
        token = await self.get_token()
        open_kfid = settings.WECOM_KF_ID

        body: dict[str, Any] = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgtype": "link",
            "link": {
                "title": title,
                "desc": desc,
                "url": url,
                "thumb_media_id": thumb_media_id,
            },
        }
        if msgid:
            body["msgid"] = msgid

        resp = await self._client.post(
            f"{WECOM_API_BASE}/kf/send_msg",
            params={"access_token": token},
            json=body,
        )
        response_data = resp.json()

        if response_data.get("errcode") == 0:
            logger.info("客服链接消息已发送 to=%s title=%s", external_userid, title)
        else:
            logger.error(
                "客服链接消息发送失败 to=%s title=%s err=%s",
                external_userid,
                title,
                response_data.get("errmsg"),
            )
        return response_data

    async def sync_kf_messages(
        self: WeComClient, kf_token: str, cursor: str = "", limit: int = 1000
    ) -> dict:
        """拉取微信客服消息（sync_msg 接口）。"""
        token = await self.get_token()
        open_kfid = settings.WECOM_KF_ID

        body: dict[str, Any] = {
            "token": kf_token,
            "open_kfid": open_kfid,
            "limit": limit,
        }
        if cursor:
            body["cursor"] = cursor

        resp = await self._client.post(
            f"{WECOM_API_BASE}/kf/sync_msg",
            params={"access_token": token},
            json=body,
        )
        return resp.json()

    # ── 会话状态管理 ──────────────────────────────────────

    async def get_kf_service_state(
        self: WeComClient, external_userid: str
    ) -> int | None:
        """
        查询客服会话状态。

        返回值：
            service_state: 0-未处理 / 1-智能助手 / 2-排队中 / 3-人工接待 / 4-已结束
            出错返回 None
        """
        token = await self.get_token()
        open_kfid = settings.WECOM_KF_ID

        body: dict[str, str] = {
            "open_kfid": open_kfid,
            "external_userid": external_userid,
        }
        resp = await self._client.post(
            f"{WECOM_API_BASE}/kf/service_state/get",
            params={"access_token": token},
            json=body,
        )
        data = resp.json()

        if data.get("errcode") == 0:
            state = data.get("service_state")
            logger.debug("客服会话状态查询 user=%s state=%s", external_userid, state)
            return state
        else:
            logger.error(
                "客服会话状态查询失败 user=%s err=%s",
                external_userid,
                data.get("errmsg"),
            )
            return None

    async def ensure_kf_session_active(self: WeComClient, external_userid: str) -> bool:
        """
        确保客服会话处于可发消息的状态。

        企微限制：只有 service_state 为 0（未处理）或 1（智能助手）时，
        才能通过 API 发送消息。如果当前状态不允许，自动切换为 1。

        返回 True 表示可以发消息，False 表示失败。
        """
        state = await self.get_kf_service_state(external_userid)

        # 状态为 None 表示查询失败，仍尝试发送（让 send_msg 报错更明确）
        if state is None:
            logger.warning("无法查询会话状态，将直接尝试发送 user=%s", external_userid)
            return True

        # 0（未处理）和 1（智能助手）都可以直接发消息
        if state in (0, 1):
            return True

        # 4（已结束）无法恢复，放弃发送
        if state == 4:
            logger.warning(
                "客服会话已结束，无法发送消息 user=%s state=%d",
                external_userid,
                state,
            )
            return False

        # 2（排队中）或 3（人工接待），切换为 1（智能助手）
        logger.info(
            "客服会话状态 %d 不允许API发送，切换为智能助手模式 user=%s",
            state,
            external_userid,
        )

        token = await self.get_token()
        open_kfid = settings.WECOM_KF_ID

        body: dict[str, Any] = {
            "open_kfid": open_kfid,
            "external_userid": external_userid,
            "service_state": 1,  # 切换为智能助手接待
        }

        resp = await self._client.post(
            f"{WECOM_API_BASE}/kf/service_state/trans",
            params={"access_token": token},
            json=body,
        )
        trans_data = resp.json()

        if trans_data.get("errcode") == 0:
            logger.info("客服会话已切换为智能助手模式 user=%s", external_userid)
            return True

        logger.error(
            "客服会话状态切换失败 user=%s err=%s",
            external_userid,
            trans_data.get("errmsg"),
        )
        return False
