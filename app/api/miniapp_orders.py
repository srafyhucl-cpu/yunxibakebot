"""小程序订单 API 路由。"""

from typing import Any

from fastapi import APIRouter, Header, HTTPException

from app.constants.miniapp import MINIAPP_DEMO_USER_ID
from app.service.order import OrderApplicationService


def create_miniapp_orders_router(service: OrderApplicationService) -> APIRouter:
    """创建小程序订单公开路由。"""
    router = APIRouter(prefix="/api/v1/miniapp/orders", tags=["miniapp-orders"])

    @router.post("")
    async def create_order(
        payload: dict[str, Any],
        x_miniapp_user_id: str | None = Header(default=None, alias="x-miniapp-user-id"),
    ) -> dict[str, Any]:
        try:
            order = await service.create_order(
                payload,
                user_id=(x_miniapp_user_id or MINIAPP_DEMO_USER_ID).strip()
                or MINIAPP_DEMO_USER_ID,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"code": 0, "data": order}

    @router.get("")
    async def list_orders(
        x_miniapp_user_id: str | None = Header(default=None, alias="x-miniapp-user-id"),
    ) -> dict[str, Any]:
        orders = await service.list_user_orders(
            user_id=(x_miniapp_user_id or MINIAPP_DEMO_USER_ID).strip()
            or MINIAPP_DEMO_USER_ID,
        )
        return {"code": 0, "data": orders}

    @router.get("/{order_id}")
    async def get_order(
        order_id: str,
        x_miniapp_user_id: str | None = Header(default=None, alias="x-miniapp-user-id"),
    ) -> dict[str, Any]:
        try:
            order = await service.get_user_order(
                order_id,
                user_id=(x_miniapp_user_id or MINIAPP_DEMO_USER_ID).strip()
                or MINIAPP_DEMO_USER_ID,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"code": 0, "data": order}

    @router.post("/{order_id}/cancel")
    async def cancel_order(
        order_id: str,
        x_miniapp_user_id: str | None = Header(default=None, alias="x-miniapp-user-id"),
    ) -> dict[str, Any]:
        try:
            order = await service.cancel_user_order(
                order_id,
                user_id=(x_miniapp_user_id or MINIAPP_DEMO_USER_ID).strip()
                or MINIAPP_DEMO_USER_ID,
            )
        except ValueError as exc:
            message = str(exc)
            status_code = 404 if message == "订单不存在" else 400
            raise HTTPException(status_code=status_code, detail=message) from exc
        return {"code": 0, "data": order}

    @router.post("/{order_id}/mock-pay")
    async def mock_pay_order(
        order_id: str,
        x_miniapp_user_id: str | None = Header(default=None, alias="x-miniapp-user-id"),
    ) -> dict[str, Any]:
        try:
            order = await service.confirm_mock_payment(
                order_id,
                user_id=(x_miniapp_user_id or MINIAPP_DEMO_USER_ID).strip()
                or MINIAPP_DEMO_USER_ID,
            )
        except ValueError as exc:
            message = str(exc)
            status_code = 404 if message == "订单不存在" else 400
            raise HTTPException(status_code=status_code, detail=message) from exc
        return {"code": 0, "data": order}

    @router.post("/{order_id}/prepare-payment")
    async def prepare_payment(
        order_id: str,
        x_miniapp_user_id: str | None = Header(default=None, alias="x-miniapp-user-id"),
    ) -> dict[str, Any]:
        try:
            payment = await service.prepare_payment(
                order_id,
                user_id=(x_miniapp_user_id or MINIAPP_DEMO_USER_ID).strip()
                or MINIAPP_DEMO_USER_ID,
            )
        except ValueError as exc:
            message = str(exc)
            status_code = 404 if message == "订单不存在" else 400
            raise HTTPException(status_code=status_code, detail=message) from exc
        return {"code": 0, "data": payment}

    return router
