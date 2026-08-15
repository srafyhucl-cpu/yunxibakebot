"""积分支付联动：抵扣快照、支付发分、退款收回。"""

from app.logger import setup_logger
from app.models.order import Order
from app.repository.customer_master_repo import CustomerMasterRepo
from app.repository.member_balance_repo import MemberBalanceRepo
from app.repository.order_repo import OrderRepo
from app.repository.points_ledger_repo import PointsLedgerRepo
from app.repository.points_refund_reconcile_repo import PointsRefundReconcileRepo
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

# B3.4 临时围栏（评审问题 1 的第一项）：D1 前关闭积分抵扣写入口。
# 围栏开启时 apply_points_snapshot 一律拒绝新抵扣；D1 以 account_hold 实现
# 「应用时预占、结算时消费、取消时释放」并放开入口，届时删除本围栏。
POINTS_DEDUCTION_FENCE = True


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
        self._reconcile_repo = PointsRefundReconcileRepo(self._order_repo._db)

    async def apply_points_snapshot(
        self,
        order: Order,
        *,
        user_id: str,
        points_used: int,
        mobile: str,
    ) -> dict:
        """校验并写积分抵扣 partial 快照（不扣积分账）。

        B3.4 临时围栏：D1 前关闭积分抵扣写入口，一律拒绝新抵扣。
        围栏解除后（D1，问题 6 硬化）：只允许首次应用积分抵扣（重复应用拒绝，
        先券后积分等未含积分的 partial 仍可应用）；永远保留首次支付创建时间，
        防止重复应用延后超时关闭。
        """
        if POINTS_DEDUCTION_FENCE:
            raise ValueError(
                "积分抵扣已临时关闭（B3.4 围栏），等待 D1 统一支付应用服务以预占方式重新开放"
            )
        payment = loads_payment(order.payment)
        payment_status = str(payment.get("status", PAYMENT_STATUS_UNPAID))
        if payment_status == PAYMENT_STATUS_PAID:
            raise ValueError("订单已支付")
        if (
            int(payment.get("pointsUsed", 0) or 0) > 0
            or int(payment.get("pointsFen", 0) or 0) > 0
        ):
            # B3.4（评审问题 6）：只允许首次应用积分抵扣，重复应用直接拒绝
            raise ValueError("订单已应用积分抵扣，不能重复应用")
        if int(payment.get("balanceFen", 0) or 0) > 0:
            raise ValueError("订单已部分支付，不能再应用积分")
        total_fen = self._total_fen(order)
        balance_fen = int(payment.get("balanceFen", 0) or 0)
        coupon_fen = int(payment.get("couponFen", 0) or 0)
        points_fen = points_to_fen(points_used)
        if points_fen <= 0:
            raise ValueError("积分抵扣至少 100 分")
        if points_fen > total_fen - balance_fen - coupon_fen:
            raise ValueError("积分抵扣金额超过剩余应付")
        from app.service.order.payment_state import compute_remain_fen

        remain_fen = compute_remain_fen(total_fen, coupon_fen, balance_fen, points_fen)
        now = now_text()
        from app.service.order.payment_state import build_points_payment

        snapshot = build_points_payment(
            now,
            balance_fen=balance_fen,
            points_fen=points_fen,
            points_used=points_used,
            remain_fen=remain_fen,
        )
        # 快照合并顺序不敏感：保留已应用的券字段
        snapshot["couponId"] = str(payment.get("couponId", "") or "")
        snapshot["couponFen"] = int(payment.get("couponFen", 0) or 0)
        # B3.4（评审问题 6）：保留首次支付创建时间，不随应用重写，超时从创建起算
        snapshot["createdAt"] = str(payment.get("createdAt", "") or "") or now
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
        coupon_fen = int(payment.get("couponFen", 0) or 0)
        points_fen = int(payment.get("pointsFen", 0) or 0)
        cash_fen = max(0, total_fen - coupon_fen - balance_fen - points_fen)
        award = award_points(cash_fen)
        if points_used > 0:
            balance_after = await self._ledger_service.deduct(
                mobile=mobile,
                amount=points_used,
                biz_type=POINTS_REDEEM_EVENT,
                biz_id=order.id,
                unique_id=f"points:redeem:{order.id}",
                event_type=POINTS_REDEEM_EVENT,
            )
            if balance_after is None:
                # B3.4（评审问题 1）：扣减失败必须阻止订单进入已支付态，
                # 禁止静默放行形成免费抵扣；外层事务随异常整体回滚。
                raise ValueError(
                    f"积分余额不足，抵扣扣减失败（订单 {order.id}），订单不得视为已支付"
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
        """按支付快照退回抵扣积分并收回已发积分（幂等）。

        B3.4 两命令分流（评审问题 2）：
        - 未结算（从未支付，无 pointsSettledAt 标记）：走 release_unsettled_points_snapshot
          只清快照，正常未结算取消不建对账案件；
        - 已结算（pointsSettledAt 标记或旧快照含 pointsAwarded 键）：走
          refund_settled_points 核验原 redeem / award 流水（账户 / 金额 / 业务归属），
          缺失或不一致进入可关闭、可审计的人工对账案件且不自动 credit；
          退款一律按原流水账户入账，不使用当前手机号。
        """
        payment = loads_payment(order.payment)
        points_used = int(payment.get("pointsUsed", 0) or 0)
        points_awarded = int(payment.get("pointsAwarded", 0) or 0)
        if points_used <= 0 and points_awarded <= 0:
            return
        if self._is_settled(payment):
            await self.refund_settled_points(order, points_used, points_awarded)
        else:
            await self.release_unsettled_points_snapshot(order)

    @staticmethod
    def _is_settled(payment: dict) -> bool:
        """已结算判定：B3.4 起以 pointsSettledAt 标记为准；旧快照以 pointsAwarded 键兜底。"""
        if payment.get("pointsSettledAt"):
            return True
        return "pointsAwarded" in payment

    async def release_unsettled_points_snapshot(self, order: Order) -> None:
        """未结算预占释放：只清快照，不 credit、不建对账案件（B3.4 评审问题 2）。"""
        await self._clear_awarded(order)

    async def refund_settled_points(
        self, order: Order, points_used: int, points_awarded: int
    ) -> None:
        """已结算退款：核验原流水后按原账户退回 / 收回；异常进可关闭对账案件。"""
        mobile = await self._try_resolve_mobile(order.user_id)
        ledger_repo = self._ledger_service.ledger_repo
        redeem_entry = await ledger_repo.get_by_unique_id(f"points:redeem:{order.id}")
        award_entry = await ledger_repo.get_by_unique_id(f"points:award:{order.id}")
        return_points, clawback_points = refund_reversal(points_used, points_awarded)
        if return_points > 0:
            if redeem_entry is None:
                await self._reconcile_repo.append(
                    order_id=order.id,
                    mobile=mobile or "",
                    unique_id=f"points:refund:{order.id}",
                    reason="redeem_missing",
                    amount=return_points,
                    note="已结算订单未发现 points:redeem 流水，禁止自动 credit，待人工核对后关闭",
                )
            elif (
                int(redeem_entry["amount"] or 0) != -return_points
                or str(redeem_entry["biz_id"] or "") != order.id
            ):
                await self._reconcile_repo.append(
                    order_id=order.id,
                    mobile=mobile or "",
                    unique_id=f"points:refund:{order.id}",
                    reason="redeem_mismatch",
                    amount=return_points,
                    note=(
                        f"points:redeem 流水金额/归属不一致（amount="
                        f"{redeem_entry['amount']}），禁止自动 credit，待人工核对后关闭"
                    ),
                )
            else:
                # 退款按原流水账户入账（原扣减发生的账户），不使用当前解析手机号
                await self._ledger_service.credit(
                    mobile=str(redeem_entry["mobile"]),
                    amount=return_points,
                    biz_type=POINTS_REFUND_EVENT,
                    biz_id=order.id,
                    unique_id=f"points:refund:{order.id}",
                    event_type=POINTS_REFUND_EVENT,
                )
        if clawback_points > 0:
            if award_entry is None:
                await self._reconcile_repo.append(
                    order_id=order.id,
                    mobile=mobile or "",
                    unique_id=f"points:refund:{order.id}:clawback",
                    reason="award_missing",
                    amount=clawback_points,
                    note="已结算订单未发现 points:award 流水，跳过已发积分收回，待人工核对后关闭",
                )
            elif (
                int(award_entry["amount"] or 0) != clawback_points
                or str(award_entry["biz_id"] or "") != order.id
            ):
                await self._reconcile_repo.append(
                    order_id=order.id,
                    mobile=mobile or "",
                    unique_id=f"points:refund:{order.id}:clawback",
                    reason="award_mismatch",
                    amount=clawback_points,
                    note=(
                        f"points:award 流水金额/归属不一致（amount="
                        f"{award_entry['amount']}），跳过收回，待人工核对后关闭"
                    ),
                )
            else:
                await self._ledger_service.deduct(
                    mobile=str(award_entry["mobile"]),
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
        # B3.4（评审问题 2）：已结算标记——退款两命令分流的依据，旧快照以
        # pointsAwarded 键存在与否兜底判定
        payment["pointsSettledAt"] = now_text()
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
