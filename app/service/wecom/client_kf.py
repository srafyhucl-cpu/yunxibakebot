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
