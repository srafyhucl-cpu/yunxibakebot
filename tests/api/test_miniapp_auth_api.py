"""小程序认证 API 测试。"""

import httpx
import pytest
from fastapi import FastAPI

from app.api.miniapp_auth import create_miniapp_auth_router
from app.service.channels.storefront import StorefrontAuthService


@pytest.mark.asyncio
async def test_miniapp_auth_login_returns_demo_session_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """未配置微信 AppID/Secret 时返回稳定 demo 会话。"""
    monkeypatch.setattr(
        "app.service.channels.storefront.auth.settings.WECHAT_MINIAPP_APP_ID",
        "",
    )
    monkeypatch.setattr(
        "app.service.channels.storefront.auth.settings.WECHAT_MINIAPP_APP_SECRET",
        "",
    )
    app = FastAPI()
    app.include_router(create_miniapp_auth_router(StorefrontAuthService()))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/miniapp/auth/login", json={"code": "dev-code"}
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["userId"].startswith("miniapp-demo-user-")
    assert data["openid"] == ""
    assert data["sessionReady"] is True
    assert data["isDemo"] is True


@pytest.mark.asyncio
async def test_miniapp_auth_login_returns_wechat_user_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """配置微信 AppID/Secret 后应按 openid 构造小程序用户 ID。"""

    async def fake_request(self, code: str) -> dict:
        assert code == "wx-code"
        return {"openid": "openid_abc"}

    monkeypatch.setattr(
        "app.service.channels.storefront.auth.settings.WECHAT_MINIAPP_APP_ID",
        "wx-app",
    )
    monkeypatch.setattr(
        "app.service.channels.storefront.auth.settings.WECHAT_MINIAPP_APP_SECRET",
        "secret",
    )
    monkeypatch.setattr(
        StorefrontAuthService,
        "_request_wechat_session",
        fake_request,
    )
    app = FastAPI()
    app.include_router(create_miniapp_auth_router(StorefrontAuthService()))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/miniapp/auth/login", json={"code": "wx-code"}
        )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "userId": "wx_openid_abc",
        "openid": "openid_abc",
        "sessionReady": True,
        "isDemo": False,
    }
