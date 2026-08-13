"""积分支付联动测试：快照、发分、退款。"""

import aiosqlite
import pytest

from app.repository.config_repo import ConfigRepo
from app.repository.customer_master_repo import CustomerMasterRepo
from app.repository.member_balance_repo import MemberBalanceRepo
from app.repository.order_event_repo import OrderEventRepo
from app.repository.order_repo import OrderRepo
from app.repository.points_ledger_repo import PointsLedgerRepo
from app.repository.session_repo import SessionRepo
from app.repository.youzan_inventory_repo import YouzanInventoryRepo
from app.repository.youzan_repo import YouzanProductRepo
from app.service.order import OrderApplicationService
from app.service.points import PointsService

MOBILE = "13800000003"
OPENID = "openid_m3_pay_001"
USER_ID = f"wx_{OPENID}"


async def _seed_member(db: aiosqlite.Connection, *, points: int = 0) -> None:
    await db.execute(
        "INSERT INTO customer_master (id, tenant_id, status, primary_phone, "
        "phone_verified, display_name, identity_confidence, has_miniapp_identity) "
        "VALUES (?, 'yunxi', 'active', ?, 1, '积分支付测试', 'high', 1)",
        (f"cm_{OPENID}", MOBILE),
    )
    await db.execute(
        "INSERT INTO customer_identity_links (id, tenant_id, customer_id, "
        "identity_type, identity_value, identity_value_normalized, source_system, "
        "link_status, verification_status, confidence_score) "
        "VALUES (?, 'yunxi', ?, 'miniapp_openid', ?, ?, 'miniapp', 'active', "
        "'verified', 100)",
        (f"cil_{OPENID}", f"cm_{OPENID}", OPENID, OPENID),
    )
    await db.execute(
        "INSERT INTO member_balance (mobile, points) VALUES (?, ?)",
        (MOBILE, points),
    )
    await db.commit()


@pytest.fixture
def points_service(db: aiosqlite.Connection) -> PointsService:
    return PointsService(
        balance_repo=MemberBalanceRepo(db),
        ledger_repo=PointsLedgerRepo(db),
        customer_repo=CustomerMasterRepo(db),
        order_repo=OrderRepo(db),
    )


@pytest.fixture
def order_service(db: aiosqlite.Connection) -> OrderApplicationService:
    return OrderApplicationService(
        order_repo=OrderRepo(db),
        event_repo=OrderEventRepo(db),
        session_repo=SessionRepo(db),
        product_repo=YouzanProductRepo(db),
        inventory_repo=YouzanInventoryRepo(db),
        config_repo=ConfigRepo(db),
    )


async def _create_order(
    order_service: OrderApplicationService, price_fen: int = 10_000
) -> str:
    created = await order_service.create_order(
        {
            "items": [
                {
                    "productId": "p_m3_pay_001",
                    "title": "M3 支付联动蛋糕",
                    "priceFen": price_fen,
                    "quantity": 1,
                }
            ],
            "receiverName": "积分支付测试",
            "receiverPhone": MOBILE,
            "deliveryType": "delivery",
            "deliveryAddress": "积分支付测试地址",
            "expectTime": "2026-08-20 19:00",
        },
        user_id=USER_ID,
    )
    return created["orderId"]


async def _points(db: aiosqlite.Connection) -> int:
    rows = await db.execute_fetchall(
        "SELECT points FROM member_balance WHERE mobile = ? LIMIT 1", (MOBILE,)
    )
    return int(rows[0]["points"]) if rows else 0


async def _ledger_count(db: aiosqlite.Connection) -> int:
    rows = await db.execute_fetchall(
        "SELECT COUNT(*) AS c FROM points_ledger WHERE mobile = ?", (MOBILE,)
    )
    return int(rows[0]["c"])


@pytest.mark.asyncio
async def test_apply_points_writes_partial_snapshot(
    db: aiosqlite.Connection,
    points_service: PointsService,
    order_service: OrderApplicationService,
) -> None:
    """apply-points 写 partial 快照但不动积分账。"""
    await _seed_member(db, points=100_000)
    order_id = await _create_order(order_service, price_fen=10_000)
    result = await points_service.apply_points(order_id, user_id=USER_ID)
    assert result["paymentStatus"] == "partial"
    assert result["pointsFen"] == 5000
    assert result["pointsUsed"] == 5000
    assert result["remainFen"] == 5000
    assert await _points(db) == 100_000
    assert await _ledger_count(db) == 0


@pytest.mark.asyncio
async def test_award_on_payment_after_mock_pay(
    db: aiosqlite.Connection,
    points_service: PointsService,
    order_service: OrderApplicationService,
) -> None:
    """mock 支付成功后发分并扣抵扣，重复确认幂等。"""
    await _seed_member(db, points=100_000)
    order_id = await _create_order(order_service, price_fen=10_000)
    await points_service.apply_points(order_id, user_id=USER_ID)
    await order_service.confirm_mock_payment(order_id, user_id=USER_ID)
    assert await _points(db) == 95_050
    await order_service.confirm_mock_payment(order_id, user_id=USER_ID)
    assert await _points(db) == 95_050
    assert await _ledger_count(db) == 2


@pytest.mark.asyncio
async def test_refund_points_returns_used_and_claws_back_award(
    db: aiosqlite.Connection,
    points_service: PointsService,
    order_service: OrderApplicationService,
) -> None:
    """退款退回全部抵扣积分并收回全部已发积分，幂等。"""
    await _seed_member(db, points=100_000)
    order_id = await _create_order(order_service, price_fen=10_000)
    await points_service.apply_points(order_id, user_id=USER_ID)
    await order_service.confirm_mock_payment(order_id, user_id=USER_ID)
    order = await OrderRepo(db).get_order(order_id)
    await points_service.refund_points(order)
    assert await _points(db) == 100_000
    await points_service.refund_points(order)
    assert await _points(db) == 100_000
