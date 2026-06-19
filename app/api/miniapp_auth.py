"""小程序认证 API 路由。"""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.service.miniapp_auth import MiniappAuthService


def create_miniapp_auth_router(service: MiniappAuthService) -> APIRouter:
    """创建小程序认证路由。"""
    router = APIRouter(prefix="/api/v1/miniapp/auth", tags=["miniapp-auth"])

    @router.post("/login")
    async def login(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            result = await service.login(str(payload.get("code", "")))
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"code": 0, "data": result}

    return router
