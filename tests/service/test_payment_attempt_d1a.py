"""D1-A 最小资金核心纵向切片验收测试（A1–A6 六项验收）。

验收矩阵（docs/specs/2026-08-16-accounting-d1a-minimal-slice.md）：
A1 预占后失败（settling_retry 保持预占可重放）
A2 结算重放幂等（重复 settle 只结算一次）
A3 取消/超时释放预占（cancelled/expired + hold released，已结算禁止释放）
A4 双连接单主体竞争（恰一次结算，事实唯一）
A5 账户删除重建（按不可变 member_balance_id，禁止按手机号新建替代账户）
A6 短缺补足结案（入账优先偿债，remaining 单调递减，open→settled）
"""

import aiosqlite
import pytest

from app.repository.account_hold_repo import AccountHoldRepo
from app.repository.config_repo import ConfigRepo
from app.repository.customer_master_repo import CustomerMasterRepo
from app.repository.member_balance_repo import MemberBalanceRepo
from app.repository.order_event_repo import OrderEventRepo
from app.repository.order_repo import OrderRepo
from app.repository.payment_attempt_repo import PaymentAttemptRepo
from app.repository.points_ledger_repo import PointsLedgerRepo
from app.repository.refund_shortfall_debt_repo import RefundShortfallDebtRepo
from app.repository.session_repo import SessionRepo
from app.repository.youzan_inventory_repo import YouzanInventoryRepo
from app.repository.youzan_repo import YouzanProductRepo
from app.service.order import OrderApplicationService
from app.service.order.payment_state import dumps_payment, loads_payment, now_text
from app.service.payment.unified import UnifiedPaymentApplicationService
from app.service.points import PointsService
from app.service.points.payment import PointsPaymentService

MOBILE = "13800000131"
OPENID = "openid_d1a_001"
USER_ID = f"wx_{OPENID}"


@pytest.fixture
def points_service(db: aiosqlite.Connection) -> PointsService:
    return PointsService(
        balance_repo=MemberBalanceRepo(db),
        ledger_repo=PointsLedgerRepo(db),
        customer_repo=CustomerMasterRepo(db),
        order_repo=OrderRepo(db),
    )


async def _seed_member(
    db: aiosqlite.Connection, *, points: int = 0, tag: str = ""
) -> int:
    """播种客户身份与积分账户，返回不可变 member_balance id（tag 区分多账户）。"""
    suffix = tag or "001"
    await db.execute(
        "INSERT INTO customer_master (id, tenant_id, status, primary_phone, "
        "phone_verified, display_name, identity_confidence, has_miniapp_identity) "
        "VALUES (?, 'yunxi', 'active', ?, 1, 'D1-A 测试', 'high', 1)",
        (f"cm_{OPENID}_{suffix}", MOBILE),
    )
    await db.execute(
        "INSERT INTO customer_identity_links (id, tenant_id, customer_id, "
        "identity_type, identity_value, identity_value_normalized, source_system, "
        "link_status, verification_status, confidence_score) "
        "VALUES (?, 'yunxi', ?, 'miniapp_openid', ?, ?, 'miniapp', 'active', "
        "'verified', 100)",
        (f"cil_{OPENID}_{suffix}", f"cm_{OPENID}_{suffix}", OPENID, OPENID),
    )
    await db.execute(
        "INSERT INTO member_balance (mobile, points) VALUES (?, ?)",
        (MOBILE, points),
    )
    await db.commit()
    rows = await db.execute_fetchall(
        "SELECT id FROM member_balance WHERE mobile = ? LIMIT 1", (MOBILE,)
    )
    return int(rows[0]["id"])


async def _create_order(
    order_service: OrderApplicationService, price_fen: int = 10_000
) -> str:
    created = await order_service.create_order(
        {
            "items": [
                {
                    "productId": "p_d1a_001",
                    "title": "D1-A 资金核心蛋糕",
                    "priceFen": price_fen,
                    "quantity": 1,
                }
            ],
            "receiverName": "D1-A 测试",
            "receiverPhone": MOBILE,
            "deliveryType": "delivery",
            "deliveryAddress": "D1-A 测试地址",
            "expectTime": "2026-08-20 19:00",
        },
        user_id=USER_ID,
    )
    return created["orderId"]


