"""小程序收货地址 API。"""

from typing import Any

from fastapi import APIRouter, Header, HTTPException

from app.constants.miniapp import MINIAPP_DEMO_USER_ID
from app.service.miniapp_address import MiniappAddressService


def _miniapp_user_id(value: str | None) -> str:
    return (value or MINIAPP_DEMO_USER_ID).strip() or MINIAPP_DEMO_USER_ID


def create_miniapp_addresses_router(service: MiniappAddressService) -> APIRouter:
    """创建小程序地址簿路由。"""
    router = APIRouter(prefix="/api/v1/miniapp/addresses", tags=["miniapp-addresses"])

    @router.get("")
    async def list_addresses(
        x_miniapp_user_id: str | None = Header(default=None, alias="x-miniapp-user-id"),
    ) -> dict[str, Any]:
        return {
            "code": 0,
            "data": await service.list_addresses(_miniapp_user_id(x_miniapp_user_id)),
        }

    @router.post("")
    async def save_address(
        payload: dict[str, Any],
        x_miniapp_user_id: str | None = Header(default=None, alias="x-miniapp-user-id"),
    ) -> dict[str, Any]:
        try:
            item = await service.save_address(
                payload, _miniapp_user_id(x_miniapp_user_id)
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"code": 0, "data": item}

    @router.post("/{address_id}/default")
    async def set_default_address(
        address_id: str,
        x_miniapp_user_id: str | None = Header(default=None, alias="x-miniapp-user-id"),
    ) -> dict[str, Any]:
        try:
            item = await service.set_default(
                address_id, _miniapp_user_id(x_miniapp_user_id)
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"code": 0, "data": item}

    @router.delete("/{address_id}")
    async def delete_address(
        address_id: str,
        x_miniapp_user_id: str | None = Header(default=None, alias="x-miniapp-user-id"),
    ) -> dict[str, Any]:
        try:
            items = await service.delete_address(
                address_id, _miniapp_user_id(x_miniapp_user_id)
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"code": 0, "data": items}

    return router
