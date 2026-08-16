"""D1-A 统一支付应用服务：账务写唯一入口（mock / 余额订单 预占→结算→取消释放→重放）。

- `payment_attempt` 是结算命令的事实源与幂等源：subject-slot 部分唯一索引保证
  单主体单活跃尝试；状态迁移全部条件更新（WHERE status AND state_version），
  双连接并发恰一次结算由 CAS 兜底（验收 A4）。
- 结算 = 同一 UoW 内：attempt CAS（prepay_ready/settling_retry → settling）→
  真实资产动作（回调，扣余额 / 扣积分 / 置 paid / 核销券 / 发分）→ 预占消费 +
  出站事件 + attempt CAS（settling → succeeded）；中途异常 → settling_retry
  保持预占（验收 A1），可重放（验收 A2）。
- 取消 / 超时 = release：未结算尝试 → cancelled / expired + 预占释放（验收 A3）。
- 账户缺失 / 漂移阻断（验收 A5）：积分账户按不可变 member_balance_id 操作，
  by-id 查无 → 阻断并转 manual_review，禁止按手机号新建账户替代原账户。
- 入账优先偿债（验收 A6）：见 PointsPaymentService（积分入账先 repay 欠账）。
- 范围边界：真实微信 prepay / notify、真实券投影、正式导入保持 No-Go。
"""

from collections.abc import Awaitable, Callable
from hashlib import sha256

from app.models.order import Order
from app.repository.account_hold_repo import AccountHoldRepo
from app.repository.accounting_outbox_repo import AccountingOutboxRepo
from app.repository.member_balance_repo import MemberBalanceRepo
from app.repository.order_repo import OrderRepo
from app.repository.payment_attempt_repo import PaymentAttemptRepo
from app.service.order.payment_state import (
    dumps_payment,
    loads_payment,
)

SettleAction = Callable[[], Awaitable[None]]

SETTLE_RETURN_SETTLED = "settled"
SETTLE_RETURN_IDEMPOTENT = "idempotent"


