"""微信客服 API 客户端（独立模块，避免 client.py 超线）。

职责：
- 调用微信客服专用接口（send_msg / sync_msg）
- 与自建应用的 /message/send 完全独立的 API 体系
"""

from typing import Any

from app.config import settings
from app.logger import setup_logger
from app.service.wecom.client import WECOM_API_BASE, WeComClient

logger = setup_logger()


class KfClientMixin:
    """微信客服 API 方法集（混入 WeComClient）。"""

    async def send_kf_text(
        self,
        external_userid: str,
        content: str,
        msgid: str = "",
    ) -> dict:
        """
        发送微信客服文本消息。

        使用 /cgi-bin/kf/send_msg 接口，与自建应用的 /message/send 完全独立。

        参数：
            external_userid: 微信客户的 external_userid
            content: 文本内容（最长 2048 字节）
            msgid: 消息 ID（用于幂等性，可选）
        返回：
            API 响应 JSON
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
        self,
        external_userid: str,
        title: str,
        url: str,
        desc: str = "",
        thumb_media_id: str = "",
        msgid: str = "",
    ) -> dict:
        """
        发送微信客服图文链接消息（用于商品卡片）。

        参数：
            external_userid: 微信客户的 external_userid
            title: 标题（最长 128 字节）
            url: 点击跳转链接（最长 2048 字节）
            desc: 描述（最长 512 字节）
            thumb_media_id: 缩略图素材 ID
            msgid: 消息 ID（用于幂等性，可选）
        返回：
            API 响应 JSON
        """
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
        self, kf_token: str, cursor: str = "", limit: int = 1000
    ) -> dict:
        """
        拉取微信客服消息（sync_msg 接口）。

        收到企微回调通知后，用回调中的 Token 调此接口拉取具体消息内容。

        参数：
            kf_token: 回调事件中的 Token 字段（有效期 10 分钟）
            cursor: 上一次返回的游标，首次不填
            limit: 每次拉取数量，最大 1000
        返回：
            API 响应 JSON，包含 next_cursor / has_more / msg_list
        """
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


# 让 WeComClient 继承 KfClientMixin，保持原有调用方式不变
WeComClient.__bases__ = (KfClientMixin,) + WeComClient.__bases__
