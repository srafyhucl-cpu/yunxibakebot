"""D1-A 统一支付应用服务：账务写唯一入口（mock / 余额订单 预占→结算→取消释放→重放）。

- `payment_attempt` 是结算命令的事实源与幂等源：subject-slot 部分唯一索引保证
  单主体单活跃尝试；状态迁移全部条件更新（WHERE status AND state_version），
  双连接并发恰一次结算由 CAS 兜底（验收 A4）。
- **两阶段结算（D1-A 复核 P1）**：
  - 阶段一（预占）：attempt + 腿 + 预占在**独立 UoW** 持久化（新 UoW commit），
    与结算事务分离——失败后存在可重放 / 可人工复核的持久事实；
  - 阶段二（结算）：在同一 UoW（savepoint/BEGIN）内执行 attempt CAS →
    真实资产动作（回调）→ 预占消费 → 出站事件 → attempt CAS；
    中途异常先回滚资产副作用，再用**新 UoW** 持久化 `settling_retry` /
    `manual_review`，最后重抛。
- **真实预占（D1-A 复核 P3）**：可用额 = 余额 - 活跃预占，预占在账户行
  `held_points` / `held_stored_value_fen` 单条条件更新内原子完成（可用性校验
  与占用同语句），account_hold 表保留审计明细；释放/消费统一 clear（held 单调减）。
- **快照 / 腿一致性（D1-A 复核 P4）**：attempt 创建即冻结支付计划；重放（复用
  既有活跃尝试）时校验快照 hash 与腿金额，不一致 → 案件 + `manual_review`；
  outbox 载荷取 attempt 不可变快照 + 结算结果，不再读调用前的 order.payment。
- **manual_review 状态矩阵（D1-A 复核 P5）**：无资产副作用（订单未置 paid）的
  manual_review 可随取消/超时释放；已产生副作用（订单已 paid）的仅可人工结案。
- 取消 / 超时 = release：未结算尝试 → cancelled / expired + 预占释放（验收 A3）。
- 账户缺失 / 漂移阻断（验收 A5）：积分/储值按不可变 member_balance_id 操作，
  by-id 查无 → 阻断并转 manual_review，禁止按手机号新建账户替代原账户。
- 入账优先偿债（验收 A6）：见 PointsPaymentService（积分入账先 repay 欠账）。
- 范围边界：真实微信 prepay / notify、真实券投影、正式导入保持 No-Go。
"""

import json
from collections.abc import Awaitable, Callable
from hashlib import sha256

from app.models.order import Order
from app.models.stored_value import BalanceBizType, BalanceLedgerEntry, BalanceSource
from app.repository.account_hold_repo import AccountHoldRepo
from app.repository.accounting_outbox_repo import AccountingOutboxRepo
from app.repository.balance_ledger_repo import BalanceLedgerRepo
from app.repository.member_balance_repo import MemberBalanceRepo
from app.repository.order_repo import OrderRepo
from app.repository.payment_attempt_repo import (
    ATTEMPT_SETTLE_FROM,
    PaymentAttemptRepo,
)
from app.service.order.payment_state import (
    PAYMENT_STATUS_PAID,
    dumps_payment,
    loads_payment,
)
from app.utils import now_str

SettleAction = Callable[[], Awaitable[None]]

SETTLE_RETURN_SETTLED = "settled"
SETTLE_RETURN_IDEMPOTENT = "idempotent"

# 账户型错误 → manual_review；其余 → settling_retry（P1 两阶段终态分流）
_ACCOUNT_ERROR_HINTS = ("积分账户", "储值账户", "账户已变更")


