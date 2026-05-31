"""企微 API 客户端。

职责：
- 缓存并自动刷新 access_token（2 小时过期）
- 调用客户联系消息推送接口发送消息
"""

import asyncio
import time

import httpx

from app.config import settings
from app.logger import setup_logger

logger = setup_logger()

# 企微 API 基础地址
WECOM_API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"

# access_token 提前 5 分钟刷新
TOKEN_REFRESH_MARGIN = 300


class WeComClient:
    """企微 API 客户端（单例，管理 access_token 缓存）。"""

    def __init__(self) -> None:
        self._token: str = ""
        self._token_expires_at: float = 0
        self._http: httpx.AsyncClient | None = None
        self._lock = asyncio.Lock()

    @property
    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        return self._http

    async def _fetch_token(self) -> str:
        """向企微获取新的 access_token。"""
        resp = await self._client.get(
            f"{WECOM_API_BASE}/gettoken",
            params={
                "corpid": settings.WECOM_CORP_ID,
                "corpsecret": settings.WECOM_SECRET,
            },
        )
        response_data = resp.json()
        if response_data.get("errcode") != 0:
            raise RuntimeError(
                f"获取 access_token 失败: {response_data.get('errmsg', 'unknown')}"
            )
        token: str = response_data["access_token"]
        expires_in: int = response_data.get("expires_in", 7200)
        self._token = token
        self._token_expires_at = time.time() + expires_in - TOKEN_REFRESH_MARGIN
        logger.info("WeCom access_token 刷新成功（并发锁保护），有效期 %ds", expires_in)
        return token

    async def get_token(self) -> str:
        """获取有效的 access_token（双重检查锁保护并发安全）。"""
        # 快速路径：缓存有效直接返回（无锁开销）
        if self._token and time.time() < self._token_expires_at:
            return self._token
        # 慢路径：带锁并发限制，防止多协程同时刷新
        async with self._lock:
            # 双重检验：排队等待的协程无需重复刷新
            if self._token and time.time() < self._token_expires_at:
                return self._token
            return await self._fetch_token()

    async def send_text(
        self,
        external_user_id: str,
        content: str,
        agent_id: str | None = None,
    ) -> dict:
        """
        给客户（外部联系人）发送文本消息。

        参数：
            external_user_id: 企微外部联系人 userid
            content: 消息内容
            agent_id: 应用 AgentId（默认从配置读取）
        返回：
            API 响应 JSON
        """
        token = await self.get_token()
        resp = await self._client.post(
            f"{WECOM_API_BASE}/externalcontact/message/send",
            params={"access_token": token},
            json={
                "to_user": external_user_id,
                "msgtype": "text",
                "text": {"content": content},
                "agent_id": int(agent_id or settings.WECOM_AGENT_ID),
            },
        )
        response_data = resp.json()
        if response_data.get("errcode") == 0:
            logger.info(
                "消息已发送 to=%s len=%d", external_user_id, len(content)
            )
        else:
            logger.error(
                "消息发送失败 to=%s err=%s",
                external_user_id, response_data.get("errmsg"),
            )
        return response_data

    async def send_markdown(
        self,
        external_user_id: str,
        content: str,
        agent_id: str | None = None,
    ) -> dict:
        """给客户发送 Markdown 消息。"""
        token = await self.get_token()
        resp = await self._client.post(
            f"{WECOM_API_BASE}/externalcontact/message/send",
            params={"access_token": token},
            json={
                "to_user": external_user_id,
                "msgtype": "markdown",
                "markdown": {"content": content},
                "agent_id": int(agent_id or settings.WECOM_AGENT_ID),
            },
        )
        response_data = resp.json()
        if response_data.get("errcode") != 0:
            logger.error("Markdown 发送失败 err=%s", response_data.get("errmsg"))
        return response_data

    async def close(self) -> None:
        """关闭 HTTP 客户端。"""
        if self._http:
            await self._http.aclose()
            self._http = None


# 全局单例
_client: WeComClient | None = None


def get_wecom_client() -> WeComClient:
    """获取全局 WeComClient 单例。"""
    global _client
    if _client is None:
        _client = WeComClient()
    return _client


async def close_wecom_client() -> None:
    """关闭全局客户端（应用退出时调用）。"""
    global _client
    if _client:
        await _client.close()
        _client = None
