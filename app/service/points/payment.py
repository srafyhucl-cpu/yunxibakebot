"""积分支付联动：抵扣快照、支付发分、退款收回。"""

from app.logger import setup_logger
from app.models.order import Order
from app.repository.customer_master_repo import CustomerMasterRepo
from app.repository.member_balance_repo import MemberBalanceRepo
from app.repository.order_repo import OrderRepo
from app.repository.points_ledger_repo import PointsLedgerRepo
from app.service.order.payment_state import (
    PAYMENT_METHOD_COMBINED,
    PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_PARTIAL,
    PAYMENT_STATUS_UNPAID,
    dumps_payment,
    loads_payment,
    now_text,
    status_value,
)
from app.service.points.ledger import PointsLedgerService
from app.service.points.rules import (
    award_points,
    points_to_fen,
    refund_reversal,
)

logger = setup_logger()

POINTS_AWARD_EVENT = "order_award"
POINTS_REDEEM_EVENT = "order_redeem"
POINTS_REFUND_EVENT = "order_refund"


class PointsPaymentService:
    """负责订单积分抵扣快照、支付发分与退款收回。"""

    def __init__(
        self,
        ledger_service: PointsLedgerService | None = None,
        order_repo: OrderRepo | None = None,
    ) -> None:
        self._order_repo = order_repo or OrderRepo(None)
        if ledger_service is not None:
            self._ledger_service = ledger_service
        else:
            # 与订单仓储共用同一数据源，保证生产（db_conn_var）与测试注入连接一致
            db = self._order_repo._db
            self._ledger_service = PointsLedgerService(
                balance_repo=MemberBalanceRepo(db),
                ledger_repo=PointsLedgerRepo(db),
            )

    async def apply_points_snapshot(
        self,
        order: Order,
        *,
        user_id: str,
        points_used: int,
        mobile: str,
    ) -> dict:
        """校验并写积分抵扣 partial 快照（不扣积分账）。"""
        payment = loads_payment(order.payment)
        payment_status = str(payment.get("status", PAYMENT_STATUS_UNPAID))
        if payment_status == PAYMENT_STATUS_PAID:
            raise ValueError("订单已支付")
        total_fen = self._total_fen(order)
        balance_fen = int(payment.get("balanceFen", 0) or 0)
        points_fen = points_to_fen(points_used)
        if points_fen <= 0:
            raise ValueError("积分抵扣至少 100 分")
        if points_fen > total_fen - balance_fen:
            raise ValueError("积分抵扣金额超过剩余应付")
        remain_fen = total_fen - balance_fen - points_fen
        now = now_text()
        from app.service.order.payment_state import build_points_payment

        snapshot = build_points_payment(
            now,
            balance_fen=balance_fen,
            points_fen=points_fen,
            points_used=points_used,
            remain_fen=remain_fen,
        )
        updated = await self._order_repo.update_payment_to_partial_if_unpaid_or_partial_active(
            order.id, dumps_payment(snapshot), now
        )
        if updated is None:
            raise ValueError("订单支付状态更新冲突")
        # 快照为独立原子写，立即提交以保持后续确认事务状态一致
        await self._order_repo._db.commit()
        return {
            "orderId": order.id,
            "status": status_value(updated),
            "paymentStatus": PAYMENT_STATUS_PARTIAL,
            "paymentMethod": PAYMENT_METHOD_COMBINED,
            "pointsFen": points_fen,
            "pointsUsed": points_used,
            "remainFen": remain_fen,
        }

    async def award_on_payment(self, order: Order) -> None:
        """支付成功后发分并扣抵扣（幂等）。"""
        payment = loads_payment(order.payment)
        if str(payment.get("status", PAYMENT_STATUS_UNPAID)) != PAYMENT_STATUS_PAID:
            return
        if int(payment.get("pointsAwarded", 0) or 0) > 0:
            return
        points_used = int(payment.get("pointsUsed", 0) or 0)
        mobile = await self._try_resolve_mobile(order.user_id)
        if mobile is None:
            return
        total_fen = self._total_fen(order)
        balance_fen = int(payment.get("balanceFen", 0) or 0)
        points_fen = int(payment.get("pointsFen", 0) or 0)
        cash_fen = max(0, total_fen - balance_fen - points_fen)
        award = award_points(cash_fen)
        if points_used > 0:
            await self._ledger_service.deduct(
                mobile=mobile,
                amount=points_used,
                biz_type=POINTS_REDEEM_EVENT,
                biz_id=order.id,
                unique_id=f"points:redeem:{order.id}",
                event_type=POINTS_REDEEM_EVENT,
            )
        if award > 0:
            await self._ledger_service.credit(
                mobile=mobile,
                amount=award,
                biz_type=POINTS_AWARD_EVENT,
                biz_id=order.id,
                unique_id=f"points:award:{order.id}",
                event_type=POINTS_AWARD_EVENT,
            )
        await self._record_awarded(order, points_used, award)

    async def refund_points(self, order: Order) -> None:
        """按支付快照退回抵扣积分并收回已发积分（幂等）。"""
        payment = loads_payment(order.payment)
        points_used = int(payment.get("pointsUsed", 0) or 0)
        points_awarded = int(payment.get("pointsAwarded", 0) or 0)
        if points_used <= 0 and points_awarded <= 0:
            return
        mobile = await self._try_resolve_mobile(order.user_id)
        if mobile is None:
            return
        return_points, clawback_points = refund_reversal(points_used, points_awarded)
        if return_points > 0:
            await self._ledger_service.credit(
                mobile=mobile,
                amount=return_points,
                biz_type=POINTS_REFUND_EVENT,
                biz_id=order.id,
                unique_id=f"points:refund:{order.id}",
                event_type=POINTS_REFUND_EVENT,
            )
        if clawback_points > 0:
            await self._ledger_service.deduct(
                mobile=mobile,
                amount=clawback_points,
                biz_type=POINTS_REFUND_EVENT,
                biz_id=order.id,
                unique_id=f"points:refund:{order.id}:clawback",
                event_type=POINTS_REFUND_EVENT,
            )
        await self._clear_awarded(order)

    async def _record_awarded(self, order: Order, points_used: int, award: int) -> None:
        """把已发积分回写支付快照，防止重复发分。"""
        latest = await self._order_repo.get_order(order.id)
        if latest is None:
            return
        payment = loads_payment(latest.payment)
        payment["pointsUsed"] = points_used
        payment["pointsAwarded"] = award
        await self._order_repo.update_payment(
            order.id, dumps_payment(payment), now_text()
        )

    async def _clear_awarded(self, order: Order) -> None:
        """退款后清理快照中的抵扣/已发标记。"""
        latest = await self._order_repo.get_order(order.id)
        if latest is None:
            return
        payment = loads_payment(latest.payment)
        payment["pointsUsed"] = 0
        payment["pointsFen"] = 0
        payment["pointsAwarded"] = 0
        await self._order_repo.update_payment(
            order.id, dumps_payment(payment), now_text()
        )

    async def _try_resolve_mobile(self, user_id: str) -> str | None:
        """解析会员手机号；非会员用户返回 None，跳过积分发放/收回。"""
        try:
            return await self._resolve_mobile(user_id)
        except ValueError:
            logger.debug("订单用户 %s 未识别为会员，跳过积分联动", user_id)
            return None

    async def _resolve_mobile(self, user_id: str) -> str:
        from app.service.stored_value.member import MemberBalanceService

        return await MemberBalanceService(
            customer_repo=CustomerMasterRepo(self._order_repo._db)
        ).resolve_mobile(user_id)

    @staticmethod
    def _total_fen(order: Order) -> int:
        from app.utils import yuan_to_fen

        return yuan_to_fen(order.total_amount)
