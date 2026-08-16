"""积分支付联动：抵扣快照、支付发分、退款收回。"""

from app.logger import setup_logger
from app.models.member import LedgerSource, PointsLedgerEntry
from app.models.order import Order
from app.repository.customer_master_repo import CustomerMasterRepo
from app.repository.ledger_operation_repo import (
    REFUND_CLAWBACK,
    REFUND_DEBT_REPAY,
    REFUND_RETURN,
    SETTLE_AWARD,
    SETTLE_REDEEM,
    LedgerOperationRepo,
)
from app.repository.member_balance_repo import MemberBalanceRepo
from app.repository.order_repo import OrderRepo
from app.repository.points_ledger_repo import PointsLedgerRepo
from app.repository.points_refund_reconcile_repo import PointsRefundReconcileRepo
from app.repository.refund_operation_repo import (
    REFUND_OP_PARTIAL,
    REFUND_OP_SHORTFALL,
    REFUND_OP_SUCCEEDED,
    RefundOperationRepo,
)
from app.repository.refund_shortfall_debt_repo import RefundShortfallDebtRepo
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
from app.service.payment.errors import PaymentAccountError
from app.service.points.ledger import PointsLedgerService
from app.service.points.rules import (
    award_points,
    points_to_fen,
    refund_reversal,
)
from app.utils import now_str

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
        self._balance_repo = MemberBalanceRepo(self._order_repo._db)
        self._reconcile_repo = PointsRefundReconcileRepo(self._order_repo._db)
        self._ledger_operation_repo = LedgerOperationRepo(self._order_repo._db)
        self._refund_operation_repo = RefundOperationRepo(self._order_repo._db)
        self._shortfall_debt_repo = RefundShortfallDebtRepo(self._order_repo._db)

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
        # B3.5（评审问题 2）：快照绑定不可变余额账户 ID——账户缺失禁止应用抵扣；
        # 结算 / 退款一律按绑定账户校验，防止账户漂移与免费抵扣。
        balance_row = await self._balance_repo.get_by_mobile(mobile)
        if balance_row is None:
            raise ValueError("积分账户不存在，订单不能应用积分抵扣")
        snapshot["memberBalanceId"] = str(balance_row["id"])
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
        # B3.5（评审问题 1）：快照写入不自提交，由调用方门面事务（PointsService.
        # apply_points 外层 transaction）统一提交，仓储与支付服务均不持有提交边界。
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
        """支付成功后发分并扣抵扣（幂等）。

        B3.5（评审问题 2）：结算前校验快照绑定账户——有抵扣但账户无法解析 /
        账户缺失 / 账户漂移（应用后换绑）时**禁止结算**（订单保持 settling，
        进入人工核对），不允许免费抵扣；扣减 / 发放 / 结算事实与
        pointsSettledAt 标记同一 UoW 原子提交（由外层应用事务负责）。
        """
        payment = loads_payment(order.payment)
        if str(payment.get("status", PAYMENT_STATUS_UNPAID)) != PAYMENT_STATUS_PAID:
            return
        if int(payment.get("pointsAwarded", 0) or 0) > 0:
            return
        points_used = int(payment.get("pointsUsed", 0) or 0)
        total_fen = self._total_fen(order)
        balance_fen = int(payment.get("balanceFen", 0) or 0)
        coupon_fen = int(payment.get("couponFen", 0) or 0)
        points_fen = int(payment.get("pointsFen", 0) or 0)
        cash_fen = max(0, total_fen - coupon_fen - balance_fen - points_fen)
        award = award_points(cash_fen)
        if points_used <= 0 and award <= 0:
            # 无抵扣无发分：不涉及积分账户身份，直接跳过（券全额抵扣 / 余额全额
            # 支付的订单快照可无 memberBalanceId，禁止因此误判历史未绑定）
            return
        mobile = await self._try_resolve_mobile(order.user_id)
        if mobile is None:
            if points_used > 0:
                raise PaymentAccountError(
                    "account_unresolved",
                    f"积分账户无法解析，订单 {order.id} 不得视为已支付",
                )
            # 无抵扣仅发分且会员无法解析：跳过发分（无账户可入账，B3.4 语义）
            return
        balance_row = await self._balance_repo.get_by_mobile(mobile)
        if balance_row is None:
            raise PaymentAccountError(
                "account_missing",
                f"积分账户不存在，订单 {order.id} 不得视为已支付",
            )
        member_balance_id = int(balance_row["id"])
        snapshot_mid = payment.get("memberBalanceId")
        if snapshot_mid and int(snapshot_mid) != member_balance_id:
            raise PaymentAccountError(
                "account_changed",
                f"积分账户已变更，订单 {order.id} 不得结算",
            )
        if not snapshot_mid:
            # R3：历史快照（B3.5 前）未绑定账户 ID——禁止按手机号补绑当前解析账户
            # （旧账户删除后同手机号重建会把扣减写到新账户，违反 A5 不可变账户
            # 身份）；转 manual_review / 可追溯案件，仅允许能证明原账户 ID 的
            # 单独迁移回填
            raise PaymentAccountError(
                "legacy_unbound",
                f"历史快照未绑定积分账户（订单 {order.id}），禁止按手机号补绑结算，需人工复核",
            )
        if points_used > 0:
            # D1-A（验收 A5）：扣减一律按快照绑定不可变账户 ID——账户行被删除后
            # 重建（新 id）时旧 id 查无 → 阻断结算进 manual_review，禁止按手机号
            # 新建账户替代原账户；余额不足同样阻断（禁止静默放行免费抵扣）
            balance_after = await self._ledger_service.deduct_by_id(
                member_balance_id=member_balance_id,
                amount=points_used,
                biz_type=POINTS_REDEEM_EVENT,
                biz_id=order.id,
                unique_id=f"points:redeem:{order.id}",
                event_type=POINTS_REDEEM_EVENT,
            )
            if balance_after is None:
                account_row = await self._balance_repo.get_by_id(member_balance_id)
                if account_row is None:
                    raise PaymentAccountError(
                        "account_missing",
                        f"积分账户不存在（已删除？），订单 {order.id} 不得视为已支付",
                    )
                raise PaymentAccountError(
                    "points_insufficient",
                    f"积分余额不足，抵扣扣减失败（订单 {order.id}），订单不得视为已支付",
                )
            # B3.5（评审问题 2）：结算事实与流水、pointsSettledAt 同一 UoW 原子写
            await self._ledger_operation_repo.append(
                operation_type=SETTLE_REDEEM,
                subject_id=order.id,
                mobile=mobile,
                member_balance_id=member_balance_id,
                amount=-points_used,
                unique_id=f"ledger:settle_redeem:{order.id}",
                biz_type=POINTS_REDEEM_EVENT,
                biz_id=order.id,
            )
        if award > 0:
            # D1-A（验收 A6）：入账优先偿债——先偿还该账户未结清欠账，
            # 剩余部分才作为可用积分入账。
            # D1-A 复核 P6：points_ledger award 流水记**实际入账** credit_amount
            # （余额总额可对账），偿还部分为独立事实 ledger:debt_repay:*；
            # 全额 award 事实仍记入 ledger_operation settle_award（退款核验
            # clawback 与 award 对账使用该事实，短口由债务机制兜底）。
            repaid = await self._repay_open_debts(member_balance_id, award)
            credit_amount = award - repaid
            if credit_amount > 0:
                balance_after = await self._balance_repo.credit_points_by_id(
                    member_balance_id, credit_amount
                )
                if balance_after is None:
                    # D1-A（验收 A5）：账户已删除 → 禁止按手机号新建替代账户
                    raise PaymentAccountError(
                        "account_missing",
                        f"积分账户不存在（已删除？），订单 {order.id} 不得视为已支付",
                    )
            else:
                balance_row = await self._balance_repo.get_by_id(member_balance_id)
                if balance_row is None:
                    raise ValueError(
                        f"积分账户不存在（已删除？），订单 {order.id} 不得视为已支付"
                    )
                balance_after = int(balance_row["points"])
            if not await self._ledger_service.ledger_repo.get_by_unique_id(
                f"points:award:{order.id}"
            ):
                await self._ledger_service.ledger_repo.insert(
                    PointsLedgerEntry(
                        unique_id=f"points:award:{order.id}",
                        mobile=mobile,
                        amount=credit_amount,
                        total=int(balance_after),
                        event_type=POINTS_AWARD_EVENT,
                        source=LedgerSource.ORDER,
                        biz_type=POINTS_AWARD_EVENT,
                        biz_id=order.id,
                        occurred_at=now_str(),
                    )
                )
            await self._ledger_operation_repo.append(
                operation_type=SETTLE_AWARD,
                subject_id=order.id,
                mobile=mobile,
                member_balance_id=member_balance_id,
                amount=award,
                unique_id=f"ledger:settle_award:{order.id}",
                biz_type=POINTS_AWARD_EVENT,
                biz_id=order.id,
            )
        await self._record_awarded(order, points_used, award)

    async def _refund_return_credit(
        self,
        order: Order,
        *,
        mobile: str,
        member_balance_id: int | None,
        redeem_entry: dict,
        return_points: int,
    ) -> tuple[bool, bool]:
        """退款退回入账：先偿债后入账（按不可变账户 ID），返回 (案件已追加, 未终结)。

        账户缺失（删除/重建）→ 禁止按手机号新建替代账户，转可关闭人工对账案件
        且不自动 credit（D1-A，验收 A5）；退款流水记全额 return_points 供对账。
        """
        case_appended = False
        unfinished = False
        credit_target_id = member_balance_id
        # R3：无账户绑定（历史快照无 ID 且无 settle_redeem 事实）不回退到按
        # 手机号查当前账户——旧账户删除后同手机号重建会把退款写到新账户；
        # 直接走下方「无账户绑定」可关闭人工对账案件，禁止自动 credit
        if credit_target_id is not None:
            repaid = await self._repay_open_debts(credit_target_id, return_points)
            credit_amount = return_points - repaid
            if credit_amount > 0:
                balance_after = await self._balance_repo.credit_points_by_id(
                    credit_target_id, credit_amount
                )
                if balance_after is None:
                    unfinished = True
                    case_open = await self._reconcile_repo.ensure_open_case(
                        order_id=order.id,
                        mobile=mobile or "",
                        unique_id=f"points:refund:{order.id}",
                        reason="account_missing",
                        amount=return_points,
                        note=(
                            "已结算订单原积分账户已删除（member_balance_id="
                            f"{credit_target_id}），禁止按手机号新建替代账户，"
                            "待人工核对后关闭"
                        ),
                    )
                    if case_open:
                        case_appended = True
                    return case_appended, unfinished
            else:
                balance_row = await self._balance_repo.get_by_id(credit_target_id)
                if balance_row is None:
                    unfinished = True
                    case_open = await self._reconcile_repo.ensure_open_case(
                        order_id=order.id,
                        mobile=mobile or "",
                        unique_id=f"points:refund:{order.id}",
                        reason="account_missing",
                        amount=return_points,
                        note=(
                            "已结算订单原积分账户已删除（member_balance_id="
                            f"{credit_target_id}），退款金额已全额偿债，"
                            "待人工核对后关闭"
                        ),
                    )
                    if case_open:
                        case_appended = True
                    return case_appended, unfinished
                balance_after = int(balance_row["points"])
            await self._ledger_service.ledger_repo.insert(
                PointsLedgerEntry(
                    unique_id=f"points:refund:{order.id}",
                    mobile=str(redeem_entry["mobile"]),
                    amount=credit_amount,
                    total=int(balance_after),
                    event_type=POINTS_REFUND_EVENT,
                    source=LedgerSource.ORDER,
                    biz_type=POINTS_REFUND_EVENT,
                    biz_id=order.id,
                    occurred_at=now_str(),
                )
            )
            return case_appended, unfinished
        # 无账户绑定且手机号查无（账户已删除）：禁止新建替代账户
        unfinished = True
        case_open = await self._reconcile_repo.ensure_open_case(
            order_id=order.id,
            mobile=mobile or "",
            unique_id=f"points:refund:{order.id}",
            reason="account_missing",
            amount=return_points,
            note=(
                "已结算订单原积分账户已删除（无快照绑定，手机号查无），"
                "禁止按手机号新建替代账户，待人工核对后关闭"
            ),
        )
        case_appended = True if case_open else case_appended
        return case_appended, unfinished

    async def _repay_open_debts(self, member_balance_id: int, amount: int) -> int:
        """积分入账优先偿债：按 min(入账额, remaining) 依次偿还 open 欠账。

        返回实际偿还总额；剩余部分（amount - repaid）才作为可用积分入账。
        偿还 / 结案均 version CAS，重复入账天然幂等（D1-A，评审问题 3 闭环）。
        D1-A 复核 P6：只偿还**积分扣回**欠账（operation_key 含 :clawback），
        防止储值退款欠账被积分误偿（跨资产对账隔离）。
        """
        if member_balance_id is None or amount <= 0:
            return 0
        debts = await self._shortfall_debt_repo.list_open_by_member_balance_id(
            member_balance_id
        )
        repaid = 0
        remaining = amount
        for debt in debts:
            if remaining <= 0:
                break
            if ":clawback" not in str(debt["operation_key"] or ""):
                continue
            debt_id = int(debt["id"])
            debt_remaining = int(debt["remaining"] or 0)
            debt_version = int(debt["version"] or 1)
            if debt_remaining <= 0:
                continue
            repay_amount = min(debt_remaining, remaining)
            if not await self._shortfall_debt_repo.repay(
                debt_id, debt_version, repay_amount
            ):
                continue
            repaid += repay_amount
            remaining -= repay_amount
            await self._ledger_operation_repo.append(
                operation_type=REFUND_DEBT_REPAY,
                subject_id=str(debt["order_id"]),
                mobile=str(debt["mobile"]),
                member_balance_id=member_balance_id,
                amount=repay_amount,
                unique_id=(
                    f"ledger:debt_repay:{debt['operation_key']}"
                    f":{repay_amount}:{debt_version}"
                ),
                biz_type=POINTS_REFUND_EVENT,
                biz_id=str(debt["order_id"]),
            )
            if debt_remaining == repay_amount:
                await self._shortfall_debt_repo.settle_if_fully_repaid(
                    debt_id, debt_version + 1
                )
        return repaid

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
        """已结算退款：核验原流水后按原账户退回 / 收回；异常进可关闭对账案件。

        B3.5（评审问题 3）：
        - 补偿未终结（存在 open 案件或扣回欠账）前**保留事实快照**，禁止无条件清空；
        - 奖励积分扣回余额不足写入 refund_shortfall_debt 欠账（不静默跳过）；
        - 每次退款写入 refund_operation / ledger_operation 事实（operation_key 幂等），
          供对账工序关联案件 / 欠账结案。
        """
        mobile = await self._try_resolve_mobile(order.user_id)
        ledger_repo = self._ledger_service.ledger_repo
        payment = loads_payment(order.payment)
        snapshot_mid = payment.get("memberBalanceId")
        member_balance_id = int(snapshot_mid) if snapshot_mid else None
        if member_balance_id is None:
            # R3：历史快照缺账户 ID 时**禁止按手机号替代**（旧账户删除后同手机号
            # 重建会把退款写到新账户，违反 A5）；仅回退到不可变结算事实
            # ledger:settle_redeem 的账户绑定（可证明原账户 ID 的记录）
            settle_redeem_op = await self._ledger_operation_repo.get_by_unique_id(
                f"ledger:settle_redeem:{order.id}"
            )
            redeem_fact_mid = (
                settle_redeem_op["member_balance_id"]
                if settle_redeem_op is not None
                else None
            )
            member_balance_id = int(redeem_fact_mid) if redeem_fact_mid else None
        redeem_entry = await ledger_repo.get_by_unique_id(f"points:redeem:{order.id}")
        award_entry = await ledger_repo.get_by_unique_id(f"points:award:{order.id}")
        return_points, clawback_points = refund_reversal(points_used, points_awarded)
        unfinished = False
        case_appended = False
        return_amount = 0
        clawback_amount = 0
        shortfall_amount = 0
        if return_points > 0:
            if redeem_entry is None:
                unfinished = True
                case_open = await self._reconcile_repo.ensure_open_case(
                    order_id=order.id,
                    mobile=mobile or "",
                    unique_id=f"points:refund:{order.id}",
                    reason="redeem_missing",
                    amount=return_points,
                    note="已结算订单未发现 points:redeem 流水，禁止自动 credit，待人工核对后关闭",
                )
                if case_open:
                    case_appended = True
            elif (
                int(redeem_entry["amount"] or 0) != -return_points
                or str(redeem_entry["biz_id"] or "") != order.id
            ):
                unfinished = True
                case_open = await self._reconcile_repo.ensure_open_case(
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
                if case_open:
                    case_appended = True
            else:
                # 退款按原流水账户入账（原扣减发生的账户，member_balance_id），
                # 不使用当前解析手机号；先偿债后入账（D1-A，评审问题 3 闭环）。
                # 整支幂等：points:refund 流水已存在（已退款过）则跳过入账
                refund_key_exists = (
                    await self._ledger_service.ledger_repo.get_by_unique_id(
                        f"points:refund:{order.id}"
                    )
                )
                if refund_key_exists:
                    return_amount = return_points
                else:
                    case_extra, unfinished_extra = await self._refund_return_credit(
                        order,
                        mobile=mobile or str(redeem_entry["mobile"]),
                        member_balance_id=member_balance_id,
                        redeem_entry=redeem_entry,
                        return_points=return_points,
                    )
                    return_amount = return_points
                    case_appended = case_appended or case_extra
                    unfinished = unfinished or unfinished_extra
                await self._ledger_operation_repo.append(
                    operation_type=REFUND_RETURN,
                    subject_id=order.id,
                    mobile=str(redeem_entry["mobile"]),
                    member_balance_id=member_balance_id,
                    amount=return_points,
                    unique_id=f"ledger:refund_return:{order.id}",
                    biz_type=POINTS_REFUND_EVENT,
                    biz_id=order.id,
                )
        if clawback_points > 0:
            # D1-A 复核 P6：全额 award 事实以 ledger_operation settle_award 为准
            # （points_ledger award 流水记实际入账，偿债分流后可能小于全额）；
            # 历史订单（无 settle_award 事实）回退按 award 流水校验。
            settle_award_op = await self._ledger_operation_repo.get_by_unique_id(
                f"ledger:settle_award:{order.id}"
            )
            if settle_award_op is not None:
                award_amount = int(settle_award_op["amount"] or 0)
                award_biz_id = str(settle_award_op["subject_id"] or "")
            elif award_entry is not None:
                award_amount = int(award_entry["amount"] or 0)
                award_biz_id = str(award_entry["biz_id"] or "")
            else:
                award_amount = 0
                award_biz_id = ""
            if award_entry is None and settle_award_op is None:
                unfinished = True
                case_open = await self._reconcile_repo.ensure_open_case(
                    order_id=order.id,
                    mobile=mobile or "",
                    unique_id=f"points:refund:{order.id}:clawback",
                    reason="award_missing",
                    amount=clawback_points,
                    note="已结算订单未发现 points:award 流水，跳过已发积分收回，待人工核对后关闭",
                )
                if case_open:
                    case_appended = True
            elif award_amount != clawback_points or award_biz_id != order.id:
                unfinished = True
                case_open = await self._reconcile_repo.ensure_open_case(
                    order_id=order.id,
                    mobile=mobile or "",
                    unique_id=f"points:refund:{order.id}:clawback",
                    reason="award_mismatch",
                    amount=clawback_points,
                    note=(
                        f"points:award 流水金额/归属不一致（amount="
                        f"{award_amount}，biz={award_biz_id}），跳过收回，"
                        "待人工核对后关闭"
                    ),
                )
                if case_open:
                    case_appended = True
            else:
                # D1-A（验收 A5）：扣回一律按不可变账户 ID——原账户已删除（重建后
                # 新 id）不命中新账户；无快照绑定则解析原发分手机号账户，查无即
                # 欠账待人工结清，禁止按手机号新建替代账户
                award_mobile = str(
                    award_entry["mobile"]
                    if award_entry is not None
                    else (
                        settle_award_op["mobile"] if settle_award_op is not None else ""
                    )
                )
                clawback_target_id = member_balance_id
                # R3：无账户绑定不回退到按手机号查当前账户（防止扣到重建后的
                # 新账户）；保持 None → 欠账待人工结清（见下 balance_after None 分支）
                if clawback_target_id is not None:
                    balance_after = await self._ledger_service.deduct_by_id(
                        member_balance_id=clawback_target_id,
                        amount=clawback_points,
                        biz_type=POINTS_REFUND_EVENT,
                        biz_id=order.id,
                        unique_id=f"points:refund:{order.id}:clawback",
                        event_type=POINTS_REFUND_EVENT,
                    )
                else:
                    balance_after = None
                if balance_after is None:
                    # B3.5（评审问题 3）：扣回余额不足 → 欠账，不静默跳过；
                    # 补偿未终结，事实快照保留供重试
                    unfinished = True
                    shortfall_amount = clawback_points
                    await self._shortfall_debt_repo.append(
                        order_id=order.id,
                        mobile=award_mobile,
                        member_balance_id=member_balance_id,
                        operation_key=f"points:refund:{order.id}:clawback",
                        amount=clawback_points,
                        note=(
                            "奖励积分扣回余额不足，待人工补足后结清"
                            "（补偿未终结，事实快照保留）"
                        ),
                    )
                else:
                    clawback_amount = clawback_points
                    await self._ledger_operation_repo.append(
                        operation_type=REFUND_CLAWBACK,
                        subject_id=order.id,
                        mobile=award_mobile,
                        member_balance_id=member_balance_id,
                        amount=-clawback_points,
                        unique_id=f"ledger:refund_clawback:{order.id}",
                        biz_type=POINTS_REFUND_EVENT,
                        biz_id=order.id,
                    )
        # B3.5（评审问题 3）：补偿未终结（open 案件 / 欠账）时保留事实快照，
        # 供重试与人工核对；已终结才清除快照并标记退款操作事实 succeeded
        if unfinished:
            status = REFUND_OP_SHORTFALL if shortfall_amount > 0 else REFUND_OP_PARTIAL
            note_parts = []
            if shortfall_amount > 0:
                note_parts.append(f"扣回欠账 {shortfall_amount} 分待人工结清")
            if case_appended:
                note_parts.append("存在 open 对账案件")
            await self._refund_operation_repo.append(
                order_id=order.id,
                mobile=mobile or "",
                member_balance_id=member_balance_id,
                operation_key=f"points:refund:{order.id}",
                points_used=points_used,
                points_awarded=points_awarded,
                return_amount=return_amount,
                clawback_amount=clawback_amount,
                shortfall_amount=shortfall_amount,
                status=status,
                note="；".join(note_parts) or "补偿未终结",
            )
            return
        await self._refund_operation_repo.append(
            order_id=order.id,
            mobile=mobile or "",
            member_balance_id=member_balance_id,
            operation_key=f"points:refund:{order.id}",
            points_used=points_used,
            points_awarded=points_awarded,
            return_amount=return_amount,
            clawback_amount=clawback_amount,
            shortfall_amount=0,
            status=REFUND_OP_SUCCEEDED,
            note="补偿终结，事实快照已清除",
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
