"""订单储值支付与组合支付服务。"""

from app.config import settings
from app.models.order import Order, OrderStatus
from app.models.stored_value import BalanceBizType, BalanceSource
from app.repository.order_repo import OrderRepo
from app.service.integrations.wechat_pay import WechatPayIntegrationService
from app.service.order.payment_state import (
    PAYMENT_METHOD_COMBINED,
    PAYMENT_STATUS_PARTIAL,
    PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_UNPAID,
    PaymentSession,
    build_balance_payment,
    build_combined_payment,
    build_mock_payment_session,
    build_order_description,
    compute_remain_fen,
    dumps_payment,
    extract_openid,
    loads_payment,
    now_text,
    status_value,
)
from app.service.stored_value.member import MemberBalanceService
from app.utils import yuan_to_fen


class StoredValueOrderPaymentService:
    """负责用储值余额支付订单（全额或组合差额）。"""

    def __init__(
        self,
        order_repo: OrderRepo | None = None,
        member_service: MemberBalanceService | None = None,
        wechat_pay_service: WechatPayIntegrationService | None = None,
    ) -> None:
        self._order_repo = order_repo or OrderRepo(None)
        self._member_service = member_service or MemberBalanceService()
        self._wechat_pay_service = wechat_pay_service or WechatPayIntegrationService()

    async def pay_order_with_balance(self, order_id: str, *, user_id: str) -> dict:
        """订单全额使用储值余额支付（防超扣，幂等）。

        D1-A 复核 P2：首次储值操作即固定不可变账户 ID（memberBalanceId 绑定
        快照），余额腿预占（P3）与结算扣减全部经统一支付应用服务按账户 ID
        完成，禁止按手机号操作 / 按手机号新建替代账户。
        """
        order = await self._owned_order(order_id, user_id)
        if status_value(order) == OrderStatus.CANCELLED.value:
            raise ValueError("订单已取消")
        payment = loads_payment(order.payment)
        payment_status = str(payment.get("status", PAYMENT_STATUS_UNPAID))
        if payment_status == PAYMENT_STATUS_PAID:
            async with self._order_repo.transaction():
                from app.service.coupon import CouponService
                from app.service.points.payment import PointsPaymentService

                await CouponService(order_repo=self._order_repo).consume_on_payment(
                    order
                )
                await PointsPaymentService(
                    order_repo=self._order_repo
                ).award_on_payment(order)
            return self._serialize_order_payment(order, payment)
        if (
            payment_status == PAYMENT_STATUS_PARTIAL
            and int(payment.get("balanceFen", 0) or 0) > 0
        ):
            raise ValueError("订单已部分支付，请完成剩余支付")
        total_fen = self._total_fen(order)
        coupon_fen = int(payment.get("couponFen", 0) or 0)
        points_fen = int(payment.get("pointsFen", 0) or 0)
        pay_fen = compute_remain_fen(total_fen, coupon_fen, 0, points_fen)

        from app.service.payment.unified import UnifiedPaymentApplicationService

        unified = UnifiedPaymentApplicationService(order_repo=self._order_repo)
        # P2：首次储值操作固定不可变账户 ID，并写入快照供 attempt 冻结
        member_balance_id = await self._member_service.resolve_member_balance_id(
            user_id
        )
        if pay_fen > 0:
            payment["memberBalanceId"] = str(member_balance_id)
            await self._order_repo.update_payment(
                order.id, dumps_payment(payment), now_text()
            )
        # 重读最新订单：attempt 冻结的快照必须含账户绑定（与库中一致）
        fresh_order = await self._order_repo.get_order(order.id)
        if fresh_order is None:
            raise ValueError("订单不存在")
        order = fresh_order

        async def _perform_settle() -> None:
            """真实资产动作：置 paid → 核销券 → 发分（余额扣减由统一服务完成）。"""
            now = now_text()
            paid_payment = build_balance_payment(now, pay_fen)
            # 快照合并顺序不敏感：保留券/积分字段与账户绑定，支付核销与发分依赖它们
            paid_payment["couponId"] = str(payment.get("couponId", "") or "")
            paid_payment["couponFen"] = int(payment.get("couponFen", 0) or 0)
            paid_payment["pointsFen"] = int(payment.get("pointsFen", 0) or 0)
            paid_payment["pointsUsed"] = int(payment.get("pointsUsed", 0) or 0)
            if pay_fen > 0:
                paid_payment["memberBalanceId"] = str(member_balance_id)
            updated = await self._order_repo.update_payment_to_paid_if_unpaid_or_partial_active(
                order.id,
                dumps_payment(paid_payment),
                now,
            )
            if updated is None:
                raise ValueError("订单支付状态更新冲突")
            from app.service.coupon import CouponService
            from app.service.points.payment import PointsPaymentService

            await CouponService(order_repo=self._order_repo).consume_on_payment(updated)
            await PointsPaymentService(order_repo=self._order_repo).award_on_payment(
                updated
            )

        leg_amounts = {"balance": pay_fen} if pay_fen > 0 else None
        await unified.settle_mock_order(
            order, settle_actions=_perform_settle, leg_amounts=leg_amounts
        )
        latest = await self._order_repo.get_order(order.id)
        if latest is None:
            raise ValueError("订单不存在")
        return self._serialize_order_payment(latest, loads_payment(latest.payment))

    async def prepare_combined_payment(
        self,
        order_id: str,
        *,
        user_id: str,
        balance_fen: int,
    ) -> dict:
        """组合支付：预占储值余额部分（真实预占 P3），再返回差额支付会话。

        D1-A 复核 P2/P3：不再提前扣减余额——首次储值操作固定不可变账户 ID，
        经统一支付应用服务创建支付尝试 + 余额腿预占（账户行 held 原子占用 +
        审计 hold 行），快照绑定 memberBalanceId；剩余差额由差额支付会话
        完成，结算时统一服务按账户 ID 扣减余额腿。
        """
        order = await self._owned_order(order_id, user_id)
        if status_value(order) == OrderStatus.CANCELLED.value:
            raise ValueError("订单已取消")
        payment = loads_payment(order.payment)
        payment_status = str(payment.get("status", PAYMENT_STATUS_UNPAID))
        if payment_status == PAYMENT_STATUS_PAID:
            raise ValueError("订单已支付")
        if (
            payment_status == PAYMENT_STATUS_PARTIAL
            and int(payment.get("balanceFen", 0) or 0) > 0
        ):
            raise ValueError("订单已部分支付，请完成剩余支付")
        total_fen = self._total_fen(order)
        coupon_fen = int(payment.get("couponFen", 0) or 0)
        points_fen = int(payment.get("pointsFen", 0) or 0)
        remain_before_balance = compute_remain_fen(total_fen, coupon_fen, 0, points_fen)
        if balance_fen <= 0 or balance_fen >= remain_before_balance:
            raise ValueError(
                "组合支付余额部分必须大于 0 且小于订单总额（券/积分后以剩余应付为准）"
            )
        remain_fen = compute_remain_fen(total_fen, coupon_fen, balance_fen, points_fen)
        # P2：首次储值操作固定不可变账户 ID
        member_balance_id = await self._member_service.resolve_member_balance_id(
            user_id
        )
        now = now_text()
        partial_payment = build_combined_payment(now, balance_fen, remain_fen)
        partial_payment["couponId"] = str(payment.get("couponId", "") or "")
        partial_payment["couponFen"] = int(payment.get("couponFen", 0) or 0)
        partial_payment["pointsFen"] = int(payment.get("pointsFen", 0) or 0)
        partial_payment["pointsUsed"] = int(payment.get("pointsUsed", 0) or 0)
        partial_payment["memberBalanceId"] = str(member_balance_id)
        from app.service.payment.unified import UnifiedPaymentApplicationService

        unified = UnifiedPaymentApplicationService(order_repo=self._order_repo)
        async with self._order_repo.transaction():
            updated = await self._order_repo.update_payment_to_partial_if_unpaid_or_partial_active(
                order.id,
                dumps_payment(partial_payment),
                now,
            )
            if updated is None:
                raise ValueError("订单支付状态更新冲突")
            # 预占：attempt + 余额腿 + 账户行 held 原子占用（同一 UoW 提交）
            await unified.ensure_mock_attempt(
                updated, leg_amounts={"balance": balance_fen}
            )
        remainder = await self._build_remainder_session(order, remain_fen)
        return {
            "orderId": order.id,
            "payment": {
                "status": PAYMENT_STATUS_PARTIAL,
                "method": PAYMENT_METHOD_COMBINED,
                "balanceFen": balance_fen,
                "remainFen": remain_fen,
            },
            "remainderPayment": remainder,
        }

    async def refund_order_balance(self, order: Order) -> None:
        """组合支付取消/超时：按快照退回已实际扣减的储值余额部分。

        D1-A 复核 P2：一律按快照绑定不可变账户 ID 退回（by-id）；新组合单
        余额为预占（未扣减），释放由 release_order_holds 完成，这里无需退回；
        历史无绑定账户的快照禁止按手机号回退 → 记欠账待人工结清。
        """
        payment = loads_payment(order.payment)
        balance_fen = int(payment.get("balanceFen", 0) or 0)
        if balance_fen <= 0:
            return
        # 仅退回实际已扣减的余额（存在 order_pay / combined_pay 流水事实）
        from app.repository.balance_ledger_repo import BalanceLedgerRepo

        balance_ledger = BalanceLedgerRepo(self._order_repo._db)
        deducted_fact = await balance_ledger.get_by_unique_id(
            f"order_pay:{order.id}"
        ) or await balance_ledger.get_by_unique_id(f"combined_pay:{order.id}")
        if deducted_fact is None:
            # 预占未扣减：释放由 release_order_holds 完成，无需退回
            return
        mobile = await self._try_resolve_mobile(order.user_id)
        snapshot_mid = payment.get("memberBalanceId")
        member_balance_id = int(snapshot_mid) if snapshot_mid else None
        if member_balance_id is None:
            # 历史无绑定账户：禁止按手机号新建替代账户，记欠账待人工结清
            await self._append_refund_debt(order, balance_fen, mobile, reason="unbound")
            return
        credited = await self._member_service.credit_by_id(
            user_id=order.user_id,
            member_balance_id=member_balance_id,
            mobile=mobile,
            amount_fen=balance_fen,
            biz_type=BalanceBizType.ORDER_REFUND,
            biz_id=order.id,
            unique_id=f"order_refund:{order.id}",
            source=BalanceSource.ORDER,
        )
        if credited is None:
            # 账户已删除（重建新 id 不命中）：记欠账待人工结清
            await self._append_refund_debt(
                order, balance_fen, mobile, reason="account_missing"
            )

    async def _append_refund_debt(
        self, order: Order, balance_fen: int, mobile: str, *, reason: str
    ) -> None:
        """储值退款无法自动退回（账户缺失/未绑定）：记欠账待人工结清。"""
        from app.repository.refund_shortfall_debt_repo import (
            RefundShortfallDebtRepo,
        )

        reason_note = {
            "unbound": "历史快照未绑定储值账户（memberBalanceId 缺失），禁止按手机号回退",
            "account_missing": "原储值账户已删除（member_balance_id 不命中），禁止按手机号新建替代账户",
        }[reason]
        await RefundShortfallDebtRepo(self._order_repo._db).append(
            order_id=order.id,
            mobile=mobile or "",
            member_balance_id=None,
            operation_key=f"order_refund:{order.id}",
            amount=balance_fen,
            note=f"储值退款 {balance_fen} 分待人工结清（{reason_note}）",
        )

    async def _try_resolve_mobile(self, user_id: str) -> str:
        try:
            return await self._member_service.resolve_mobile(user_id)
        except ValueError:
            return ""

    async def _owned_order(self, order_id: str, user_id: str) -> Order:
        order = await self._order_repo.get_order(order_id)
        if order is None or order.user_id != user_id:
            raise ValueError("订单不存在")
        return order

    async def _build_remainder_session(
        self,
        order: Order,
        remain_fen: int,
    ) -> dict:
        if self._wechat_pay_service.is_ready():
            payer_openid = extract_openid(order.user_id)
            if not payer_openid:
                raise ValueError("当前用户未绑定微信 openid")
            prepay = await self._wechat_pay_service.create_jsapi_prepay(
                order_id=order.id,
                total_fen=remain_fen,
                description=build_order_description(order),
                payer_openid=payer_openid,
            )
            return {
                "mode": "wechat",
                "orderId": order.id,
                "paymentMethod": "wechat",
                "paymentStatus": PAYMENT_STATUS_UNPAID,
                "paymentParams": self._wechat_pay_service.build_payment_params(
                    prepay.prepay_id,
                    signer=self._wechat_pay_service.sign_with_rsa,
                ),
            }
        if not settings.ALLOW_MOCK_PAYMENT:
            raise ValueError("微信支付未配置，生产环境不提供 mock 支付")
        session = build_mock_payment_session(order.id)
        return self._serialize_session(session)

    @staticmethod
    def _serialize_session(session: PaymentSession) -> dict:
        return {
            "mode": session.mode,
            "orderId": session.order_id,
            "paymentMethod": session.payment_method,
            "paymentStatus": session.payment_status,
            "paymentParams": session.payload,
        }

    @staticmethod
    def _total_fen(order: Order) -> int:
        return yuan_to_fen(order.total_amount)

    @staticmethod
    def _serialize_order_payment(order: Order, payment: dict) -> dict:
        return {
            "orderId": order.id,
            "status": status_value(order),
            "paymentStatus": payment.get("status", ""),
            "paymentMethod": payment.get("method", ""),
            "balanceFen": payment.get("balanceFen", 0),
            "paidAt": payment.get("paidAt", ""),
        }
