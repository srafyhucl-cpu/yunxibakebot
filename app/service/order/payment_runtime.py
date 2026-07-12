"""订单支付真实实现。"""

from datetime import datetime, timedelta
from app.config import settings
from app.models.order import Order, OrderStatus
from app.repository.order_repo import OrderRepo
from app.repository.order_event_repo import OrderEventRepo
from app.service.integrations.wechat_pay import (
    PAYMENT_SIGN_TYPE,
    WECHAT_PAY_SUCCESS_STATE,
    WechatPayIntegrationService,
    WechatPayPrepayResult,
)
from app.service.order.inventory import OrderInventoryService
from app.service.order.payment_notification import WechatPaymentNotificationService
from app.service.order.payment_state import (
    PAYMENT_METHOD_MOCK,
    PAYMENT_METHOD_WECHAT,
    PAYMENT_MODE_MOCK,
    PAYMENT_MODE_WECHAT,
    PAYMENT_STATUS_EXPIRED,
    PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_UNPAID,
    PAYMENT_TIMEOUT_MINUTES,
    PaymentSession,
    TIME_FORMAT,
    build_initial_payment,
    build_mock_payment_session,
    build_order_description,
    dumps_payment,
    extract_openid,
    loads_json_object,
    loads_payment,
    now_text,
    parse_time,
    status_value,
)
from app.service.order.serialization import OrderSerializationService


