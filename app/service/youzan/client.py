"""
有赞云 API 客户端。

负责 OAuth2 token 管理和核心业务 API 调用：
- silent grant 获取 access_token（自动续期）
- 客服消息主动推送
- 订单详情查询
- 物流跟踪查询
"""

import asyncio
import time

import httpx

from app.config import settings
from app.exceptions import APIError
from app.logger import setup_logger
from app.repository.config_repo import ConfigRepo

logger = setup_logger()

# ── 有赞云常量 ────────────────────────────────────────────────────────────
YOUZAN_AUTH_URL = "https://open.youzanyun.com/auth/token"
YOUZAN_API_BASE = "https://open.youzanyun.com/api"
YOUZAN_GOODS_H5_BASE_URL = "https://h5.youzan.com/v2/showcase/goods"
TOKEN_REFRESH_MARGIN = 300  # 提前 5 分钟刷新（秒）
DEFAULT_TOKEN_EXPIRES_SECONDS = 172_800  # 有赞 token 默认有效期（48 小时）
MOCK_TOKEN_EXPIRES_SECONDS = 86_400     # Mock 模式 token 有效期（24 小时）


class YouzanClient:
    """有赞云 API 客户端（单例，管理 access_token 缓存并支持并发刷新锁与仓储持久化）。"""

    def __init__(self, config_repo: ConfigRepo | None = None) -> None:
        self._access_token: str = ""
        self._token_expires_at: float = 0.0
        self._http: httpx.AsyncClient | None = None
        self._lock = asyncio.Lock()
        self._config_repo = config_repo

    @property
    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            # trust_env=False 禁止从环境变量读取代理，避免无效端口错误
            self._http = httpx.AsyncClient(timeout=httpx.Timeout(10.0), trust_env=False)
        return self._http

    async def _refresh_token(self) -> str:
        """通过 OAuth2 silent grant 向有赞云申请 access_token。"""
        if settings.YOUZAN_MOCK_MODE:
            self._access_token = "mock_access_token_123456"
            self._token_expires_at = time.time() + MOCK_TOKEN_EXPIRES_SECONDS
            logger.info("有赞 access_token 已通过 Mock 仿真刷新")
            await self._save_token_to_db(self._access_token)
            return self._access_token

        try:
            resp = await self._client.post(
                YOUZAN_AUTH_URL,
                json={
                    "client_id": settings.YOUZAN_CLIENT_ID,
                    "client_secret": settings.YOUZAN_CLIENT_SECRET,
                    "authorize_type": "silent",
                    "grant_id": settings.YOUZAN_KDT_ID,
                },
            )
            data: dict = resp.json()
        except httpx.HTTPError as exc:
            raise APIError(f"有赞 token 请求失败: {exc}") from exc

        auth_data = data.get("data") if isinstance(data, dict) else None
        token = ""
        expires_in = DEFAULT_TOKEN_EXPIRES_SECONDS

        if isinstance(auth_data, dict):
            token = auth_data.get("access_token", "")
            expires_ms = auth_data.get("expires", 0)
            if expires_ms:
                expires_in = max(60, int((expires_ms / 1000.0) - time.time()))
        else:
            token = data.get("access_token", "")
            expires_in = data.get("expires_in", DEFAULT_TOKEN_EXPIRES_SECONDS)

        if not token:
            raise APIError(f"有赞 token 响应异常: {data}")

        self._access_token = token
        self._token_expires_at = time.time() + expires_in - TOKEN_REFRESH_MARGIN
        logger.info("有赞 access_token 已刷新，有效期 %ds", expires_in)
        await self._save_token_to_db(token)
        return token

    async def _save_token_to_db(self, token: str) -> None:
        """通过 ConfigRepo 安全持久化写入配置数据库。"""
        if self._config_repo is not None:
            try:
                await self._config_repo.set("youzan_access_token", token)
                logger.info("有赞 access_token 已通过 ConfigRepo 写入 shop_config 表")
            except Exception as exc:
                logger.error("有赞 access_token 数据库持久化失败: %s", exc)

    async def get_token(self) -> str:
        """返回有效的 access_token，使用 asyncio.Lock() 做并发刷新互斥。"""
        # Fast path
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        # Slow path with Lock
        async with self._lock:
            # Double-Checked Locking 双重过滤
            if self._access_token and time.time() < self._token_expires_at:
                return self._access_token
            return await self._refresh_token()

    async def _call(self, api_name: str, version: str, params: dict) -> dict:
        """调用有赞 OpenAPI，自动附加 Bearer token。"""
        if settings.YOUZAN_MOCK_MODE:
            from app.service.youzan.mock_emulator import YouzanMockEmulator
            logger.info("有赞 API 仿真调用拦截 [%s]: %s", api_name, params)
            if api_name == "youzan.scrm.im.conversation.message.create":
                return {"response": {"success": True}}
            elif api_name == "youzan.trade.get":
                return YouzanMockEmulator.get_mock_order_response(params.get("tid", "mock_order_123"))
            elif api_name == "youzan.express.order.get":
                return YouzanMockEmulator.get_mock_logistics_response(params.get("tid", "mock_order_123"))
            elif api_name == "youzan.item.get":
                return YouzanMockEmulator.get_mock_product_response(
                    params.get("item_id", 0), params.get("alias", "")
                )
            return {"response": {"success": True}}

        token = await self.get_token()
        try:
            resp = await self._client.post(
                f"{YOUZAN_API_BASE}/{api_name}/{version}?access_token={token}",
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

    async def get_product(self, item_id: int | str = 0, alias: str = "") -> dict:
        """根据商品 ID 或别名查询单品规格与实时库存。"""
        logger.info("有赞单品查询: item_id=%s, alias=%s", item_id, alias)
        params: dict = {"kdt_id": settings.YOUZAN_KDT_ID}
        if item_id:
            try:
                params["item_id"] = int(item_id)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"商品ID格式非法，期望纯数字，实际值: {item_id!r}") from exc
        if alias:
            params["alias"] = alias
        return await self._call(
            "youzan.item.get", "3.0.0",
            params,
        )

    async def list_onsale_item_ids(self) -> set[int]:
        """分页拉取有赞店铺所有在售商品的 item_id 集合。"""
        if settings.YOUZAN_MOCK_MODE:
            logger.info("有赞在售商品列表仿真拦截，返回空集合")
            return set()

        page_no = 1
        page_size = 100
        item_ids: set[int] = set()
        while True:
            result = await self._call(
                "youzan.items.onsale.get", "3.0.1",
                {
                    "kdt_id": settings.YOUZAN_KDT_ID,
                    "page_no": page_no,
                    "page_size": page_size,
                },
            )
            response = result.get("response") or {}
            items: list[dict] = response.get("items") or []
            for item in items:
                try:
                    item_ids.add(int(item["item_id"]))
                except (KeyError, ValueError, TypeError):
                    continue
            total_results = int(response.get("total_results") or 0)
            if page_no * page_size >= total_results or not items:
                break
            page_no += 1
        logger.info("有赞在售商品全量拉取完成，共 %d 条", len(item_ids))
        return item_ids

    async def close(self) -> None:
        """关闭 HTTP 连接池。"""
        if self._http:
            await self._http.aclose()
            self._http = None