async def _seed_points_partial(
    db: aiosqlite.Connection,
    order_id: str,
    *,
    points_used: int,
    points_fen: int,
    member_balance_id: int,
) -> None:
    """直写积分抵扣 partial 快照（绑定不可变账户 ID，绕过 B3.4 围栏）。"""
    order = await OrderRepo(db).get_order(order_id)
    assert order is not None
    payment = loads_payment(order.payment)
    payment.update(
        {
            "status": "partial",
            "method": "combined",
            "pointsUsed": points_used,
            "pointsFen": points_fen,
            "memberBalanceId": str(member_balance_id),
            "remainFen": max(0, 10_000 - points_fen),
        }
    )
    await OrderRepo(db).update_payment(order_id, dumps_payment(payment), now_text())
    await db.commit()


def _order_service(db: aiosqlite.Connection) -> OrderApplicationService:
    return OrderApplicationService(
        order_repo=OrderRepo(db),
        event_repo=OrderEventRepo(db),
        session_repo=SessionRepo(db),
        product_repo=YouzanProductRepo(db),
        inventory_repo=YouzanInventoryRepo(db),
        config_repo=ConfigRepo(db),
    )


# ==================== A1：预占后失败 → settling_retry 保持预占 ====================


@pytest.mark.asyncio
async def test_a1_preclaim_failure_keeps_hold_and_retry(
    db: aiosqlite.Connection,
) -> None:
    """A1：预占（attempt prepay_ready + hold active）后结算中途失败 → 尝试进入
    settling_retry 且预占保持 active，可重放；不产生任何资产副作用。"""
    account_id = await _seed_member(db, points=100_000)
    order_service = _order_service(db)
    order_id = await _create_order(order_service)
    await _seed_points_partial(
        db,
        order_id,
        points_used=5000,
        points_fen=5000,
        member_balance_id=account_id,
    )
    unified = UnifiedPaymentApplicationService(order_repo=OrderRepo(db))
    order = await OrderRepo(db).get_order(order_id)
    attempt = await unified.ensure_mock_attempt(order)
    assert attempt["status"] == "prepay_ready"
    holds = await AccountHoldRepo(db).list_active_by_attempt(attempt["id"])
    assert len(holds) == 1
    assert holds[0]["asset_type"] == "points"
    assert holds[0]["status"] == "active"

    async def _boom() -> None:
        raise ValueError("模拟结算中途失败")

    with pytest.raises(ValueError, match="模拟结算中途失败"):
        await unified.settle_mock_order(order, settle_actions=_boom)
    await db.commit()

    attempt_after = await PaymentAttemptRepo(db).get_by_id(attempt["id"])
    assert attempt_after["status"] == "settling_retry"
    assert "模拟结算中途失败" in attempt_after["last_error"]
    holds_after = await AccountHoldRepo(db).list_active_by_attempt(attempt["id"])
    assert len(holds_after) == 1  # 预占保持占用，未消费未释放
    ledger = await db.execute_fetchall(
        "SELECT COUNT(*) AS c FROM points_ledger WHERE mobile = ?", (MOBILE,)
    )
    assert int(ledger[0]["c"]) == 0
    order_after = await OrderRepo(db).get_order(order_id)
    assert str(loads_payment(order_after.payment).get("status")) == "partial"


# ==================== A2：结算重放幂等 ====================


