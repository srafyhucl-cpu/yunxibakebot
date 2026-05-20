"""有赞 Webhook 高并发重试去重集成测试。"""

import asyncio
import pytest
import httpx
from fastapi import FastAPI

from app.config import settings
from app.api.webhook import create_webhook_router
from app.service.youzan import webhook as webhook_module


class MockSessionRepo:
    def __init__(self) -> None:
        self._db = None  # 传递 None 使得 YouzanClient 在 Mock 模式下跳过真实的 DB 保存


class MockMessageRepo:
    async def has_processed(self, msg_id: str) -> bool:
        # 模拟数据库中尚没有处理该消息
        return False


class MockChatService:
    def __init__(self) -> None:
        self._session_repo = MockSessionRepo()
        self._message_repo = MockMessageRepo()
        self.handle_count = 0

    async def handle_message_and_reply_youzan(self, buyer_id: str, content: str, msg_id: str) -> str:
        self.handle_count += 1
        # 模拟后台 AI 判定与知识检索延迟 50ms
        await asyncio.sleep(0.05)
        return "仿真自动回复"


@pytest.mark.asyncio
async def test_youzan_webhook_concurrency_deduplication(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试在高并发重复报文打入时，Webhook 层的秒回防御与后台协程分流是否 100% 幂等。"""
    # 1. 强制开启 Mock 模式
    monkeypatch.setattr(settings, "YOUZAN_MOCK_MODE", True)
    monkeypatch.setattr(settings, "YOUZAN_WEBHOOK_TOKEN", "mock_webhook_token_xyz")

    # 2. 模拟签名验证：总是验证通过 (需在消费端的 webhook 路由模块上打桩)
    from app.api import webhook as api_webhook_module
    def fake_verify_signature(secret: str, raw_body: bytes, signature_header: str) -> bool:
        return True

    monkeypatch.setattr(api_webhook_module, "verify_youzan_signature", fake_verify_signature)

    # 3. 创建孤立的测试 app 并注入模拟的 ChatService
    chat_service = MockChatService()
    test_app = FastAPI()
    test_app.include_router(create_webhook_router(chat_service))

    # 4. 准备 3 份具有完全相同 msg_id 的重复并发回调请求
    payload = {
        "msg_id": "duplicate_msg_id_100200",
        "msg_type": "text",
        "buyer_id": "buyer_999",
        "content": {
            "text": "提拉米苏多少钱"
        }
    }

    # 5. 使用 httpx.AsyncClient 并发打入接口
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 连续发送 3 次高频请求
        tasks = []
        for _ in range(3):
            tasks.append(
                client.post(
                    "/api/v1/webhook/youzan",
                    json=payload,
                    headers={"X-Youzan-Signature": "dummy_sig"}
                )
            )

        responses = await asyncio.gather(*tasks)

        # 验证所有 3 个请求是否全部获得极速返回 (200) 并秒回复 success
        for r in responses:
            assert r.status_code == 200
            assert r.json() == {"code": 0, "msg": "success"}

        # 等待后台任务完全执行完
        await asyncio.sleep(0.1)

        # 核心断言：验证虽然并发调用了 3 次接口，但 chat_service.handle_message 有且仅被触发处理了 1 次
        assert chat_service.handle_count == 1