class UnifiedPaymentApplicationService:
    """统一支付应用服务（D1-A，账务写唯一入口）。"""

    def __init__(
        self,
        order_repo: OrderRepo | None = None,
        attempt_repo: PaymentAttemptRepo | None = None,
        hold_repo: AccountHoldRepo | None = None,
        outbox_repo: AccountingOutboxRepo | None = None,
        balance_repo: MemberBalanceRepo | None = None,
        balance_ledger_repo: BalanceLedgerRepo | None = None,
    ) -> None:
        self._order_repo = order_repo or OrderRepo(None)
        db = self._order_repo._db
        self._attempt_repo = attempt_repo or PaymentAttemptRepo(db)
        self._hold_repo = hold_repo or AccountHoldRepo(db)
        self._outbox_repo = outbox_repo or AccountingOutboxRepo(db)
        self._balance_repo = balance_repo or MemberBalanceRepo(db)
        self._balance_ledger_repo = balance_ledger_repo or BalanceLedgerRepo(db)

    # ── 阶段一：预占（独立持久化，由调用方决定提交点）─────────────────────

    async def ensure_mock_attempt(
        self,
        order: Order,
        *,
        leg_amounts: dict[str, int] | None = None,
    ) -> dict:
        """幂等创建/复用活跃支付尝试（prepay_ready）+ 腿与真实预占。

        腿金额：显式 leg_amounts 优先（余额路径结算前已知支付额），否则从
        支付快照推导（balanceFen / pointsFen / couponFen）。
        预占 = account_hold 审计行 + 账户行 held_* 原子占用（P3）。
        """
        payment = loads_payment(order.payment)
        snapshot_mid = payment.get("memberBalanceId")
        member_balance_id = int(snapshot_mid) if snapshot_mid else None
        # 预占串行化（D1-A 复核 P4）：先对订单行做无副作用条件写抢占写锁——
        # WAL 下 SQLite 唯一索引只在语句级检查、提交不复查，两个并发
        # INSERT OR IGNORE 可能都成功（双活跃尝试）。先到者持有写锁，
        # 后者阻塞至其提交后重读，保证并发预占恰一个创建尝试。
        await self._order_repo._db.execute(
            "UPDATE orders SET updated_at = updated_at WHERE id = ?", (order.id,)
        )
        active = await self._attempt_repo.get_active("order", order.id)
        if active is not None:
            # 复用既有活跃尝试（重放 / 并发重复）：先校验支付计划一致性（P4）
            await self._validate_attempt_consistency(order, active)
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
            await self._validate_attempt_consistency(order, attempt)
            return attempt
        # 预占：先账户行原子占用（可用性校验），成功后才写审计 hold 行；
        # 任一腿失败 → 余额不足转 failed（前置失败，B3.5 合同），账户缺失
        # 直接抛账户型错误（settle 阶段一分流转 manual_review）；同时回滚
        # 本尝试已占用的账户行预占与审计行（不泄漏 held）。
        amounts = leg_amounts or self._leg_amounts_from_snapshot(payment)
        for asset_type, amount_fen in amounts.items():
            if amount_fen <= 0:
                continue
            if asset_type not in ("balance", "points"):
                continue
            if member_balance_id is None:
                continue
            if not await self._reserve_on_account(
                asset_type, member_balance_id, amount_fen
            ):
                account_row = await self._balance_repo.get_by_id(member_balance_id)
                if account_row is None:
                    label = "储值账户" if asset_type == "balance" else "积分账户"
                    raise ValueError(
                        f"{label}不存在（已删除？），订单 {order.id} 不得发起支付"
                    )
                await self._rollback_partial_reserve(attempt)
                await self._attempt_repo.mark_failed_preclaim(
                    attempt["id"],
                    attempt["state_version"],
                    self._insufficient_message(asset_type, order.id),
                )
                await self._hold_repo.release_by_attempt(attempt["id"])
                await self._attempt_repo.mark_legs_released(attempt["id"])
                raise ValueError(self._insufficient_message(asset_type, order.id))
            await self._hold_repo.reserve(
                hold_key=f"hold:order:{order.id}:{asset_type}",
                subject_type="order",
                subject_id=order.id,
                payment_attempt_id=attempt["id"],
                asset_type=asset_type,
                amount_fen=amount_fen,
                member_balance_id=member_balance_id,
            )
            await self._attempt_repo.upsert_leg(attempt["id"], asset_type, amount_fen)
        return attempt

    async def _rollback_partial_reserve(self, attempt: dict) -> None:
        """回滚本尝试已占用的账户行预占（held 单调减）+ 审计 hold 行。"""
        holds = await self._hold_repo.list_active_by_attempt(attempt["id"])
        for hold in holds:
            if hold["member_balance_id"] is not None:
                await self._clear_hold_on_account(
                    str(hold["asset_type"]),
                    int(hold["member_balance_id"]),
                    int(hold["amount_fen"] or 0),
                )

    async def _reserve_on_account(
        self, asset_type: str, member_balance_id: int, amount_fen: int
    ) -> bool:
        """账户行原子预占（可用额 = 余额 - 活跃预占）。"""
        if asset_type == "balance":
            return await self._balance_repo.reserve_stored_value_fen(
                member_balance_id, amount_fen
            )
        if asset_type == "points":
            return await self._balance_repo.reserve_points(
                member_balance_id, amount_fen
            )
        return True

    async def _clear_hold_on_account(
        self, asset_type: str, member_balance_id: int, amount_fen: int
    ) -> bool:
        """账户行释放/消费预占（held 单调减）。"""
        if asset_type == "balance":
            return await self._balance_repo.clear_stored_value_fen_hold(
                member_balance_id, amount_fen
            )
        if asset_type == "points":
            return await self._balance_repo.clear_points_hold(
                member_balance_id, amount_fen
            )
        return True

    @staticmethod
    def _insufficient_message(asset_type: str, order_id: str) -> str:
        label = "储值余额" if asset_type == "balance" else "积分"
        return f"{label}不足（含预占），订单 {order_id} 无法发起支付"

    # ── 快照 / 腿一致性（P4）─────────────────────────────────────────────

    async def _validate_attempt_consistency(self, order: Order, attempt: dict) -> None:
        """重放一致性校验：当前支付计划 vs 冻结快照 hash 与腿金额。

        不一致 → 案件（open_case）+ manual_review（独立 UoW 持久化）+ 抛错。
        """
        payment = loads_payment(order.payment)
        current_hash = sha256(dumps_payment(payment).encode("utf-8")).hexdigest()
        if current_hash != attempt["snapshot_hash"]:
            await self._open_case_and_review(
                order.id,
                attempt,
                reason="plan_changed",
                note=(
                    "支付计划已变更（快照 hash 不一致），禁止按旧计划结算，"
                    "待人工核对后结案"
                ),
                message="支付计划已变更，订单需人工复核",
            )
        current_legs = self._leg_amounts_from_snapshot(payment)
        legs = await self._attempt_repo.list_legs(attempt["id"])
        leg_by_asset = {leg["asset_type"]: int(leg["amount_fen"] or 0) for leg in legs}
        # 腿金额对比（balance/points/coupon；快照中不存在的腿不参与占用校验）
        for asset_type, amount_fen in current_legs.items():
            if amount_fen <= 0 or asset_type not in leg_by_asset:
                continue
            if leg_by_asset[asset_type] != amount_fen:
                await self._open_case_and_review(
                    order.id,
                    attempt,
                    reason="plan_changed",
                    note=(
                        f"支付计划腿金额不一致（{asset_type}: 快照 "
                        f"{leg_by_asset[asset_type]} vs 当前 {amount_fen}），"
                        "禁止按旧计划结算，待人工核对后结案"
                    ),
                    message="支付计划腿金额已变更，订单需人工复核",
                )

    async def _open_case_and_review(
        self,
        order_id: str,
        attempt: dict,
        *,
        reason: str,
        note: str,
        message: str,
    ) -> None:
        """案件 + manual_review（独立 UoW 持久化，P6 open_case 接入点）。"""
        from app.repository.points_refund_reconcile_repo import (
            PointsRefundReconcileRepo,
        )

        await PointsRefundReconcileRepo(self._order_repo._db).append(
            order_id=order_id,
            mobile="",
            unique_id=f"points:settle:{order_id}",
            reason=reason,
            amount=0,
            note=note,
        )
        await self._commit_attempt_state(
            self._attempt_repo.mark_manual_review(
                attempt["id"], attempt["state_version"], message
            )
        )
        raise ValueError(message)

    # ── 阶段二：结算（两阶段，P1）────────────────────────────────────────

    async def settle_mock_order(
        self,
        order: Order,
        *,
        settle_actions: SettleAction | None = None,
        leg_amounts: dict[str, int] | None = None,
    ) -> str:
        """预占→结算全链路（两阶段持久化）。

        阶段一：预占独立 UoW 提交（attempt + 腿 + 预占持久化）；
        阶段二：结算在独立 UoW 内（CAS → 资产动作 → 预占消费 → outbox →
        succeeded）；失败先回滚资产副作用，再用新 UoW 持久化终态后重抛。
        """
        try:
            attempt = await self._ensure_committed(order, leg_amounts)
        except Exception as exc:
            error_text = str(exc)
            latest = await self._attempt_repo.get_latest("order", order.id)
            if any(hint in error_text for hint in _ACCOUNT_ERROR_HINTS):
                # 预占阶段账户型失败：attempt 保持 prepay_ready → manual_review
                if latest is not None and latest["status"] in (
                    "prepay_ready",
                    "settling_retry",
                ):
                    await self._commit_attempt_state(
                        self._attempt_repo.mark_manual_review(
                            latest["id"], latest["state_version"], error_text
                        )
                    )
            else:
                # 预占不足等前置失败：attempt 已标 failed，补齐独立 UoW 提交
                if latest is not None and latest["status"] == "failed":
                    await self._order_repo._db.commit()
            raise
        if attempt["status"] == "succeeded":
            return SETTLE_RETURN_IDEMPOTENT
        if attempt["status"] not in ATTEMPT_SETTLE_FROM:
            raise ValueError(
                f"支付尝试状态 {attempt['status']} 不可结算（仅可释放或人工结案）"
            )
        try:
            async with self._order_repo.transaction():
                moved = await self._attempt_repo.begin_settle(
                    attempt["id"], attempt["state_version"]
                )
                if not moved:
                    latest = await self._attempt_repo.get_active("order", order.id)
                    if latest is not None and latest["status"] == "succeeded":
                        return SETTLE_RETURN_IDEMPOTENT
                    raise ValueError(
                        f"支付尝试状态冲突（订单 {order.id}），请刷新后重试"
                    )
                next_version = attempt["state_version"] + 1
                await self._settle_balance_legs(order, attempt)
                if settle_actions is not None:
                    await settle_actions()
                await self._consume_holds(attempt)
                await self._attempt_repo.mark_legs_consumed(attempt["id"])
                await self._outbox_repo.enqueue(
                    operation_key=f"order:settled:{order.id}",
                    operation_type="order.settled",
                    subject_type="order",
                    subject_id=order.id,
                    payload_json=self._outbox_payload(attempt, "settled"),
                )
                if not await self._attempt_repo.complete_settle(
                    attempt["id"], next_version
                ):
                    raise ValueError(f"支付尝试完成失败（订单 {order.id}），请重放")
                return SETTLE_RETURN_SETTLED
        except Exception as exc:
            error_text = str(exc)
            # 结算 UoW 已回滚：尝试回到 begin_settle 前状态，重读当前版本
            latest_attempt = await self._attempt_repo.get_by_id(attempt["id"])
            if latest_attempt is None:
                raise RuntimeError(
                    f"支付尝试 {attempt['id']} 结算失败后重读不到，订单 {order.id} 需人工排查"
                ) from exc
            current_version = int(latest_attempt["state_version"])
            if any(hint in error_text for hint in _ACCOUNT_ERROR_HINTS):
                await self._commit_attempt_state(
                    self._attempt_repo.mark_manual_review(
                        attempt["id"],
                        current_version,
                        error_text,
                    )
                )
            else:
                await self._commit_attempt_state(
                    self._attempt_repo.mark_retry(
                        attempt["id"],
                        current_version,
                        error_text,
                    )
                )
            raise

    async def replay_settle(
        self,
        order: Order,
        *,
        settle_actions: SettleAction | None = None,
    ) -> str:
        """结算重放：settling_retry 重放成功（A2），succeeded 幂等返回。"""
        return await self.settle_mock_order(order, settle_actions=settle_actions)

    async def _ensure_committed(
        self, order: Order, leg_amounts: dict[str, int] | None
    ) -> dict:
        """阶段一：预占独立 UoW（ensure + 显式 commit）。"""
        attempt = await self.ensure_mock_attempt(order, leg_amounts=leg_amounts)
        await self._order_repo._db.commit()
        return attempt

    async def _commit_attempt_state(self, coro: Awaitable[bool]) -> None:
        """用新 UoW 持久化尝试终态（先执行写，再显式 commit）。"""
        await coro
        await self._order_repo._db.commit()

    async def _settle_balance_legs(self, order: Order, attempt: dict) -> None:
        """结算余额腿：按不可变账户 ID 原子扣减 + 流水记账（P2）。

        余额腿的真实扣减统一在结算 UoW 内完成（预占只占用 held，不提前扣减）；
        账户删除 / 余额不足（预占后被外部变动挤占）→ 阻断转 manual_review，
        禁止按手机号新建账户替代原账户。
        """
        legs = await self._attempt_repo.list_legs(attempt["id"])
        for leg in legs:
            if leg["asset_type"] != "balance":
                continue
            amount_fen = int(leg["amount_fen"] or 0)
            if amount_fen <= 0:
                continue
            member_balance_id = attempt["member_balance_id"]
            if member_balance_id is None:
                continue
            member_balance_id = int(member_balance_id)
            if not await self._balance_repo.deduct_stored_value_if_sufficient_by_id(
                member_balance_id, amount_fen
            ):
                account_row = await self._balance_repo.get_by_id(member_balance_id)
                if account_row is None:
                    raise ValueError(
                        f"储值账户不存在（已删除？），订单 {order.id} 不得结算"
                    )
                raise ValueError(
                    f"储值账户余额不足（含预占），订单 {order.id} 需人工复核"
                )
            balance_after = await self._balance_repo.get_stored_value_fen_by_id(
                member_balance_id
            )
            account_row = await self._balance_repo.get_by_id(member_balance_id)
            await self._balance_ledger_repo.insert(
                BalanceLedgerEntry(
                    unique_id=f"order_pay:{order.id}",
                    user_id=order.user_id,
                    mobile=str(account_row["mobile"] or "") if account_row else "",
                    amount_fen=-amount_fen,
                    balance_after_fen=balance_after,
                    biz_type=BalanceBizType.ORDER_PAY,
                    biz_id=order.id,
                    source=BalanceSource.ORDER,
                    occurred_at=now_str(),
                )
            )

    async def _consume_holds(self, attempt: dict) -> None:
        """结算消费预占：账户行 held 清除 + 审计行 active→consumed。"""
        holds = await self._hold_repo.list_active_by_attempt(attempt["id"])
        for hold in holds:
            if hold["member_balance_id"] is not None:
                await self._clear_hold_on_account(
                    str(hold["asset_type"]),
                    int(hold["member_balance_id"]),
                    int(hold["amount_fen"] or 0),
                )
        await self._hold_repo.consume_by_attempt(attempt["id"])

    def _outbox_payload(self, attempt: dict, result: str) -> str:
        """outbox 载荷：attempt 不可变快照 + 结算结果（不读调用前的 order.payment）。"""
        return json.dumps(
            {
                "attempt_id": attempt["id"],
                "snapshot": loads_payment(attempt["payment_snapshot_json"]),
                "result": result,
            },
            ensure_ascii=False,
        )

    # ── 取消 / 超时释放（A3）─────────────────────────────────────────────

    async def release_order_holds(
        self,
        order: Order,
        *,
        to_status: str,
        reason: str,
    ) -> bool:
        """取消/超时释放未结算尝试的预占。

        已 succeeded 尝试禁止释放；manual_review 按状态矩阵裁决（P5）：
        订单未置 paid（无资产副作用）可释放，订单已 paid（有副作用）仅可人工结案。
        """
        active = await self._attempt_repo.get_active("order", order.id)
        if active is None:
            return False
        if active["status"] == "succeeded":
            return False
        if active["status"] == "manual_review":
            # 状态矩阵（P5）：按订单**最新**支付快照裁决副作用（paid 与否）
            latest = await self._order_repo.get_order(order.id)
            payment = loads_payment(
                latest.payment if latest is not None else order.payment
            )
            if str(payment.get("status")) == PAYMENT_STATUS_PAID:
                raise ValueError(
                    "订单已结算（支付成功），人工复核尝试禁止取消释放，仅可人工结案"
                )
        released = await self._attempt_repo.release(
            active["id"], active["state_version"], to_status, reason
        )
        if not released:
            raise ValueError(
                f"支付尝试释放冲突（订单 {order.id}，状态 {active['status']}），"
                "请刷新后重试"
            )
        holds = await self._hold_repo.list_active_by_attempt(active["id"])
        for hold in holds:
            if hold["member_balance_id"] is not None:
                await self._clear_hold_on_account(
                    str(hold["asset_type"]),
                    int(hold["member_balance_id"]),
                    int(hold["amount_fen"] or 0),
                )
        await self._hold_repo.release_by_attempt(active["id"])
        await self._attempt_repo.mark_legs_released(active["id"])
        await self._outbox_repo.enqueue(
            operation_key=f"order:released:{order.id}",
            operation_type="order.released",
            subject_type="order",
            subject_id=order.id,
            payload_json=self._outbox_payload(active, f"released:{to_status}"),
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

    @staticmethod
    def _leg_amounts_from_snapshot(payment: dict) -> dict[str, int]:
        """从支付快照推导腿金额（balanceFen / pointsFen / couponFen）。"""
        amounts: dict[str, int] = {}
        for key, asset_type in (
            ("balanceFen", "balance"),
            ("pointsFen", "points"),
            ("couponFen", "coupon"),
        ):
            value = int(payment.get(key, 0) or 0)
            if value > 0:
                amounts[asset_type] = value
        return amounts


__all__ = [
    "SETTLE_RETURN_IDEMPOTENT",
    "SETTLE_RETURN_SETTLED",
    "UnifiedPaymentApplicationService",
]