@pytest.mark.asyncio
async def test_a2_settle_replay_after_retry_succeeds_once(
    db: aiosqlite.Connection,
) -> None:
    """A2：settling_retry 重放成功 → succeeded + 订单 paid + 事实唯一；
    再次重放幂等返回，不重复结算。"""
    account_id = await _seed_member(db, points=100_000)
    order_service = _order_service(db)
    order_id = await _create_order(order_service)
    await _seed_points_partial(
        db,
        order_id,
        points_used=5000,
        points_fen=5000,
        member_balance_id=account_id,
    )
    unified = UnifiedPaymentApplicationService(order_repo=OrderRepo(db))
    order = await OrderRepo(db).get_order(order_id)
    attempt = await unified.ensure_mock_attempt(order)
    assert attempt["status"] == "prepay_ready"

    async def _boom() -> None:
        raise ValueError("第一次结算失败")

    with pytest.raises(ValueError, match="第一次结算失败"):
        await unified.settle_mock_order(order, settle_actions=_boom)
    await db.commit()

    order = await OrderRepo(db).get_order(order_id)

    async def _real_settle() -> None:
        payment = loads_payment(order.payment)
        payment["status"] = "paid"
        payment["paidAt"] = now_text()
        updated = await OrderRepo(
            db
        ).update_payment_to_paid_if_unpaid_or_partial_active(
            order_id, dumps_payment(payment), now_text()
        )
        assert updated is not None
        await PointsPaymentService(order_repo=OrderRepo(db)).award_on_payment(updated)

    result = await unified.replay_settle(order, settle_actions=_real_settle)
    assert result == "settled"
    await db.commit()

    attempt = await PaymentAttemptRepo(db).get_by_id(attempt["id"])
    assert attempt["status"] == "succeeded"
    holds = await AccountHoldRepo(db).list_by_attempt(attempt["id"])
    assert all(h["status"] == "consumed" for h in holds)
    ledger = await db.execute_fetchall(
        "SELECT COUNT(*) AS c FROM points_ledger WHERE mobile = ?", (MOBILE,)
    )
    assert int(ledger[0]["c"]) == 2  # redeem + award 恰一次
    order_after = await OrderRepo(db).get_order(order_id)
    assert str(loads_payment(order_after.payment).get("status")) == "paid"

    # 再重放：幂等返回，事实不重复
    order_again = await OrderRepo(db).get_order(order_id)
    result2 = await unified.replay_settle(order_again)
    assert result2 == "idempotent"
    ledger2 = await db.execute_fetchall(
        "SELECT COUNT(*) AS c FROM points_ledger WHERE mobile = ?", (MOBILE,)
    )
    assert int(ledger2[0]["c"]) == 2


# ==================== A3：取消/超时释放 ====================


@pytest.mark.asyncio
async def test_a3_cancel_releases_holds_and_blocks_resettle(
    db: aiosqlite.Connection,
) -> None:
    """A3：取消释放未结算尝试 → cancelled + hold released + outbox 事件；
    释放后尝试终态不再活跃（subject-slot 让位，新支付尝试由订单状态放行）；
    已 succeeded 尝试禁止释放。"""
    account_id = await _seed_member(db, points=100_000)
    order_service = _order_service(db)
    order_id = await _create_order(order_service)
    await _seed_points_partial(
        db,
        order_id,
        points_used=5000,
        points_fen=5000,
        member_balance_id=account_id,
    )
    unified = UnifiedPaymentApplicationService(order_repo=OrderRepo(db))
    order = await OrderRepo(db).get_order(order_id)
    attempt = await unified.ensure_mock_attempt(order)
    await db.commit()

    released = await unified.release_order_holds(
        order, to_status="cancelled", reason="用户取消"
    )
    assert released is True
    await db.commit()

    attempt_after = await PaymentAttemptRepo(db).get_by_id(attempt["id"])
    assert attempt_after["status"] == "cancelled"
    holds = await AccountHoldRepo(db).list_by_attempt(attempt["id"])
    assert all(h["status"] == "released" for h in holds)
    outbox = await db.execute_fetchall(
        "SELECT status FROM accounting_outbox WHERE operation_key = ?",
        (f"order:released:{order_id}",),
    )
    assert outbox and outbox[0]["status"] == "pending"
    # 释放后尝试为终态，不再占据 subject-slot 活跃位
    assert await PaymentAttemptRepo(db).get_active("order", order_id) is None

    # 已 succeeded 尝试禁止释放：结算成功后 release 返回 False
    order_id_2 = await _create_order(order_service)
    await _seed_points_partial(
        db,
        order_id_2,
        points_used=5000,
        points_fen=5000,
        member_balance_id=account_id,
    )
    order_2 = await OrderRepo(db).get_order(order_id_2)

    async def _real_settle() -> None:
        payment = loads_payment(order_2.payment)
        payment["status"] = "paid"
        payment["paidAt"] = now_text()
        updated = await OrderRepo(
            db
        ).update_payment_to_paid_if_unpaid_or_partial_active(
            order_id_2, dumps_payment(payment), now_text()
        )
        assert updated is not None
        await PointsPaymentService(order_repo=OrderRepo(db)).award_on_payment(updated)

    assert (
        await unified.settle_mock_order(order_2, settle_actions=_real_settle)
        == "settled"
    )
    await db.commit()
    assert (
        await unified.release_order_holds(
            order_2, to_status="cancelled", reason="用户取消"
        )
        is False
    )
    attempt_2 = await PaymentAttemptRepo(db).get_active("order", order_id_2)
    assert attempt_2 is None or attempt_2["status"] == "succeeded"


