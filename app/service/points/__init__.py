"""积分域应用服务门面。"""

from app.models.order import Order
from app.repository.customer_master_repo import CustomerMasterRepo
from app.repository.member_balance_repo import MemberBalanceRepo
from app.repository.order_repo import OrderRepo
from app.repository.points_ledger_repo import PointsLedgerRepo
from app.service.order.payment_state import (
    PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_UNPAID,
    loads_payment,
)
from app.service.points.ledger import PointsLedgerService
from app.service.points.rules import points_to_fen, redeem_units


class PointsService:
    """积分域门面：查询/预览/支付联动/退款。"""

    def __init__(
        self,
        balance_repo: MemberBalanceRepo | None = None,
        ledger_repo: PointsLedgerRepo | None = None,
        customer_repo: CustomerMasterRepo | None = None,
        order_repo: OrderRepo | None = None,
        ledger_service: PointsLedgerService | None = None,
    ) -> None:
        self._balance_repo = balance_repo or MemberBalanceRepo(None)
        self._ledger_repo = ledger_repo or PointsLedgerRepo(None)
        self._customer_repo = customer_repo or CustomerMasterRepo(None)
        self._order_repo = order_repo or OrderRepo(None)
        self._ledger_service = ledger_service or PointsLedgerService(
            balance_repo=self._balance_repo,
            ledger_repo=self._ledger_repo,
        )

    async def resolve_mobile(self, user_id: str) -> str:
        """把小程序用户标识解析为会员手机号。"""
        from app.service.stored_value.member import MemberBalanceService

        return await MemberBalanceService(
            customer_repo=self._customer_repo
        ).resolve_mobile(user_id)

    async def get_points(self, user_id: str) -> dict:
        """读取会员积分余额与最近流水。"""
        mobile = await self.resolve_mobile(user_id)
        balance = await self._balance_repo.get_points(mobile)
        ledger = await self._ledger_service.list_by_mobile(mobile)
        return {"pointsBalance": balance, "mobile": mobile, "ledger": ledger}

    async def redeem_preview(self, order_id: str, *, user_id: str) -> dict:
        """积分抵扣试算（不落账）。"""
        order = await self._owned_order(order_id, user_id)
        payment = loads_payment(order.payment)
        payment_status = str(payment.get("status", PAYMENT_STATUS_UNPAID))
        if payment_status == PAYMENT_STATUS_PAID:
            raise ValueError("订单已支付")
        mobile = await self.resolve_mobile(user_id)
        balance = await self._balance_repo.get_points(mobile)
        total_fen = self._total_fen(order)
        balance_fen = int(payment.get("balanceFen", 0) or 0)
        points_used = redeem_units(balance, total_fen, balance_fen)
        points_fen = points_to_fen(points_used)
        return {
            "orderId": order.id,
            "pointsBalance": balance,
            "pointsFen": points_fen,
            "pointsUsed": points_used,
            "remainFen": max(0, total_fen - balance_fen - points_fen),
        }

    async def _owned_order(self, order_id: str, user_id: str) -> Order:
        order = await self._order_repo.get_order(order_id)
        if order is None or order.user_id != user_id:
            raise ValueError("订单不存在")
        return order

    @staticmethod
    def _total_fen(order: Order) -> int:
        from app.utils import yuan_to_fen

        return yuan_to_fen(order.total_amount)
