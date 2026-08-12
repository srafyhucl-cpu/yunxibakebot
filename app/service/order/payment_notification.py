"""微信支付交易通知的业务校验与入账。"""

from decimal import Decimal, InvalidOperation

from app.config import settings
from app.models.order import Order, OrderEvent, OrderStatus
from app.repository.order_event_repo import OrderEventRepo
from app.repository.order_repo import OrderRepo
from app.service.order.payment_state import (
    PAYMENT_METHOD_WECHAT,
    PAYMENT_STATUS_EXPIRED,
    PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_PARTIAL,
    PAYMENT_STATUS_UNPAID,
    dumps_payment,
    loads_payment,
    now_text,
    status_value,
)


class WechatPaymentNotificationService:
    """负责微信通知字段校验、交易号认领和支付事件写入。"""

    def __init__(
        self,
        order_repo: OrderRepo,
        event_repo: OrderEventRepo | None = None,
    ) -> None:
        self._order_repo = order_repo
        self._event_repo = event_repo

    async def validate_transaction(self, transaction: dict) -> None:
        """校验微信通知的商户、应用、金额、币种和交易号。"""
        if str(transaction.get("mchid", "")).strip() != settings.WECHAT_PAY_MCH_ID:
            raise ValueError("微信支付通知商户号不匹配")
        if str(transaction.get("appid", "")).strip() != settings.WECHAT_MINIAPP_APP_ID:
            raise ValueError("微信支付通知 appid 不匹配")
        if str(transaction.get("currency", "")).strip() != "CNY":
            raise ValueError("微信支付通知币种不匹配")
        transaction_id = str(transaction.get("transaction_id", "")).strip()
        if not transaction_id:
            raise ValueError("微信支付通知缺少交易号")
        try:
            total_fen = int(transaction.get("amount", {}).get("total"))
        except (AttributeError, TypeError, ValueError):
            raise ValueError("微信支付通知金额无效") from None
        order_id = str(transaction.get("out_trade_no", "")).strip()
        order = await self._order_repo.get_order(order_id)
        if order is None:
            raise ValueError("订单不存在")
        try:
            expected_fen = int(Decimal(str(order.total_amount)) * 100)
        except (InvalidOperation, ValueError):
            raise ValueError("订单金额无效") from None
        payment = loads_payment(order.payment)
        if str(payment.get("status", PAYMENT_STATUS_UNPAID)) == PAYMENT_STATUS_PARTIAL:
            remain_fen = int(payment.get("remainFen", 0) or 0)
            if remain_fen <= 0 or remain_fen >= expected_fen:
                raise ValueError("组合支付差额金额无效")
            expected_fen = remain_fen
        if total_fen != expected_fen:
            raise ValueError("微信支付通知金额不匹配")

    async def mark_paid(
        self,
        order_id: str,
        *,
        paid_at: str,
        transaction_id: str,
    ) -> Order:
        """原子认领交易号并把订单置为已支付。"""
        order = await self._order_repo.get_order(order_id)
        if order is None:
            raise ValueError("订单不存在")
        if status_value(order) == OrderStatus.CANCELLED.value:
            raise ValueError("订单已取消")
        payment = loads_payment(order.payment)
        payment_status = str(payment.get("status", PAYMENT_STATUS_UNPAID))
        if payment_status == PAYMENT_STATUS_PAID:
            if str(payment.get("transactionId", "")) == transaction_id:
                return order
            raise ValueError("订单已绑定其他支付交易号")
        if payment_status == PAYMENT_STATUS_EXPIRED:
            raise ValueError("订单支付已超时")
        if not transaction_id:
            raise ValueError("微信支付通知缺少交易号")
        if payment_status == PAYMENT_STATUS_PARTIAL:
            payment.update(
                {
                    "status": PAYMENT_STATUS_PAID,
                    "paidAt": paid_at or now_text(),
                    "transactionId": transaction_id,
                }
            )
            updated = await self._order_repo.update_payment_to_paid_if_unpaid_or_partial_active(
                order.id, dumps_payment(payment), payment["paidAt"]
            )
        else:
            payment.update(
                {
                    "status": PAYMENT_STATUS_PAID,
                    "method": PAYMENT_METHOD_WECHAT,
                    "paidAt": paid_at or now_text(),
                    "transactionId": transaction_id,
                }
            )
            updated = await self._order_repo.update_payment_if_unpaid_active(
                order.id, dumps_payment(payment), payment["paidAt"]
            )
        if updated is None:
            latest = await self._order_repo.get_order(order.id)
            if latest is None:
                raise ValueError("订单不存在")
            latest_payment = loads_payment(latest.payment)
            if status_value(latest) == OrderStatus.CANCELLED.value:
                raise ValueError("订单已取消")
            if (
                str(latest_payment.get("status", PAYMENT_STATUS_UNPAID))
                == PAYMENT_STATUS_PAID
            ):
                if str(latest_payment.get("transactionId", "")) == transaction_id:
                    return latest
                raise ValueError("订单已绑定其他支付交易号")
            raise ValueError("订单支付状态更新冲突")
        await self._claim_transaction(transaction_id, order_id)
        await self._record_paid_event(updated, payment["paidAt"])
        return updated

    async def _claim_transaction(self, transaction_id: str, order_id: str) -> None:
        existing_order_id = await self._order_repo.get_payment_transaction_order_id(
            transaction_id
        )
        if existing_order_id and existing_order_id != order_id:
            raise ValueError("微信交易号已绑定其他订单")
        claimed = await self._order_repo.claim_payment_transaction(
            transaction_id, order_id, now_text()
        )
        if claimed:
            return
        existing_order_id = await self._order_repo.get_payment_transaction_order_id(
            transaction_id
        )
        if existing_order_id != order_id:
            raise ValueError("微信交易号已绑定其他订单")
        latest = await self._order_repo.get_order(order_id)
        if latest is None:
            raise ValueError("订单不存在")
        latest_payment = loads_payment(latest.payment)
        if str(latest_payment.get("transactionId", "")) == transaction_id:
            return
        raise ValueError("微信交易号重复通知状态异常")

    async def _record_paid_event(self, order: Order, paid_at: str) -> None:
        if self._event_repo is None:
            return
        await self._event_repo.add(
            OrderEvent(
                order_id=order.id,
                status=PAYMENT_STATUS_PAID,
                operator="wechat-pay",
                note="微信支付通知确认到账",
                created_at=paid_at,
            )
        )


__all__ = ["WechatPaymentNotificationService"]