@pytest.mark.asyncio
async def test_a3_expire_releases_holds_via_expiration_service(
    db: aiosqlite.Connection,
) -> None:
    """A3（接入）：超时关闭链路释放未结算尝试的预占。"""
    account_id = await _seed_member(db, points=100_000)
    order_service = _order_service(db)
    order_id = await _create_order(order_service)
    await _seed_points_partial(
        db,
        order_id,
        points_used=5000,
        points_fen=5000,
        member_balance_id=account_id,
    )
    unified = UnifiedPaymentApplicationService(order_repo=OrderRepo(db))
    order = await OrderRepo(db).get_order(order_id)
    attempt = await unified.ensure_mock_attempt(order)
    await db.commit()
    # 管理端单笔关闭路径（不校验超时时间，仅校验未支付）
    await order_service.expire_unpaid_order(order_id)
    await db.commit()

    attempt_after = await PaymentAttemptRepo(db).get_by_id(attempt["id"])
    assert attempt_after["status"] == "expired"
    holds = await AccountHoldRepo(db).list_by_attempt(attempt["id"])
    assert all(h["status"] == "released" for h in holds)


# ==================== A4：双连接单主体竞争 ====================


@pytest.mark.asyncio
async def test_a4_dual_connection_exactly_once_settle(tmp_path) -> None:
    """A4：两个独立连接 + 同步屏障并发结算同一订单（快照绑定账户，
    含预占消费路径）——恰一条 succeeded 尝试，预占消费一次、事实唯一。"""
    import asyncio
    import sqlite3

    from app.database import close_db, init_db
    from app.repository.base import DatabaseHandle
    from tests.helpers.catalog_seed import seed_catalog_product

    db_path = tmp_path / "d1a_dual.db"
    conn_a = await init_db(str(db_path))
    conn_b = await init_db(str(db_path))
    try:
        handle_a = DatabaseHandle(conn_a)
        handle_b = DatabaseHandle(conn_b)
        await seed_catalog_product(
            conn_a,
            item_id=92031,
            title="D1-A 并发结算蛋糕",
            price_fen=10_000,
            stock=8,
        )
        await conn_a.commit()
        svc_a = _order_service(handle_a)
        created = await svc_a.create_order(
            {
                "items": [
                    {
                        "productId": "92031",
                        "title": "D1-A 并发结算蛋糕",
                        "priceFen": 10_000,
                        "quantity": 1,
                    }
                ],
                "receiverName": "并发测试",
                "receiverPhone": "18800000920",
                "deliveryType": "delivery",
                "deliveryAddress": "并发测试地址",
                "expectTime": "2026-08-20 19:00",
            },
            user_id="wx_openid_d1a_dual",
        )
        order_id = created["orderId"]
        await conn_a.execute(
            "INSERT INTO customer_master (id, tenant_id, status, primary_phone, "
            "phone_verified, display_name, identity_confidence, has_miniapp_identity) "
            "VALUES ('cm_d1a_dual', 'yunxi', 'active', '18800000920', 1, "
            "'并发结算测试', 'high', 1)"
        )
        await conn_a.execute(
            "INSERT INTO customer_identity_links (id, tenant_id, customer_id, "
            "identity_type, identity_value, identity_value_normalized, source_system, "
            "link_status, verification_status, confidence_score) "
            "VALUES ('cil_d1a_dual', 'yunxi', 'cm_d1a_dual', 'miniapp_openid', "
            "'openid_d1a_dual', 'openid_d1a_dual', 'miniapp', 'active', 'verified', 100)"
        )
        await conn_a.execute(
            "INSERT INTO member_balance (mobile, points) VALUES ('18800000920', 100000)"
        )
        await conn_a.commit()
        account_id = int(
            (
                await conn_a.execute_fetchall(
                    "SELECT id FROM member_balance WHERE mobile = '18800000920'"
                )
            )[0]["id"]
        )
        order = await OrderRepo(conn_a).get_order(order_id)
        payment = loads_payment(order.payment)
        payment.update(
            {
                "status": "partial",
                "method": "combined",
                "pointsUsed": 5000,
                "pointsFen": 5000,
                "memberBalanceId": str(account_id),
                "remainFen": 5000,
            }
        )
        await OrderRepo(conn_a).update_payment(
            order_id, dumps_payment(payment), now_text()
        )
        await conn_a.commit()

        svc_b = _order_service(handle_b)
        barrier = asyncio.Barrier(2)

        async def attempt(svc: OrderApplicationService) -> str:
            await barrier.wait()
            try:
                await svc.confirm_mock_payment(order_id, user_id="wx_openid_d1a_dual")
                return "ok"
            except ValueError:
                return "conflict"
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower():
                    raise
                return "locked"

        results = await asyncio.gather(attempt(svc_a), attempt(svc_b))
        assert results.count("ok") >= 1
        assert set(results) <= {"ok", "conflict", "locked"}
        attempts = await conn_a.execute_fetchall(
            "SELECT status FROM payment_attempt WHERE subject_id = ?", (order_id,)
        )
        assert len(attempts) == 1
        assert attempts[0]["status"] == "succeeded"
        attempt_id = int(
            (
                await conn_a.execute_fetchall(
                    "SELECT id FROM payment_attempt WHERE subject_id = ?",
                    (order_id,),
                )
            )[0]["id"]
        )
        holds = await conn_a.execute_fetchall(
            "SELECT status FROM account_hold WHERE payment_attempt_id = ?",
            (attempt_id,),
        )
        assert len(holds) == 1 and holds[0]["status"] == "consumed"
        ledger = await conn_a.execute_fetchall(
            "SELECT COUNT(*) AS c FROM points_ledger WHERE biz_id = ?", (order_id,)
        )
        assert int(ledger[0]["c"]) == 2
        balance = await conn_a.execute_fetchall(
            "SELECT points FROM member_balance WHERE mobile = '18800000920'"
        )
        assert balance and int(balance[0]["points"]) == 95_050
        outbox = await conn_a.execute_fetchall(
            "SELECT COUNT(*) AS c FROM accounting_outbox WHERE operation_key = ?",
            (f"order:settled:{order_id}",),
        )
        assert int(outbox[0]["c"]) == 1
    finally:
        await close_db(conn_a)
        await close_db(conn_b)


