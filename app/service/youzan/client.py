"""
有赞云 API 客户端。

负责 OAuth2 token 管理和核心业务 API 调用：
- silent grant 获取 access_token（自动续期）
- 客服消息主动推送
- 订单详情查询
- 物流跟踪查询
"""

import time

import httpx

from app.config import settings
from app.exceptions import APIError
from app.logger import setup_logger

logger = setup_logger()

# ── 有赞云常量 ────────────────────────────────────────────────────────────
YOUZAN_AUTH_URL = "https://open.youzanyun.com/auth/token"
YOUZAN_API_BASE = "https://open.youzanyun.com/api"
TOKEN_REFRESH_MARGIN = 300  # 提前 5 分钟刷新（秒）


class YouzanClient:
    """有赞云 API 客户端（单例，管理 access_token 缓存）。"""

    def __init__(self) -> None:
        self._access_token: str = ""
        self._token_expires_at: float = 0.0
        self._http: httpx.AsyncClient | None = None

    @property
    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        return self._http

    async def _refresh_token(self) -> str:
        """通过 OAuth2 silent grant 向有赞云申请 access_token。"""
        try:
            resp = await self._client.post(
                YOUZAN_AUTH_URL,
                data={
                    "client_id": settings.YOUZAN_CLIENT_ID,
                    "client_secret": settings.YOUZAN_CLIENT_SECRET,
                    "grant_type": "silent",
                    "kdtId": settings.YOUZAN_KDT_ID,
                },
            )
            data: dict = resp.json()
        except httpx.HTTPError as exc:
            raise APIError(f"有赞 token 请求失败: {exc}") from exc

        token: str = data.get("access_token", "")
        if not token:
            raise APIError(f"有赞 token 响应异常: {data}")

        expires_in: int = data.get("expires_in", 172800)
        self._access_token = token
        self._token_expires_at = time.time() + expires_in - TOKEN_REFRESH_MARGIN
        logger.info("有赞 access_token 已刷新，有效期 %ds", expires_in)
        return token

    async def get_token(self) -> str:
        """返回有效的 access_token，过期则自动刷新。"""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        return await self._refresh_token()

    async def _call(self, api_name: str, version: str, params: dict) -> dict:
        """调用有赞 OpenAPI，自动附加 Bearer token。"""
        token = await self.get_token()
        try:
            resp = await self._client.post(
                f"{YOUZAN_API_BASE}/{api_name}/{version}",
                headers={"Authorization": f"Bearer {token}"},
                json=params,
            )
            result: dict = resp.json()
        except httpx.HTTPError as exc:
            raise APIError(f"有赞 API 调用失败 [{api_name}]: {exc}") from exc

        if resp.status_code != 200:
            raise APIError(f"有赞 API 响应异常 [{api_name}]: {result}")
        return result

    async def send_reply(self, buyer_open_id: str, content: str) -> dict:
        """主动推送客服消息给买家。"""
        logger.info("有赞客服消息发送: buyer=%s", buyer_open_id)
        return await self._call(
            "youzan.scrm.im.conversation.message.create", "3.0.0",
            {
                "kdt_id": settings.YOUZAN_KDT_ID,
                "open_id": buyer_open_id,
                "message_type": "text",
                "content": content,
            },
        )

    async def get_order(self, order_no: str) -> dict:
        """查询订单详情。"""
        logger.info("有赞订单查询: order=%s", order_no)
        return await self._call(
            "youzan.trade.get", "4.0.0",
            {"tid": order_no, "kdt_id": settings.YOUZAN_KDT_ID},
        )

    async def get_logistics(self, order_no: str) -> dict:
        """查询物流跟踪信息。"""
        logger.info("有赞物流查询: order=%s", order_no)
        return await self._call(
            "youzan.express.order.get", "3.0.0",
            {"tid": order_no, "kdt_id": settings.YOUZAN_KDT_ID},
        )

    async def close(self) -> None:
        """关闭 HTTP 连接池。"""
        if self._http:
            await self._http.aclose()
            self._http = None
