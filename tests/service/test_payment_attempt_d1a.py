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
from app.service.payment.errors import PaymentAccountError
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
    # D1-A 复核 P3：真实预占——账户行 held 原子占用（可用额 = 余额 - 预占）
    row = (
        await db.execute_fetchall(
            "SELECT held_points FROM member_balance WHERE id = ?", (account_id,)
        )
    )[0]
    assert int(row["held_points"]) == 5000

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
    row_after = (
        await db.execute_fetchall(
            "SELECT held_points FROM member_balance WHERE id = ?", (account_id,)
        )
    )[0]
    assert int(row_after["held_points"]) == 5000  # 账户行预占保持
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
    # D1-A 复核 P4：outbox 载荷用 attempt 不可变快照 + 结算结果（不读调用前 order.payment）
    import json as _json

    payload_row = (
        await db.execute_fetchall(
            "SELECT payload_json FROM accounting_outbox WHERE operation_key = ?",
            (f"order:settled:{order_id}",),
        )
    )[0]
    payload = _json.loads(payload_row["payload_json"])
    assert payload["attempt_id"] == attempt["id"]
    assert payload["result"] == "settled"
    assert payload["snapshot"]["pointsFen"] == 5000

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

    公开路径（D1-A 复核 P1 两阶段持久化）：预占独立提交、结算失败回滚资产
    副作用后，账户型错误 → attempt manual_review 持久化（不再整体回滚
    抹掉尝试事实）；未解除前同主体不可再结算。
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

    # (a) 公开路径：预占阶段发现账户缺失 → 账户型错误 → manual_review 持久化，
    #     订单保持 partial（paid 未写入），不新建替代账户
    with pytest.raises(ValueError, match="积分账户不存在"):
        await order_service.confirm_mock_payment(order_id, user_id=USER_ID)
    order_after = await OrderRepo(db).get_order(order_id)
    assert str(loads_payment(order_after.payment).get("status")) == "partial"
    attempts = await db.execute_fetchall(
        "SELECT COUNT(*) AS c FROM payment_attempt WHERE subject_id = ?", (order_id,)
    )
    assert int(attempts[0]["c"]) == 1  # 两阶段：尝试事实持久化（manual_review）
    attempt_row = await PaymentAttemptRepo(db).get_active("order", order_id)
    assert attempt_row["status"] == "manual_review"
    accounts = await db.execute_fetchall(
        "SELECT COUNT(*) AS c FROM member_balance WHERE mobile = ?", (MOBILE,)
    )
    assert int(accounts[0]["c"]) == 0  # 未新建替代账户

    # (b) 统一服务直接路径（结算中账户型错误）：预占成功后删除账户再结算 →
    #     结算 UoW 回滚资产副作用后 manual_review 持久化
    # 恢复原账户（(a) 已删除）供本笔预占成功
    await db.execute(
        "INSERT INTO member_balance (id, mobile, points) VALUES (?, ?, 100000)",
        (account_id, MOBILE),
    )
    await db.commit()
    order_id_b = await _create_order(order_service)
    await _seed_points_partial(
        db,
        order_id_b,
        points_used=5000,
        points_fen=5000,
        member_balance_id=account_id,
    )
    unified = UnifiedPaymentApplicationService(order_repo=OrderRepo(db))
    order_b = await OrderRepo(db).get_order(order_id_b)
    await unified.ensure_mock_attempt(order_b)  # 预占成功（账户仍存在）
    await db.commit()
    await db.execute("DELETE FROM member_balance WHERE id = ?", (account_id,))
    await db.commit()

    async def _account_error() -> None:
        # D1-A.1（R5）：账户型错误以结构化 PaymentAccountError 抛出，分流按
        # isinstance 判定 → manual_review（不再依赖中文字符串子串）
        raise PaymentAccountError(
            "account_missing", "积分账户不存在（已删除？），订单不得视为已支付"
        )

    with pytest.raises(ValueError, match="积分账户不存在"):
        await unified.settle_mock_order(order_b, settle_actions=_account_error)
    await db.commit()

    attempt_b = await PaymentAttemptRepo(db).get_active("order", order_id_b)
    assert attempt_b["status"] == "manual_review"
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


# ==================== 复核 P1：公开路径两阶段持久化 ====================