# ==================== A5：账户删除重建 ====================


@pytest.mark.asyncio
async def test_a5_settle_blocks_when_account_deleted(
    db: aiosqlite.Connection,
) -> None:
    """A5（结算侧）：快照绑定账户行被删除 → 结算阻断，不新建替代账户。

    公开路径（application 事务）：整体回滚，订单保持 partial、无残留尝试；
    统一服务直接路径：账户型错误 → attempt manual_review（持久化），
    未解除前同主体不可再结算。
    """
    account_id = await _seed_member(db, points=100_000)
    order_service = _order_service(db)
    order_id = await _create_order(order_service)
    await _seed_points_partial(
        db,
        order_id,
        points_used=5000,
        points_fen=5000,
        member_balance_id=account_id,
    )
    await db.execute("DELETE FROM member_balance WHERE id = ?", (account_id,))
    await db.commit()

    # (a) 公开路径：award 扣减发现账户缺失 → ValueError → application 事务整体回滚
    with pytest.raises(ValueError, match="积分账户不存在"):
        await order_service.confirm_mock_payment(order_id, user_id=USER_ID)
    order_after = await OrderRepo(db).get_order(order_id)
    assert str(loads_payment(order_after.payment).get("status")) == "partial"
    attempts = await db.execute_fetchall(
        "SELECT COUNT(*) AS c FROM payment_attempt WHERE subject_id = ?", (order_id,)
    )
    assert int(attempts[0]["c"]) == 0
    accounts = await db.execute_fetchall(
        "SELECT COUNT(*) AS c FROM member_balance WHERE mobile = ?", (MOBILE,)
    )
    assert int(accounts[0]["c"]) == 0  # 未新建替代账户

    # (b) 统一服务直接路径：账户型错误 → manual_review 持久化
    unified = UnifiedPaymentApplicationService(order_repo=OrderRepo(db))
    order = await OrderRepo(db).get_order(order_id)

    async def _account_error() -> None:
        raise ValueError("积分账户不存在（已删除？），订单不得视为已支付")

    with pytest.raises(ValueError, match="积分账户不存在"):
        await unified.settle_mock_order(order, settle_actions=_account_error)
    await db.commit()

    attempt = await PaymentAttemptRepo(db).get_active("order", order_id)
    assert attempt["status"] == "manual_review"
    accounts = await db.execute_fetchall(
        "SELECT COUNT(*) AS c FROM member_balance WHERE mobile = ?", (MOBILE,)
    )
    assert int(accounts[0]["c"]) == 0


