"""订单未支付关闭服务。"""

from app.models.order import OrderStatus
from app.repository.order_repo import OrderRepo
from app.service.order.payment_runtime import OrderPaymentRuntimeService
from app.service.order.timeline import OrderTimelineService

ADMIN_EXPIRE_NOTE = "后台关闭未支付订单"
SYSTEM_TIMEOUT_EXPIRE_NOTE = "未支付超时自动关闭"


class OrderExpirationService:
    """负责单笔和批量未支付关闭链路。"""

    def __init__(
        self,
        order_repo: OrderRepo,
        payment_service: OrderPaymentRuntimeService,
        timeline_service: OrderTimelineService,
    ) -> None:
        self._order_repo = order_repo
        self._payment_service = payment_service
        self._timeline_service = timeline_service

    async def expire_unpaid_order(self, order_id: str) -> dict:
        """后台手动关闭单笔未支付订单。"""
        expired = await self._payment_service.expire_unpaid_order(order_id, force=True)
        await self._timeline_service.record_event(
            order_id=order_id,
            status=OrderStatus.CANCELLED.value,
            operator="admin",
            note=ADMIN_EXPIRE_NOTE,
            created_at=str(expired.get("updatedAt", "")),
        )
        return await self._serialize_order(order_id)

    async def expire_timeout_unpaid_orders(self) -> dict:
        """批量扫描并关闭超时未支付订单。"""
        candidates = await self._order_repo.list_by_status(OrderStatus.PENDING.value)
        expired_orders = await self._payment_service.expire_unpaid_orders(candidates)
        for order in expired_orders:
            await self._timeline_service.record_event(
                order_id=str(order.get("id", "")),
                status=OrderStatus.CANCELLED.value,
                operator="system",
                note=SYSTEM_TIMEOUT_EXPIRE_NOTE,
                created_at=str(order.get("updatedAt", "")),
            )
        return {
            "expiredCount": len(expired_orders),
            "orders": [
                await self._serialize_order(str(order.get("id", "")))
                for order in expired_orders
            ],
        }

    async def _serialize_order(self, order_id: str) -> dict:
        order = await self._order_repo.get_order(order_id)
        if order is None:
            raise ValueError("订单不存在")
        return await self._timeline_service.serialize(order)


__all__ = [
    "ADMIN_EXPIRE_NOTE",
    "OrderExpirationService",
    "SYSTEM_TIMEOUT_EXPIRE_NOTE",
]