@pytest.mark.asyncio
async def test_public_confirm_failure_persists_retry_then_replays(
    db: aiosqlite.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P1：公开 confirm 结算失败（非账户型）→ settling_retry 持久化（不再被
    外层事务整体回滚抹掉），失败信息可追溯；修复后重放成功。"""
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

    from app.service.points.payment import PointsPaymentService

    real_award = PointsPaymentService.award_on_payment

    async def _failing_award(self, order) -> None:
        raise ValueError("模拟发分服务故障")

    monkeypatch.setattr(PointsPaymentService, "award_on_payment", _failing_award)
    with pytest.raises(ValueError, match="模拟发分服务故障"):
        await order_service.confirm_mock_payment(order_id, user_id=USER_ID)
    # 失败终态持久化：settling_retry + 预占保持 + 订单未置 paid
    attempt = await PaymentAttemptRepo(db).get_active("order", order_id)
    assert attempt["status"] == "settling_retry"
    assert "模拟发分服务故障" in attempt["last_error"]
    row = (
        await db.execute_fetchall(
            "SELECT held_points FROM member_balance WHERE id = ?", (account_id,)
        )
    )[0]
    assert int(row["held_points"]) == 5000
    order_mid = await OrderRepo(db).get_order(order_id)
    assert str(loads_payment(order_mid.payment).get("status")) == "partial"

    # 修复后重放：公开 confirm 幂等结算成功
    monkeypatch.setattr(PointsPaymentService, "award_on_payment", real_award)
    paid = await order_service.confirm_mock_payment(order_id, user_id=USER_ID)
    assert paid["paymentStatus"] == "paid"
    attempt_after = await PaymentAttemptRepo(db).get_by_id(attempt["id"])
    assert attempt_after["status"] == "succeeded"
    ledger = await db.execute_fetchall(
        "SELECT COUNT(*) AS c FROM points_ledger WHERE mobile = ?", (MOBILE,)
    )
    assert int(ledger[0]["c"]) == 2  # 结算事实恰一次


# ==================== 复核 P3：真实预占（可用额 = 余额 - 活跃预占） ====================


@pytest.mark.asyncio
async def test_dual_orders_over_hold_blocked_then_release_frees(
    db: aiosqlite.Connection,
) -> None:
    """P3：账户行 held 参与可用额——第二单预占超可用额被阻断（attempt failed，
    前置失败）；释放第一单后 held 归零，第二单可重新发起（释放后重预占）。"""
    account_id = await _seed_member(db, points=100_000)
    order_service = _order_service(db)
    unified = UnifiedPaymentApplicationService(order_repo=OrderRepo(db))
    order_id_1 = await _create_order(order_service)
    await _seed_points_partial(
        db,
        order_id_1,
        points_used=95000,
        points_fen=95000,
        member_balance_id=account_id,
    )
    order_1 = await OrderRepo(db).get_order(order_id_1)
    attempt_1 = await unified.ensure_mock_attempt(order_1)
    await db.commit()
    assert attempt_1["status"] == "prepay_ready"
    row = (
        await db.execute_fetchall(
            "SELECT held_points FROM member_balance WHERE id = ?", (account_id,)
        )
    )[0]
    assert int(row["held_points"]) == 95000

    order_id_2 = await _create_order(order_service)
    await _seed_points_partial(
        db,
        order_id_2,
        points_used=10000,
        points_fen=10000,
        member_balance_id=account_id,
    )
    order_2 = await OrderRepo(db).get_order(order_id_2)
    with pytest.raises(ValueError, match="积分不足（含预占）"):
        await unified.ensure_mock_attempt(order_2)
    await db.commit()
    attempt_2 = await PaymentAttemptRepo(db).get_latest("order", order_id_2)
    assert attempt_2["status"] == "failed"  # 前置失败（B3.5 合同）
    holds_2 = await AccountHoldRepo(db).list_by_attempt(attempt_2["id"])
    assert all(h["status"] == "released" for h in holds_2)
    # 第二单失败不污染第一单预占
    row = (
        await db.execute_fetchall(
            "SELECT held_points FROM member_balance WHERE id = ?", (account_id,)
        )
    )[0]
    assert int(row["held_points"]) == 95000

    # 释放第一单 → held 归零 → 第二单重新发起成功（释放后重预占）
    await unified.release_order_holds(order_1, to_status="cancelled", reason="用户取消")
    await db.commit()
    row = (
        await db.execute_fetchall(
            "SELECT held_points FROM member_balance WHERE id = ?", (account_id,)
        )
    )[0]
    assert int(row["held_points"]) == 0
    attempt_2b = await unified.ensure_mock_attempt(order_2)
    await db.commit()
    assert attempt_2b["status"] == "prepay_ready"
    row = (
        await db.execute_fetchall(
            "SELECT held_points FROM member_balance WHERE id = ?", (account_id,)
        )
    )[0]
    assert int(row["held_points"]) == 10000


# ==================== 复核 P4：快照 / 腿一致性（案件 + manual_review） ====================


@pytest.mark.asyncio
async def test_plan_change_marks_manual_review_and_opens_case(
    db: aiosqlite.Connection,
) -> None:
    """P4：支付计划在预占后变更（快照 hash 不一致）→ open_case + manual_review，
    禁止按旧计划结算；预占保持占用待人工裁决（P5 矩阵可释放）。"""
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
    # 预占后变更支付计划（pointsFen 5000 → 6000）
    payment = loads_payment(order.payment)
    payment["pointsFen"] = 6000
    payment["remainFen"] = 4000
    await OrderRepo(db).update_payment(order_id, dumps_payment(payment), now_text())
    await db.commit()

    order_changed = await OrderRepo(db).get_order(order_id)
    with pytest.raises(ValueError, match="支付计划已变更"):
        await unified.settle_mock_order(order_changed)
    attempt_after = await PaymentAttemptRepo(db).get_by_id(attempt["id"])
    assert attempt_after["status"] == "manual_review"
    cases = await db.execute_fetchall(
        "SELECT reason FROM points_refund_reconcile WHERE unique_id = ?",
        (f"points:settle:{order_id}",),
    )
    assert cases and cases[0]["reason"] == "plan_changed"
    # 预占保持占用（待人工裁决；P5：无副作用 manual_review 可随取消释放）
    row = (
        await db.execute_fetchall(
            "SELECT held_points FROM member_balance WHERE id = ?", (account_id,)
        )
    )[0]
    assert int(row["held_points"]) == 5000
    # 人工裁决后释放 → held 归零
    await unified.release_order_holds(
        order_changed, to_status="cancelled", reason="计划变更人工结案"
    )
    await db.commit()
    row = (
        await db.execute_fetchall(
            "SELECT held_points FROM member_balance WHERE id = ?", (account_id,)
        )
    )[0]
    assert int(row["held_points"]) == 0


# ==================== 复核 P5：manual_review 状态矩阵 ====================


@pytest.mark.asyncio
async def test_manual_review_no_side_effect_releasable_via_cancel(
    db: aiosqlite.Connection,
) -> None:
    """P5：无资产副作用的 manual_review（订单未置 paid）可随取消释放，slot 让位。"""
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
    with pytest.raises(ValueError, match="积分账户不存在"):
        await order_service.confirm_mock_payment(order_id, user_id=USER_ID)
    attempt = await PaymentAttemptRepo(db).get_active("order", order_id)
    assert attempt["status"] == "manual_review"

    cancelled = await order_service.cancel_user_order(order_id, user_id=USER_ID)
    assert cancelled["status"] == "cancelled"
    attempt_after = await PaymentAttemptRepo(db).get_by_id(attempt["id"])
    assert attempt_after["status"] == "cancelled"
    assert await PaymentAttemptRepo(db).get_active("order", order_id) is None


@pytest.mark.asyncio
async def test_manual_review_with_paid_side_effect_not_releasable(
    db: aiosqlite.Connection,
) -> None:
    """P5：已产生资产副作用（订单已 paid）的 manual_review 禁止取消释放，仅可人工结案。"""
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
    await unified.mark_manual_review(order, reason="人工复核中")
    await db.commit()
    # 构造矛盾态防御：manual_review 并存已 paid（有副作用）
    payment = loads_payment(order.payment)
    payment["status"] = "paid"
    payment["paidAt"] = now_text()
    await OrderRepo(db).update_payment(order_id, dumps_payment(payment), now_text())
    await db.commit()

    with pytest.raises(ValueError, match="仅可人工结案"):
        await unified.release_order_holds(
            order, to_status="cancelled", reason="用户取消"
        )
    attempt_after = await PaymentAttemptRepo(db).get_by_id(attempt["id"])
    assert attempt_after["status"] == "manual_review"  # 未被释放


# ==================== 复核 P6：偿债独立事实（可对账） ====================


@pytest.mark.asyncio
async def test_award_ledger_records_actual_credit_not_full_award(
    db: aiosqlite.Connection,
) -> None:
    """P6：points_ledger award 记实际入账（credit_amount），偿还部分为独立
    ledger_operation 事实；全额 award 事实在 ledger_operation settle_award
    （退款 clawback 核验依据）——余额总额与流水可对账。"""
    account_id = await _seed_member(db, points=100_000)
    debt_repo = RefundShortfallDebtRepo(db)
    await debt_repo.append(
        order_id="debt_order_p6",
        mobile=MOBILE,
        member_balance_id=account_id,
        operation_key="points:refund:debt_order_p6:clawback",
        amount=60,
        note="P6 对账测试欠账",
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

    award_entry = (
        await db.execute_fetchall(
            "SELECT amount FROM points_ledger WHERE unique_id = ?",
            (f"points:award:{order_id}",),
        )
    )[0]
    assert int(award_entry["amount"]) == 40  # award 100 - 偿债 60 = 实际入账 40
    settle_award = (
        await db.execute_fetchall(
            "SELECT amount FROM ledger_operation WHERE unique_id = ?",
            (f"ledger:settle_award:{order_id}",),
        )
    )[0]
    assert int(settle_award["amount"]) == 100  # 全额 award 事实
    debt = await debt_repo.get_by_operation_key("points:refund:debt_order_p6:clawback")
    assert int(debt["remaining"]) == 0
    assert debt["status"] == "settled"  # 60 全额偿还
    points = int(
        (
            await db.execute_fetchall(
                "SELECT points FROM member_balance WHERE id = ?", (account_id,)
            )
        )[0]["points"]
    )
    assert points == 100_000 + 40  # 余额总额 = 期初 + 实际入账（可对账）


# ==================== 复核 P7：迁移回填只覆盖 open 行 ====================


@pytest.mark.asyncio
async def test_debt_backfill_only_open_rows(db: aiosqlite.Connection) -> None:
    """P7：v027 回填只对 status='open' 的历史行置 remaining=amount；
    已结案行保持 remaining=0（status=settled 与 remaining>0 的矛盾态不存在）。"""
    await db.execute(
        "INSERT INTO refund_shortfall_debt (order_id, mobile, member_balance_id, "
        "operation_key, amount, remaining, status, created_at, updated_at) "
        "VALUES ('old_settled', '13800000000', NULL, "
        "'points:refund:old_settled:clawback', 100, 0, 'settled', "
        "datetime('now'), datetime('now'))"
    )
    await db.execute(
        "INSERT INTO refund_shortfall_debt (order_id, mobile, member_balance_id, "
        "operation_key, amount, remaining, status, created_at, updated_at) "
        "VALUES ('old_open', '13800000000', NULL, "
        "'points:refund:old_open:clawback', 100, 0, 'open', "
        "datetime('now'), datetime('now'))"
    )
    await db.commit()
    # 复现 v027 修复后的回填语义（仅 open）
    await db.execute(
        "UPDATE refund_shortfall_debt SET remaining = amount "
        "WHERE remaining = 0 AND status = 'open'"
    )
    await db.commit()
    settled = (
        await db.execute_fetchall(
            "SELECT remaining, status FROM refund_shortfall_debt "
            "WHERE order_id = 'old_settled'"
        )
    )[0]
    assert int(settled["remaining"]) == 0 and settled["status"] == "settled"
    open_row = (
        await db.execute_fetchall(
            "SELECT remaining, status FROM refund_shortfall_debt "
            "WHERE order_id = 'old_open'"
        )
    )[0]
    assert int(open_row["remaining"]) == 100 and open_row["status"] == "open"


@pytest.mark.asyncio
async def test_v027_migration_text_backfill_guarded() -> None:
    """P7（迁移文本守卫）：v027 回填 SQL 必须限定 status='open'，防止已结案行
    被回填成 remaining>0 的矛盾态（评审 P7 回归）。"""
    from pathlib import Path

    v027 = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "migrations"
        / "v027_accounting_d1a.sql"
    )
    text = v027.read_text(encoding="utf-8")
    backfill_line = next(
        line for line in text.splitlines() if "SET remaining = amount" in line
    )
    assert "status = 'open'" in backfill_line
    assert "WHERE remaining = 0" in backfill_line


# ==================== D1-A.1 复核：五项验收（R1–R5） ====================


@pytest.mark.asyncio
async def test_r1_retry_after_failed_preclaim_no_hold_leak(
    db: aiosqlite.Connection,
) -> None:
    """R1：同订单失败→重试→取消无预占泄漏（hold_key 按 payment_attempt_id 维度）。

    第一尝试多腿预占部分成功（points 腿已占 + 审计行已写）后因 balance 腿
    不足整体 failed（held 归零、审计行 released）；同订单重试的新尝试必须能
    写入自己的活跃 hold——旧的 order-scoped key 会被 released 行占据而
    INSERT OR IGNORE 静默失败（held 永久残留且取消无法定位）；取消后 held 归零。
    """
    account_id = await _seed_member(db, points=100_000)
    order_service = _order_service(db)
    order_id = await _create_order(order_service)
    # 订单快照：points 9500 + balance 1000（储值余额 0 → balance 腿预占失败）
    order = await OrderRepo(db).get_order(order_id)
    assert order is not None
    payment = loads_payment(order.payment)
    payment.update(
        {
            "status": "partial",
            "method": "combined",
            "pointsUsed": 9500,
            "pointsFen": 9500,
            "balanceFen": 1000,
            "memberBalanceId": str(account_id),
            "remainFen": 0,
        }
    )
    await OrderRepo(db).update_payment(order_id, dumps_payment(payment), now_text())
    await db.commit()
    unified = UnifiedPaymentApplicationService(order_repo=OrderRepo(db))
    # 第一尝试：points 腿预占成功 → balance 腿不足 → 整体 failed + 释放
    order_1 = await OrderRepo(db).get_order(order_id)
    with pytest.raises(ValueError, match="储值余额不足"):
        await unified.settle_mock_order(order_1)
    await db.commit()
    attempt_1 = await PaymentAttemptRepo(db).get_latest("order", order_id)
    assert attempt_1["status"] == "failed"
    row = (
        await db.execute_fetchall(
            "SELECT held_points, held_stored_value_fen FROM member_balance "
            "WHERE id = ?",
            (account_id,),
        )
    )[0]
    assert int(row["held_points"]) == 0
    assert int(row["held_stored_value_fen"]) == 0
    # 补足储值余额后同订单重试：新尝试必须写入自己的活跃 hold（attempt-scoped key）
    await db.execute(
        "UPDATE member_balance SET stored_value_fen = 100000 WHERE id = ?",
        (account_id,),
    )
    await db.commit()
    order_2 = await OrderRepo(db).get_order(order_id)
    attempt_2 = await unified.ensure_mock_attempt(order_2)
    await db.commit()
    assert attempt_2["status"] == "prepay_ready"
    holds_2 = await AccountHoldRepo(db).list_active_by_attempt(attempt_2["id"])
    assert (
        len(holds_2) == 2
    )  # points + balance 两条活跃审计行（旧 key 下 points 行缺失）
    row = (
        await db.execute_fetchall(
            "SELECT held_points, held_stored_value_fen FROM member_balance "
            "WHERE id = ?",
            (account_id,),
        )
    )[0]
    assert int(row["held_points"]) == 9500
    assert int(row["held_stored_value_fen"]) == 1000
    # 取消：释放全部预占，held 归零（旧 key 下 points held 无法定位 → 永久泄漏）
    await unified.release_order_holds(
        order_2, to_status="cancelled", reason="R1 验收取消"
    )
    await db.commit()
    row = (
        await db.execute_fetchall(
            "SELECT held_points, held_stored_value_fen FROM member_balance "
            "WHERE id = ?",
            (account_id,),
        )
    )[0]
    assert int(row["held_points"]) == 0
    assert int(row["held_stored_value_fen"]) == 0
    assert await AccountHoldRepo(db).list_active_by_attempt(attempt_2["id"]) == []
    attempt_2_after = await PaymentAttemptRepo(db).get_by_id(attempt_2["id"])
    assert attempt_2_after["status"] == "cancelled"


@pytest.mark.asyncio
async def test_r2_full_balance_payment_attempt_outbox_consistent(
    db: aiosqlite.Connection,
) -> None:
    """R2：全额储值支付 attempt/outbox 可还原完整规范支付计划。

    创建 attempt 前已把规范支付计划落库（method=balance、balanceFen、总额、
    币种、账户 ID、计划版本）——attempt 冻结快照与 order.settled outbox 载荷
    均引用该计划，provider 不再退化为 mock。
    """
    import json as _json

    from app.repository.balance_ledger_repo import BalanceLedgerRepo
    from app.service.stored_value.member import MemberBalanceService
    from app.service.stored_value.payment import StoredValueOrderPaymentService

    await db.execute(
        "INSERT INTO customer_master (id, tenant_id, status, primary_phone, "
        "phone_verified, display_name, identity_confidence, has_miniapp_identity) "
        "VALUES ('cm_r2', 'yunxi', 'active', ?, 1, 'R2 测试', 'high', 1)",
        (MOBILE,),
    )
    await db.execute(
        "INSERT INTO customer_identity_links (id, tenant_id, customer_id, "
        "identity_type, identity_value, identity_value_normalized, source_system, "
        "link_status, verification_status, confidence_score) "
        "VALUES ('cil_r2', 'yunxi', 'cm_r2', 'miniapp_openid', ?, ?, "
        "'miniapp', 'active', 'verified', 100)",
        (OPENID, OPENID),
    )
    await db.execute(
        "INSERT INTO member_balance (mobile, stored_value_fen) VALUES (?, 100000)",
        (MOBILE,),
    )
    await db.commit()
    order_service = _order_service(db)
    order_id = await _create_order(order_service)
    member_service = MemberBalanceService(
        balance_repo=MemberBalanceRepo(db),
        ledger_repo=BalanceLedgerRepo(db),
        customer_repo=CustomerMasterRepo(db),
    )
    payment_service = StoredValueOrderPaymentService(
        order_repo=OrderRepo(db),
        member_service=member_service,
    )
    paid = await payment_service.pay_order_with_balance(order_id, user_id=USER_ID)
    assert paid["paymentStatus"] == "paid"
    attempt = await PaymentAttemptRepo(db).get_latest("order", order_id)
    assert attempt["status"] == "succeeded"
    assert attempt["provider"] == "balance"  # 不再退化为 mock
    snapshot = loads_payment(attempt["payment_snapshot_json"])
    assert int(snapshot["balanceFen"]) == 10_000
    assert snapshot["method"] == "balance"
    assert int(snapshot["totalFen"]) == 10_000
    assert snapshot["currency"] == "CNY"
    assert int(snapshot["planVersion"]) == 1
    assert snapshot["memberBalanceId"]
    # outbox 载荷引用同一规范计划（可还原完整计划）
    rows = await db.execute_fetchall(
        "SELECT payload_json FROM accounting_outbox WHERE operation_key = ?",
        (f"order:settled:{order_id}",),
    )
    assert rows
    payload = _json.loads(str(rows[0]["payload_json"]))
    assert payload["attempt_id"] == attempt["id"]
    assert payload["result"] == "settled"
    payload_snapshot = payload["snapshot"]
    assert int(payload_snapshot["balanceFen"]) == 10_000
    assert payload_snapshot["method"] == "balance"
    assert payload_snapshot["memberBalanceId"] == snapshot["memberBalanceId"]


@pytest.mark.asyncio
async def test_r3_legacy_unbound_settle_never_writes_new_account(
    db: aiosqlite.Connection,
) -> None:
    """R3（结算侧）：历史快照无账户 ID + 原账户删除重建 → 禁止按手机号补绑
    结算（不写新账户），尝试转 manual_review，新账户与积分账分文未动。"""
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
    # 抹掉快照账户绑定，模拟 B3.5 前历史订单
    order = await OrderRepo(db).get_order(order_id)
    assert order is not None
    payment = loads_payment(order.payment)
    payment.pop("memberBalanceId", None)
    await OrderRepo(db).update_payment(order_id, dumps_payment(payment), now_text())
    # 删除原账户，同手机号重建（新 id）
    await db.execute("DELETE FROM member_balance WHERE id = ?", (account_id,))
    await db.execute(
        "INSERT INTO member_balance (mobile, points) VALUES (?, 100000)", (MOBILE,)
    )
    await db.commit()
    with pytest.raises(ValueError, match="禁止按手机号补绑"):
        await order_service.confirm_mock_payment(order_id, user_id=USER_ID)
    await db.commit()
    attempt = await PaymentAttemptRepo(db).get_active("order", order_id)
    assert attempt["status"] == "manual_review"
    new_rows = await db.execute_fetchall(
        "SELECT points FROM member_balance WHERE mobile = ?", (MOBILE,)
    )
    assert new_rows and int(new_rows[0]["points"]) == 100_000  # 新账户未被动
    ledger = await db.execute_fetchall(
        "SELECT COUNT(*) AS c FROM points_ledger WHERE biz_id = ?", (order_id,)
    )
    assert int(ledger[0]["c"]) == 0  # 无任何积分流水（未扣减未发分）


@pytest.mark.asyncio
async def test_r3_legacy_unbound_refund_never_writes_new_account(
    db: aiosqlite.Connection,
    points_service: PointsService,
) -> None:
    """R3（退款侧）：历史快照无账户 ID 且无结算事实 → 退款不按手机号替代
    （同手机号重建的新账户分文未动），进 account_missing 可关闭案件。"""
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
    await db.commit()
    # 抹掉快照绑定 + 删除 settle_redeem 事实（模拟 B3.5 前：无快照绑定亦无
    # 可证明原账户 ID 的结算事实）
    order = await OrderRepo(db).get_order(order_id)
    assert order is not None
    payment = loads_payment(order.payment)
    payment.pop("memberBalanceId", None)
    await OrderRepo(db).update_payment(order_id, dumps_payment(payment), now_text())
    await db.execute(
        "DELETE FROM ledger_operation WHERE operation_type = 'settle_redeem' "
        "AND subject_id = ?",
        (order_id,),
    )
    # 删除原账户，同手机号重建（新 id）
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
    order_latest = await OrderRepo(db).get_order(order_id)
    assert order_latest is not None
    await points_service.refund_points(order_latest)
    await db.commit()
    new_points = (
        await db.execute_fetchall(
            "SELECT points FROM member_balance WHERE id = ?", (new_account_id,)
        )
    )[0]["points"]
    assert int(new_points) == 100_000  # 新账户分文未动（无退回也无扣回）
    cases = await db.execute_fetchall(
        "SELECT reason FROM points_refund_reconcile WHERE unique_id = ?",
        (f"points:refund:{order_id}",),
    )
    assert cases and cases[0]["reason"] == "account_missing"


@pytest.mark.asyncio
async def test_r4_closed_case_reopens_on_recurrence(
    db: aiosqlite.Connection,
) -> None:
    """R4：案件关闭后同一冲突复发 → ensure_open_case 重新打开（版本递增），
    案件必为 open（杜绝 INSERT OR IGNORE 静默失败导致案件保持 closed）。"""
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
    assert attempt["status"] == "prepay_ready"
    # 第一次：计划变更 → 开案 + manual_review
    payment = loads_payment(order.payment)
    payment["pointsFen"] = 6000
    payment["remainFen"] = 4000
    await OrderRepo(db).update_payment(order_id, dumps_payment(payment), now_text())
    await db.commit()
    order_changed = await OrderRepo(db).get_order(order_id)
    with pytest.raises(ValueError, match="支付计划已变更"):
        await unified.settle_mock_order(order_changed)
    await db.commit()
    case_row = (
        await db.execute_fetchall(
            "SELECT id, status, version FROM points_refund_reconcile "
            "WHERE unique_id = ?",
            (f"points:settle:{order_id}",),
        )
    )[0]
    assert case_row["status"] == "open"
    case_id = int(case_row["id"])
    first_version = int(case_row["version"])
    # 人工结案关闭
    await db.execute(
        "UPDATE points_refund_reconcile SET status = 'closed', resolved_at = ?, "
        "resolution = '人工核对结案', evidence_ref = 'manual-close' "
        "WHERE id = ?",
        (now_text(), case_id),
    )
    await db.commit()
    # 复发：释放 manual_review 尝试后同订单重放（预占成功 → 计划再变）
    await unified.release_order_holds(
        order_changed, to_status="cancelled", reason="结案释放"
    )
    await db.commit()
    order_recur = await OrderRepo(db).get_order(order_id)
    attempt_2 = await unified.ensure_mock_attempt(order_recur)
    await db.commit()
    assert attempt_2["status"] == "prepay_ready"
    payment_2 = loads_payment(order_recur.payment)
    payment_2["pointsFen"] = 7000
    payment_2["remainFen"] = 3000
    await OrderRepo(db).update_payment(order_id, dumps_payment(payment_2), now_text())
    await db.commit()
    order_recur_2 = await OrderRepo(db).get_order(order_id)
    with pytest.raises(ValueError, match="支付计划已变更"):
        await unified.settle_mock_order(order_recur_2)
    await db.commit()
    case_after = (
        await db.execute_fetchall(
            "SELECT status, version FROM points_refund_reconcile WHERE id = ?",
            (case_id,),
        )
    )[0]
    assert case_after["status"] == "open"  # 关闭后复发必为 open
    assert int(case_after["version"]) == first_version + 1  # 版本递增，保留结案审计
    attempt_2_after = await PaymentAttemptRepo(db).get_by_id(attempt_2["id"])
    assert attempt_2_after["status"] == "manual_review"


@pytest.mark.asyncio
async def test_r5_points_insufficient_routes_to_manual_review(
    db: aiosqlite.Connection,
) -> None:
    """R5：结算时「积分余额不足」→ manual_review（结构化错误码分流，
    不再误入 settling_retry）。"""
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
    assert attempt["status"] == "prepay_ready"
    assert (
        await db.execute_fetchall(
            "SELECT held_points FROM member_balance WHERE id = ?", (account_id,)
        )
    )[0]["held_points"]
    # 预占成功后账户被外部挤占（余额降到不足）
    await db.execute(
        "UPDATE member_balance SET points = 1000 WHERE id = ?", (account_id,)
    )
    await db.commit()

    async def _perform() -> None:
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

    with pytest.raises(ValueError, match="积分余额不足"):
        await unified.settle_mock_order(order, settle_actions=_perform)
    await db.commit()
    attempt_after = await PaymentAttemptRepo(db).get_by_id(attempt["id"])
    assert attempt_after["status"] == "manual_review"  # 非 settling_retry
    assert "积分余额不足" in attempt_after["last_error"]


@pytest.mark.asyncio
async def test_r5_cas_conflict_on_attempt_state_visible(
    db: aiosqlite.Connection,
) -> None:
    """R5：终态写入 CAS 落空 → 失败可见且可处理——非幂等活跃状态抛显式
    并发冲突；已推进到幂等终态则接受（不重复写状态）。"""
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
    assert attempt["status"] == "prepay_ready"

    async def _cas_miss() -> bool:
        return False

    # 非幂等活跃状态（prepay_ready 未被并发推进到终态）：CAS 落空 → 显式冲突
    with pytest.raises(ValueError, match="支付尝试状态并发冲突"):
        await unified._commit_attempt_state(attempt["id"], _cas_miss())
    await db.commit()
    attempt_still = await PaymentAttemptRepo(db).get_by_id(attempt["id"])
    assert attempt_still["status"] == "prepay_ready"  # 未被半持久化覆盖

    # 幂等终态（并发已推进到 failed）：CAS 落空但接受，不重复写状态
    await db.execute(
        "UPDATE payment_attempt SET status = 'failed', "
        "state_version = state_version + 1, updated_at = ? WHERE id = ?",
        (now_text(), attempt["id"]),
    )
    await db.commit()
    await unified._commit_attempt_state(attempt["id"], _cas_miss())
    attempt_final = await PaymentAttemptRepo(db).get_by_id(attempt["id"])
    assert attempt_final["status"] == "failed"


__all__: list[str] = []