@pytest.mark.asyncio
async def test_a5_refund_after_account_rebuilt_never_credits_new_account(
    db: aiosqlite.Connection,
    points_service,
) -> None:
    """A5（退款侧）：账户删除后同手机号重建（新 id）——退款退回与扣回一律
    按旧不可变账户 ID，新账户分文不动，进 account_missing 案件与欠账。"""
    account_id = await _seed_member(db, points=100_000)
    order_service = _order_service(db)
    order_id = await _create_order(order_service)
    await _seed_points_partial(
        db,
        order_id,
        points_used=5000,
        points_fen=5000,
        member_balance_id=account_id,
    )
    await order_service.confirm_mock_payment(order_id, user_id=USER_ID)
    assert (
        int(
            (
                await db.execute_fetchall(
                    "SELECT points FROM member_balance WHERE id = ?", (account_id,)
                )
            )[0]["points"]
        )
        == 95_050
    )
    # 删除原账户，同手机号重建（新 id，余额 100000）
    await db.execute("DELETE FROM member_balance WHERE id = ?", (account_id,))
    await db.execute(
        "INSERT INTO member_balance (mobile, points) VALUES (?, 100000)", (MOBILE,)
    )
    await db.commit()
    new_rows = await db.execute_fetchall(
        "SELECT id FROM member_balance WHERE mobile = ?", (MOBILE,)
    )
    new_account_id = int(new_rows[0]["id"])
    assert new_account_id != account_id

    order = await OrderRepo(db).get_order(order_id)
    await points_service.refund_points(order)
    await db.commit()

    # 新账户分文未动（退回 5000 未写入、扣回 50 未扣走）
    new_points = int(
        (
            await db.execute_fetchall(
                "SELECT points FROM member_balance WHERE id = ?", (new_account_id,)
            )
        )[0]["points"]
    )
    assert new_points == 100_000
    cases = await db.execute_fetchall(
        "SELECT reason FROM points_refund_reconcile WHERE unique_id = ?",
        (f"points:refund:{order_id}",),
    )
    assert cases and cases[0]["reason"] == "account_missing"
    debts = await db.execute_fetchall(
        "SELECT amount, remaining, status FROM refund_shortfall_debt "
        "WHERE order_id = ?",
        (order_id,),
    )
    assert debts and int(debts[0]["amount"]) == 50
    assert debts[0]["status"] == "open"


