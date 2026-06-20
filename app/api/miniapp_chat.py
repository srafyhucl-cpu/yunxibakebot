"""小程序客服消息 API 路由。"""

from typing import Any

from fastapi import APIRouter, Header, HTTPException

from app.constants.miniapp import MINIAPP_DEMO_USER_ID
from app.service.conversation import StorefrontConversationService


def create_miniapp_chat_router(service: StorefrontConversationService) -> APIRouter:
    """创建小程序客服消息路由。"""
    router = APIRouter(prefix="/api/v1/miniapp/chat", tags=["miniapp-chat"])

    @router.post("/messages")
    async def send_message(
        payload: dict[str, Any],
        x_miniapp_user_id: str | None = Header(default=None, alias="x-miniapp-user-id"),
    ) -> dict[str, Any]:
        try:
            result = await service.send_message(
                str(payload.get("content", "")),
                user_id=(x_miniapp_user_id or MINIAPP_DEMO_USER_ID).strip()
                or MINIAPP_DEMO_USER_ID,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"code": 0, "data": result}

    @router.get("/messages")
    async def list_messages(
        x_miniapp_user_id: str | None = Header(default=None, alias="x-miniapp-user-id"),
    ) -> dict[str, Any]:
        payload = await service.get_chat_payload(
            user_id=(x_miniapp_user_id or MINIAPP_DEMO_USER_ID).strip()
            or MINIAPP_DEMO_USER_ID,
        )
        return {"code": 0, "data": payload}

    @router.post("/transfer")
    async def request_transfer(
        payload: dict[str, Any] | None = None,
        x_miniapp_user_id: str | None = Header(default=None, alias="x-miniapp-user-id"),
    ) -> dict[str, Any]:
        try:
            result = await service.request_human_transfer(
                str((payload or {}).get("reason", "")),
                user_id=(x_miniapp_user_id or MINIAPP_DEMO_USER_ID).strip()
                or MINIAPP_DEMO_USER_ID,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"code": 0, "data": result}

    return router
