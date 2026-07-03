from __future__ import annotations

import base64
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.integrations.wecom_intelligent_bot import (
    create_wecom_intelligent_bot_router,
)
from app.config import settings
from app.service.wecom.crypto import (
    decrypt,
    encrypt,
    generate_signature,
    verify_signature,
)
from app.service.wecom.intelligent_bot_tools import WeComBotBusinessToolService


TOKEN = "callback-token"
AES_KEY = base64.b64encode(b"1" * 32).decode("utf-8").rstrip("=")


class _FakeCatalogService:
    async def list_products(self, *, featured: bool = False) -> list[dict]:
        return [
            {
                "id": "71001",
                "title": "草莓蛋糕",
                "priceFen": 26800,
                "stock": 6,
                "categoryName": "生日蛋糕",
                "soldText": "已售 12",
                "tags": ["生日蛋糕", "草莓"],
            }
        ]


class _FakeEmployeeAgentService:
    async def answer(self, query: str) -> str:
        return f"agent:{query}"


def _client(monkeypatch, *, agent_service=None) -> TestClient:
    monkeypatch.setattr(settings, "WECOM_INTELLIGENT_BOT_TOKEN", TOKEN)
    monkeypatch.setattr(settings, "WECOM_INTELLIGENT_BOT_ENCODING_AES_KEY", AES_KEY)
    app = FastAPI()
    app.include_router(
        create_wecom_intelligent_bot_router(
            tool_service=WeComBotBusinessToolService(
                catalog_service=_FakeCatalogService(),
            ),
            agent_service=agent_service,
        )
    )
    return TestClient(app)


def _signed_query(msg_encrypt: str, *, timestamp: str = "1783000000") -> dict[str, str]:
    nonce = "nonce-1"
    return {
        "msg_signature": generate_signature(TOKEN, timestamp, nonce, msg_encrypt),
        "timestamp": timestamp,
        "nonce": nonce,
    }


def test_callback_get_returns_decrypted_echostr(monkeypatch) -> None:
    client = _client(monkeypatch)
    echostr = encrypt(AES_KEY, "ok", "")

    response = client.get(
        "/api/v1/wecom/intelligent-bot/callback",
        params={**_signed_query(echostr), "echostr": echostr},
    )

    assert response.status_code == 200
    assert response.text == "ok"


def test_callback_post_returns_encrypted_product_reply(monkeypatch) -> None:
    client = _client(monkeypatch)
    plaintext = json.dumps(
        {
            "msgid": "msg-001",
            "aibotid": "bot-001",
            "chattype": "group",
            "msgtype": "text",
            "text": {"content": "@芸熙助手 草莓蛋糕还有库存吗"},
        },
        ensure_ascii=False,
    )
    msg_encrypt = encrypt(AES_KEY, plaintext, "")

    response = client.post(
        "/api/v1/wecom/intelligent-bot/callback",
        params=_signed_query(msg_encrypt),
        json={"encrypt": msg_encrypt},
    )

    assert response.status_code == 200
    payload = response.json()
    assert verify_signature(
        TOKEN,
        str(payload["timestamp"]),
        payload["nonce"],
        payload["encrypt"],
        payload["msgsignature"],
    )
    reply = json.loads(decrypt(AES_KEY, payload["encrypt"]))
    assert reply["msgtype"] == "stream"
    assert reply["stream"]["id"] == "msg-001"
    assert reply["stream"]["finish"] is True
    assert "草莓蛋糕" in reply["stream"]["content"]
    assert "库存 6" in reply["stream"]["content"]


def test_callback_post_uses_employee_agent_when_injected(monkeypatch) -> None:
    client = _client(monkeypatch, agent_service=_FakeEmployeeAgentService())
    plaintext = json.dumps(
        {
            "msgid": "msg-agent-001",
            "aibotid": "bot-001",
            "chattype": "group",
            "msgtype": "text",
            "text": {"content": "今天一共多少订单"},
        },
        ensure_ascii=False,
    )
    msg_encrypt = encrypt(AES_KEY, plaintext, "")

    response = client.post(
        "/api/v1/wecom/intelligent-bot/callback",
        params=_signed_query(msg_encrypt),
        json={"encrypt": msg_encrypt},
    )

    assert response.status_code == 200
    payload = response.json()
    reply = json.loads(decrypt(AES_KEY, payload["encrypt"]))
    assert reply["stream"]["content"] == "agent:今天一共多少订单"


def test_callback_post_rejects_invalid_signature(monkeypatch) -> None:
    client = _client(monkeypatch)
    msg_encrypt = encrypt(AES_KEY, '{"msgtype":"text","text":{"content":"test"}}', "")

    response = client.post(
        "/api/v1/wecom/intelligent-bot/callback",
        params={
            "msg_signature": "wrong-signature",
            "timestamp": "1783000000",
            "nonce": "nonce-1",
        },
        json={"encrypt": msg_encrypt},
    )

    assert response.status_code == 403
    assert response.text == "签名验证失败"