# ==================== A6：短缺补足结案 ====================


@pytest.mark.asyncio
async def test_a6_next_award_repays_shortfall_debt_and_settles(
    db: aiosqlite.Connection,
) -> None:
    """A6：后续积分入账优先偿债——部分偿还 remaining 单调递减（version CAS），
    补足后 open→settled；偿债有 ledger_operation 事实。"""
    account_id = await _seed_member(db, points=100_000)
    debt_repo = RefundShortfallDebtRepo(db)
    await debt_repo.append(
        order_id="debt_order_001",
        mobile=MOBILE,
        member_balance_id=account_id,
        operation_key="points:refund:debt_order_001:clawback",
        amount=150,
        note="D1-A 测试欠账",
    )
    await db.commit()
    order_service = _order_service(db)
    # 第一笔入账 100：部分偿还 100，remaining 50 保持 open
    order_id_1 = await _create_order(order_service)
    await _seed_points_partial(
        db,
        order_id_1,
        points_used=0,
        points_fen=0,
        member_balance_id=account_id,
    )
    await order_service.confirm_mock_payment(order_id_1, user_id=USER_ID)
    await db.commit()
    debt = await debt_repo.get_by_operation_key("points:refund:debt_order_001:clawback")
    assert int(debt["remaining"]) == 50
    assert debt["status"] == "open"
    # 第二笔入账 100：偿还剩余 50 → open→settled，账户入账 50
    order_id_2 = await _create_order(order_service)
    await _seed_points_partial(
        db,
        order_id_2,
        points_used=0,
        points_fen=0,
        member_balance_id=account_id,
    )
    await order_service.confirm_mock_payment(order_id_2, user_id=USER_ID)
    await db.commit()
    debt = await debt_repo.get_by_operation_key("points:refund:debt_order_001:clawback")
    assert int(debt["remaining"]) == 0
    assert debt["status"] == "settled"
    points = int(
        (
            await db.execute_fetchall(
                "SELECT points FROM member_balance WHERE id = ?", (account_id,)
            )
        )[0]["points"]
    )
    assert points == 100_000 + 200 - 150  # 两笔 award 各 100，偿债 150，入账 50
    repay_facts = await db.execute_fetchall(
        "SELECT operation_type, amount FROM ledger_operation "
        "WHERE operation_type = 'refund_debt_repay' "
        "AND member_balance_id = ? ORDER BY id ASC",
        (account_id,),
    )
    assert [int(f["amount"]) for f in repay_facts] == [100, 50]


@pytest.mark.asyncio
async def test_a6_repeated_repay_is_idempotent(
    db: aiosqlite.Connection,
) -> None:
    """A6：单次入账只偿债一次（version CAS）；补足后 open→settled。"""
    account_id = await _seed_member(db, points=100_000)
    debt_repo = RefundShortfallDebtRepo(db)
    await debt_repo.append(
        order_id="debt_order_002",
        mobile=MOBILE,
        member_balance_id=account_id,
        operation_key="points:refund:debt_order_002:clawback",
        amount=40,
    )
    await db.commit()
    order_service = _order_service(db)
    order_id = await _create_order(order_service)
    await _seed_points_partial(
        db,
        order_id,
        points_used=0,
        points_fen=0,
        member_balance_id=account_id,
    )
    await order_service.confirm_mock_payment(order_id, user_id=USER_ID)
    await db.commit()
    debt = await debt_repo.get_by_operation_key("points:refund:debt_order_002:clawback")
    assert int(debt["remaining"]) == 0
    assert debt["status"] == "settled"
    repay_count = int(
        (
            await db.execute_fetchall(
                "SELECT COUNT(*) AS c FROM ledger_operation "
                "WHERE operation_type = 'refund_debt_repay' "
                "AND member_balance_id = ?",
                (account_id,),
            )
        )[0]["c"]
    )
    assert repay_count == 1


__all__: list[str] = []