class OrderPaymentRuntimeService:
    """处理支付确认和未支付超时释放。"""

    def __init__(
        self,
        order_repo: OrderRepo,
        inventory_service: OrderInventoryService,
        wechat_pay_service: WechatPayIntegrationService | None = None,
        event_repo: OrderEventRepo | None = None,
    ) -> None:
        self._order_repo = order_repo
        self._inventory_service = inventory_service
        self._serializer = OrderSerializationService()
        self._wechat_pay_service = wechat_pay_service or WechatPayIntegrationService()
        self._notification_service = WechatPaymentNotificationService(
            order_repo, event_repo
        )

    async def prepare_payment(self, order_id: str, *, user_id: str) -> PaymentSession:
        """准备订单支付会话。"""
        order = await self._get_user_order(order_id, user_id=user_id)
        current_status = status_value(order)
        if current_status == OrderStatus.CANCELLED.value:
            raise ValueError("订单已取消")
        payment = loads_payment(order.payment)
        payment_status = str(payment.get("status", PAYMENT_STATUS_UNPAID))
        if payment_status == PAYMENT_STATUS_PAID:
            return PaymentSession(
                mode=PAYMENT_MODE_WECHAT,
                order_id=order.id,
                payment_method=str(
                    payment.get("method", PAYMENT_METHOD_WECHAT)
                    or PAYMENT_METHOD_WECHAT
                ),
                payment_status=PAYMENT_STATUS_PAID,
                payload={},
            )
        if payment_status == PAYMENT_STATUS_EXPIRED:
            raise ValueError("订单支付已超时")
        if not self._wechat_pay_ready():
            if not settings.ALLOW_MOCK_PAYMENT:
                raise ValueError("微信支付未配置，生产环境不提供 mock 支付")
            return build_mock_payment_session(order.id)
        prepay = await self._create_wechat_jsapi_prepay(order)
        payment_params = self._build_wechat_payment_params(prepay.prepay_id)
        return PaymentSession(
            mode=PAYMENT_MODE_WECHAT,
            order_id=order.id,
            payment_method=PAYMENT_METHOD_WECHAT,
            payment_status=PAYMENT_STATUS_UNPAID,
            payload=payment_params,
        )

    async def confirm_mock_payment(self, order_id: str, *, user_id: str) -> dict:
        """MVP mock 支付确认，真实微信支付接入后复用同一状态流转。"""
        if not settings.ALLOW_MOCK_PAYMENT:
            raise ValueError("生产环境已禁用 mock 支付")
        order = await self._get_user_order(order_id, user_id=user_id)
        current_status = status_value(order)
        if current_status == OrderStatus.CANCELLED.value:
            raise ValueError("订单已取消")
        payment = loads_payment(order.payment)
        payment_status = str(payment.get("status", PAYMENT_STATUS_UNPAID))
        if payment_status == PAYMENT_STATUS_PAID:
            return self._serializer.serialize(order)
        if payment_status == PAYMENT_STATUS_EXPIRED:
            raise ValueError("订单支付已超时")
        now = now_text()
        payment.update(
            {
                "status": PAYMENT_STATUS_PAID,
                "method": PAYMENT_METHOD_MOCK,
                "paidAt": now,
            }
        )
        updated = await self._order_repo.update_payment(
            order.id, dumps_payment(payment), now
        )
        if updated is None:
            raise ValueError("订单不存在")
        return self._serializer.serialize(updated)

    async def handle_wechat_payment_notify(
        self,
        *,
        raw_body: bytes,
        headers: dict[str, str],
    ) -> dict:
        """处理微信支付结果通知。"""
        if not self._verify_wechat_notify_signature(raw_body, headers):
            raise ValueError("微信支付通知签名无效")
        payload = loads_json_object(raw_body.decode("utf-8"))
        resource = payload.get("resource")
        if not isinstance(resource, dict):
            raise ValueError("微信支付通知缺少 resource")
        transaction = self._decrypt_wechat_resource(resource)
        order_id = str(transaction.get("out_trade_no", "")).strip()
        if not order_id:
            raise ValueError("微信支付通知缺少订单号")
        trade_state = str(transaction.get("trade_state", "")).strip()
        if trade_state != WECHAT_PAY_SUCCESS_STATE:
            return {"orderId": order_id, "ignored": True, "tradeState": trade_state}
        await self._validate_wechat_transaction(transaction)
        paid_at = self._wechat_pay_service.format_success_time(
            str(transaction.get("success_time", ""))
        )
        transaction_id = str(transaction.get("transaction_id", "")).strip()
        updated = await self._mark_wechat_payment_paid(
            order_id,
            paid_at=paid_at,
            transaction_id=transaction_id,
        )
        return self._serializer.serialize(updated)

    async def expire_unpaid_order(
        self,
        order_id: str,
        *,
        now: datetime | None = None,
        force: bool = False,
    ) -> dict:
        """关闭单个未支付订单并释放预占库存。"""
        order = await self._order_repo.get_order(order_id)
        if order is None:
            raise ValueError("订单不存在")
        current_time = now or datetime.now()
        if force and not self._is_unpaid_active(order):
            return self._serializer.serialize(order)
        if not force and not self._is_expirable(order, current_time):
            return self._serializer.serialize(order)
        expired = await self._expire_order(order, current_time)
        return self._serializer.serialize(expired)

    async def expire_unpaid_orders(
        self, orders: list[Order], *, now: datetime | None = None
    ) -> list[dict]:
        """批量关闭超时未支付订单。"""
        current_time = now or datetime.now()
        expired_orders: list[dict] = []
        for order in orders:
            if not self._is_expirable(order, current_time):
                continue
            expired = await self._expire_order(order, current_time)
            expired_orders.append(self._serializer.serialize(expired))
        return expired_orders

    async def _get_user_order(self, order_id: str, *, user_id: str) -> Order:
        order = await self._order_repo.get_order(order_id)
        if order is None or order.user_id != user_id:
            raise ValueError("订单不存在")
        return order

    async def _expire_order(self, order: Order, now: datetime) -> Order:
        payment = loads_payment(order.payment)
        now_text = now.strftime(TIME_FORMAT)
        payment.update(
            {
                "status": PAYMENT_STATUS_EXPIRED,
                "expiredAt": now_text,
                "expiredReason": "payment_timeout",
            }
        )
        updated = await self._order_repo.update_payment(
            order.id, dumps_payment(payment), now_text
        )
        if updated is None:
            raise ValueError("订单不存在")
        await self._inventory_service.release_reserved_inventory(
            self._inventory_service.items_from_order(updated)
        )
        cancelled = await self._order_repo.update_status(
            order.id,
            OrderStatus.CANCELLED.value,
            now_text,
        )
        if cancelled is None:
            raise ValueError("订单不存在")
        return cancelled

    async def _mark_wechat_payment_paid(
        self,
        order_id: str,
        *,
        paid_at: str,
        transaction_id: str,
    ) -> Order:
        order = await self._order_repo.get_order(order_id)
        if order is None:
            raise ValueError("订单不存在")
        if status_value(order) == OrderStatus.CANCELLED.value:
            raise ValueError("订单已取消")
        return await self._notification_service.mark_paid(
            order_id,
            paid_at=paid_at,
            transaction_id=transaction_id,
        )

    async def _validate_wechat_transaction(self, transaction: dict) -> None:
        """委托微信通知业务合同校验。"""
        await self._notification_service.validate_transaction(transaction)

    def _is_expirable(self, order: Order, now: datetime) -> bool:
        if not self._is_unpaid_active(order):
            return False
        payment = loads_payment(order.payment)
        created_at = parse_time(str(payment.get("createdAt") or order.created_at))
        return created_at is not None and now - created_at >= timedelta(
            minutes=PAYMENT_TIMEOUT_MINUTES
        )

    def _is_unpaid_active(self, order: Order) -> bool:
        if status_value(order) == OrderStatus.CANCELLED.value:
            return False
        payment = loads_payment(order.payment)
        return (
            str(payment.get("status", PAYMENT_STATUS_UNPAID)) == PAYMENT_STATUS_UNPAID
        )

    def _wechat_pay_ready(self) -> bool:
        return self._wechat_pay_service.is_ready()

    def _verify_wechat_notify_signature(
        self, raw_body: bytes, headers: dict[str, str]
    ) -> bool:
        return self._wechat_pay_service.verify_notify_signature(raw_body, headers)

    def _decrypt_wechat_resource(self, resource: dict) -> dict:
        return self._wechat_pay_service.decrypt_notify_resource(resource)

    async def _create_wechat_jsapi_prepay(self, order: Order) -> WechatPayPrepayResult:
        total_fen = int(round(float(order.total_amount) * 100))
        payer_openid = extract_openid(order.user_id)
        if not payer_openid:
            raise ValueError("当前用户未绑定微信 openid")
        return await self._wechat_pay_service.create_jsapi_prepay(
            order_id=order.id,
            total_fen=total_fen,
            description=build_order_description(order),
            payer_openid=payer_openid,
        )

    def _build_wechat_payment_params(self, prepay_id: str) -> dict:
        return self._wechat_pay_service.build_payment_params(
            prepay_id,
            signer=self._sign_with_rsa,
        )

    def _sign_with_rsa(self, message: str) -> str:
        return self._wechat_pay_service.sign_with_rsa(message)


__all__ = [
    "OrderPaymentRuntimeService",
    "PAYMENT_METHOD_MOCK",
    "PAYMENT_METHOD_WECHAT",
    "PAYMENT_MODE_MOCK",
    "PAYMENT_MODE_WECHAT",
    "PAYMENT_SIGN_TYPE",
    "PAYMENT_STATUS_EXPIRED",
    "PAYMENT_STATUS_PAID",
    "PAYMENT_STATUS_UNPAID",
    "PAYMENT_TIMEOUT_MINUTES",
    "PaymentSession",
    "TIME_FORMAT",
    "WECHAT_PAY_SUCCESS_STATE",
    "WechatPayPrepayResult",
    "build_initial_payment",
    "build_mock_payment_session",
]
