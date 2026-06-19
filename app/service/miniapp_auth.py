"""小程序登录服务。"""

import hashlib

import httpx

from app.config import settings
from app.constants.miniapp import MINIAPP_DEMO_USER_ID


class MiniappAuthService:
    """处理微信小程序登录。"""

    async def login(self, code: str) -> dict:
        """使用 wx.login code 换取小程序用户标识；配置缺失时返回 demo 会话。"""
        normalized_code = code.strip()
        if not normalized_code:
            raise ValueError("登录 code 不能为空")
        if not self._is_wechat_configured():
            return self._demo_session(normalized_code)
        payload = await self._request_wechat_session(normalized_code)
        openid = str(payload.get("openid", "")).strip()
        if not openid:
            raise ValueError(str(payload.get("errmsg") or "微信登录失败"))
        return {
            "userId": f"wx_{openid}",
            "openid": openid,
            "sessionReady": True,
            "isDemo": False,
        }

    def _is_wechat_configured(self) -> bool:
        return bool(
            settings.WECHAT_MINIAPP_APP_ID and settings.WECHAT_MINIAPP_APP_SECRET
        )

    async def _request_wechat_session(self, code: str) -> dict:
        async with httpx.AsyncClient(
            timeout=settings.WECHAT_MINIAPP_HTTP_TIMEOUT_SECONDS
        ) as client:
            response = await client.get(
                settings.WECHAT_MINIAPP_AUTH_URL,
                params={
                    "appid": settings.WECHAT_MINIAPP_APP_ID,
                    "secret": settings.WECHAT_MINIAPP_APP_SECRET,
                    "js_code": code,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            data = response.json()
        return data if isinstance(data, dict) else {}

    def _demo_session(self, code: str) -> dict:
        digest = hashlib.sha256(code.encode("utf-8")).hexdigest()[:12]
        return {
            "userId": f"{MINIAPP_DEMO_USER_ID}-{digest}",
            "openid": "",
            "sessionReady": True,
            "isDemo": True,
        }
