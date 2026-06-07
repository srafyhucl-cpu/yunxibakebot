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

        企微限制：
          - 状态 0（未处理）：需先分配给智能助手才能 API 发送
          - 状态 1（智能助手）：可以直接 API 发送
          - 状态 2（排队中）：可切换为智能助手
          - 状态 3（人工接待）：只能转接或结束，**无法切回智能助手**
          - 状态 4（已结束）：无法操作

        状态转换规则（官方文档）：
          - 0 → 1 / 2 / 3
          - 1 → 2 / 3
          - 2 → 3
          - 3 → 3（转接）/ 4（结束）
          - 4 → 不可变更（需用户重新发消息）

        返回 True 表示可以发消息，False 表示失败。
        """
        state = await self.get_kf_service_state(external_userid)

        # 状态为 None 表示查询失败，仍尝试发送（让 send_msg 报错更明确）
        if state is None:
            logger.warning("无法查询会话状态，将直接尝试发送 user=%s", external_userid)
            return True

        # 1（智能助手）可以直接发消息
        if state == 1:
            return True

        # 0（未处理）→ 分配给智能助手
        if state == 0:
            return await self._trans_service_state(external_userid, 1)

        # 2（排队中）→ 尝试切换为智能助手
        if state == 2:
            return await self._trans_service_state(external_userid, 1)

        # 3（人工接待）→ 无法切回智能助手，只能结束会话
        #   结束后用户重新发消息会创建状态 0 的新会话
        if state == 3:
            logger.warning(
                "客服会话处于人工接待模式，尝试结束会话 user=%s",
                external_userid,
            )
            ended = await self._trans_service_state(external_userid, 4)
            if ended:
                logger.info(
                    "已结束人工客服会话，请用户重新发送消息以创建新会话 user=%s",
                    external_userid,
                )
            return False

        # 4（已结束）
        logger.warning(
            "客服会话已结束，无法发送消息 user=%s state=%d",
            external_userid,
            state,
        )
        return False

    async def _trans_service_state(
        self: WeComClient, external_userid: str, target_state: int
    ) -> bool:
        """
        调用 service_state/trans 接口变更会话状态。
        """
        token = await self.get_token()
        open_kfid = settings.WECOM_KF_ID

        body: dict[str, Any] = {
            "open_kfid": open_kfid,
            "external_userid": external_userid,
            "service_state": target_state,
        }

        resp = await self._client.post(
            f"{WECOM_API_BASE}/kf/service_state/trans",
            params={"access_token": token},
            json=body,
        )
        data = resp.json()

        state_names = {
            0: "未处理",
            1: "智能助手",
            2: "排队中",
            3: "人工接待",
            4: "已结束",
        }
        target_name = state_names.get(target_state, str(target_state))

        if data.get("errcode") == 0:
            logger.info(
                "客服会话状态切换成功 → %s user=%s", target_name, external_userid
            )
            return True

        logger.error(
            "客服会话状态切换失败 目标=%s user=%s err=%s",
            target_name,
            external_userid,
            data.get("errmsg"),
        )
        return False