class UnifiedPaymentApplicationService:
    """统一支付应用服务（D1-A，账务写唯一入口）。"""

    def __init__(
        self,
        order_repo: OrderRepo | None = None,
        attempt_repo: PaymentAttemptRepo | None = None,
        hold_repo: AccountHoldRepo | None = None,
        outbox_repo: AccountingOutboxRepo | None = None,
        balance_repo: MemberBalanceRepo | None = None,
    ) -> None:
        self._order_repo = order_repo or OrderRepo(None)
        db = self._order_repo._db
        self._attempt_repo = attempt_repo or PaymentAttemptRepo(db)
        self._hold_repo = hold_repo or AccountHoldRepo(db)
        self._outbox_repo = outbox_repo or AccountingOutboxRepo(db)
        self._balance_repo = balance_repo or MemberBalanceRepo(db)

    async def ensure_mock_attempt(
        self,
        order: Order,
        *,
        leg_amounts: dict[str, int] | None = None,
    ) -> dict:
        """幂等创建/复用活跃支付尝试（prepay_ready）+ 腿与预占。

        腿金额：显式 leg_amounts 优先（余额路径结算前已知支付额），否则从
        支付快照推导（balanceFen / pointsFen / couponFen）。
        """
        payment = loads_payment(order.payment)
        snapshot_mid = payment.get("memberBalanceId")
        member_balance_id = int(snapshot_mid) if snapshot_mid else None
        active = await self._attempt_repo.get_active("order", order.id)
        if active is not None:
            return active
        # 已结算过的终态尝试（succeeded）：直接返回，settle 幂等判定不再新建尝试
        latest = await self._attempt_repo.get_latest("order", order.id)
        if latest is not None and latest["status"] == "succeeded":
            return latest
        snapshot_json = dumps_payment(payment)
        snapshot_hash = sha256(snapshot_json.encode("utf-8")).hexdigest()
        attempt = await self._attempt_repo.create_active(
            subject_type="order",
            subject_id=order.id,
            provider=str(payment.get("method", "mock") or "mock"),
            merchant_order_no=order.id,
            snapshot_json=snapshot_json,
            snapshot_hash=snapshot_hash,
            member_balance_id=member_balance_id,
        )
        if attempt is None:
            # 并发创建冲突（另一连接已建）：重读活跃尝试
            attempt = await self._attempt_repo.get_active("order", order.id)
            if attempt is None:
                raise ValueError("支付尝试创建冲突且重读失败")
        amounts = leg_amounts or self._leg_amounts_from_snapshot(payment)
        for asset_type, amount_fen in amounts.items():
            if amount_fen <= 0:
                continue
            await self._attempt_repo.upsert_leg(attempt["id"], asset_type, amount_fen)
            if asset_type in ("balance", "points") and member_balance_id is not None:
                await self._hold_repo.reserve(
                    hold_key=f"hold:order:{order.id}:{asset_type}",
                    subject_type="order",
                    subject_id=order.id,
                    payment_attempt_id=attempt["id"],
                    asset_type=asset_type,
                    amount_fen=amount_fen,
                    member_balance_id=member_balance_id,
                )
        return attempt

    @staticmethod
    def _leg_amounts_from_snapshot(payment: dict) -> dict[str, int]:
        """从支付快照推导腿金额。"""
        amounts: dict[str, int] = {}
        balance_fen = int(payment.get("balanceFen", 0) or 0)
        points_fen = int(payment.get("pointsFen", 0) or 0)
        coupon_fen = int(payment.get("couponFen", 0) or 0)
        if balance_fen > 0:
            amounts["balance"] = balance_fen
        if points_fen > 0:
            amounts["points"] = points_fen
        if coupon_fen > 0:
            amounts["coupon"] = coupon_fen
        return amounts

    async def settle_mock_order(
        self,
        order: Order,
        *,
        settle_actions: SettleAction | None = None,
        leg_amounts: dict[str, int] | None = None,
    ) -> str:
        """统一 mock / 余额结算。

        返回 'settled'（本连接完成结算）或 'idempotent'（已结算，直接返回）。
        双连接并发：CAS 败者重读——已 succeeded 幂等返回，否则抛冲突。
        """
        attempt = await self.ensure_mock_attempt(order, leg_amounts=leg_amounts)
        if attempt["status"] == "succeeded":
            return SETTLE_RETURN_IDEMPOTENT
        if attempt["status"] not in ("prepay_ready", "settling_retry"):
            raise ValueError(
                f"支付尝试当前不可结算（status={attempt['status']}，订单 {order.id}）"
            )
        moved = await self._attempt_repo.begin_settle(
            attempt["id"], attempt["state_version"]
        )
        if not moved:
            latest = await self._attempt_repo.get_by_id(attempt["id"])
            if latest is not None and latest["status"] == "succeeded":
                return SETTLE_RETURN_IDEMPOTENT
            raise ValueError(
                f"支付尝试状态冲突（订单 {order.id}，另一连接正在结算或已终止）"
            )
        next_version = attempt["state_version"] + 1
        try:
            if settle_actions is not None:
                await settle_actions()
            await self._hold_repo.consume_by_attempt(attempt["id"])
            await self._attempt_repo.mark_legs_consumed(attempt["id"])
            await self._outbox_repo.enqueue(
                operation_key=f"order:settled:{order.id}",
                operation_type="order.settled",
                subject_type="order",
                subject_id=order.id,
                payload_json=dumps_payment(loads_payment(order.payment)),
            )
            if not await self._attempt_repo.complete_settle(
                attempt["id"], next_version
            ):
                raise ValueError(f"支付尝试结算完成冲突（订单 {order.id}）")
            return SETTLE_RETURN_SETTLED
        except Exception as exc:
            # 结算失败保持预占（settling_retry），可重放；
            # 账户缺失/漂移等阻断性错误直接转 manual_review（验收 A5）
            error_text = str(exc)
            if "积分账户" in error_text or "账户已变更" in error_text:
                await self._attempt_repo.mark_manual_review(
                    attempt["id"], next_version, error_text
                )
            else:
                await self._attempt_repo.mark_retry(
                    attempt["id"], next_version, error_text
                )
            raise

    async def replay_settle(
        self,
        order: Order,
        *,
        settle_actions: SettleAction | None = None,
        leg_amounts: dict[str, int] | None = None,
    ) -> str:
        """结算重放（settling_retry → 重试，幂等由 CAS 兜底，验收 A2）。"""
        return await self.settle_mock_order(
            order, settle_actions=settle_actions, leg_amounts=leg_amounts
        )

    async def release_order_holds(
        self,
        order: Order,
        *,
        to_status: str,
        reason: str,
    ) -> bool:
        """取消 / 超时释放：未结算尝试 → cancelled / expired + 预占释放。

        已 succeeded 尝试禁止释放（返回 False）；无活跃尝试为 no-op。
        """
        active = await self._attempt_repo.get_active("order", order.id)
        if active is None:
            return False
        if active["status"] == "succeeded":
            return False
        released = await self._attempt_repo.release(
            active["id"], active["state_version"], to_status, reason
        )
        if not released:
            latest = await self._attempt_repo.get_by_id(active["id"])
            if latest is not None and latest["status"] == "succeeded":
                return False
            raise ValueError(f"支付尝试释放冲突（订单 {order.id}）")
        await self._hold_repo.release_by_attempt(active["id"])
        await self._attempt_repo.mark_legs_released(active["id"])
        await self._outbox_repo.enqueue(
            operation_key=f"order:released:{order.id}",
            operation_type="order.released",
            subject_type="order",
            subject_id=order.id,
            payload_json=dumps_payment(loads_payment(order.payment)),
        )
        return True

    async def mark_manual_review(self, order: Order, *, reason: str) -> bool:
        """人工复核：活跃尝试 → manual_review（未解除前禁止同主体新尝试）。"""
        active = await self._attempt_repo.get_active("order", order.id)
        if active is None:
            return False
        return await self._attempt_repo.mark_manual_review(
            active["id"], active["state_version"], reason
        )


__all__ = [
    "SETTLE_RETURN_IDEMPOTENT",
    "SETTLE_RETURN_SETTLED",
    "UnifiedPaymentApplicationService",
]
