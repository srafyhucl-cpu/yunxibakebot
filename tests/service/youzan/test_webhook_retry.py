"""Concurrency deduplication tests for the Youzan webhook."""

import asyncio

import httpx
import pytest
from fastapi import FastAPI

from app.api.webhook import create_webhook_router
from app.config import settings


class MockSessionRepo:
    def __init__(self) -> None:
        self._db = None


class MockMessageRepo:
    async def has_processed(self, msg_id: str) -> bool:
        return False


class MockChatService:
    def __init__(self) -> None:
        self._session_repo = MockSessionRepo()
        self._message_repo = MockMessageRepo()
        self.handle_count = 0

    async def handle_message_and_reply_youzan(self, buyer_id: str, content: str, msg_id: str) -> str:
        self.handle_count += 1
        await asyncio.sleep(0.05)
        return "mock reply"


@pytest.mark.asyncio
async def test_youzan_webhook_concurrency_deduplication(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "YOUZAN_MOCK_MODE", True)
    monkeypatch.setattr(settings, "YOUZAN_CLIENT_ID", "mock_client_id")
    monkeypatch.setattr(settings, "YOUZAN_CLIENT_SECRET", "mock_client_secret")

    from app.api import webhook as webhook_module

    def fake_verify_signature(client_id: str, client_secret: str, raw_body: bytes, signature_header: str) -> bool:
        return True

    monkeypatch.setattr(webhook_module, "verify_youzan_signature", fake_verify_signature)

    chat_service = MockChatService()
    test_app = FastAPI()
    test_app.include_router(create_webhook_router(chat_service))

    payload = {
        "msg_id": "duplicate_msg_id_100200",
        "msg_type": "text",
        "buyer_id": "buyer_999",
        "content": {
            "text": "提拉米苏多少钱",
        },
    }

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        tasks = [
            client.post(
                "/api/v1/webhook/youzan",
                json=payload,
                headers={"event-sign": "dummy_sig"},
            )
            for _ in range(3)
        ]
        responses = await asyncio.gather(*tasks)

        for response in responses:
            assert response.status_code == 200
            assert response.json() == {"code": 0, "msg": "success"}

        await asyncio.sleep(0.1)

    assert chat_service.handle_count == 1
