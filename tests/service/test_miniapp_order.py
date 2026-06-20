"""小程序订单服务测试。"""

import aiosqlite
import pytest
import json
from datetime import datetime, timedelta

from app.models.config import SHOP_OPERATIONS_KEY
from app.repository.config_repo import ConfigRepo
from app.repository.order_event_repo import OrderEventRepo
from app.repository.order_repo import OrderRepo
from app.repository.session_repo import SessionRepo
from app.repository.youzan_inventory_repo import YouzanInventoryRepo
from app.repository.youzan_repo import YouzanProductRepo
from app.service.integrations import wechat_pay
from app.service.integrations.wechat_pay import WechatPayPrepayResult
from app.service.order import OrderApplicationService
from app.service.order.inventory import OrderInventoryService
from app.service.order.payment_runtime import OrderPaymentRuntimeService
from app.service.order.payment_state import (
    PAYMENT_TIMEOUT_MINUTES,
    build_initial_payment,
)
from tests.helpers.miniapp_catalog_seed import seed_miniapp_product


@pytest.fixture
def service(db: aiosqlite.Connection) -> OrderApplicationService:
    """使用真实内存库仓储构建订单服务。"""
    return OrderApplicationService(
        order_repo=OrderRepo(db),
        event_repo=OrderEventRepo(db),
        session_repo=SessionRepo(db),
        product_repo=YouzanProductRepo(db),
        inventory_repo=YouzanInventoryRepo(db),
        config_repo=ConfigRepo(db),
    )


async def test_admin_order_status_chain_updates_miniapp_reads(
    service: OrderApplicationService,
) -> None:
    """后台完整履约状态链应同步反映到小程序订单详情和列表。"""
    user_id = "miniapp-status-chain-user"
    created = await service.create_order(
        {
            "items": [
                {
                    "productId": "p_001",
                    "title": "状态链测试蛋糕",
                    "priceFen": 26800,
                    "quantity": 1,
                }
            ],
            "receiverName": "状态测试",
            "receiverPhone": "18800000001",
            "deliveryType": "delivery",
            "deliveryAddress": "状态测试地址",
            "expectTime": "2026-06-18 19:00",
            "remark": "状态链自动化测试",
        },
        user_id=user_id,
    )
    order_id = created["orderId"]

    initial = await service.get_user_order(order_id, user_id=user_id)
    assert initial["status"] == "pending"
    assert [event["status"] for event in initial["timeline"]] == ["pending"]

    with pytest.raises(ValueError, match="当前订单状态不允许切换到目标状态"):
        await service.update_admin_order_status(order_id, "done")

    for next_status in ["confirmed", "making", "delivering", "done"]:
        updated = await service.update_admin_order_status(order_id, next_status)
        assert updated["status"] == next_status
        miniapp_detail = await service.get_user_order(order_id, user_id=user_id)
        assert miniapp_detail["status"] == next_status

    with pytest.raises(ValueError, match="当前订单状态不允许切换到目标状态"):
        await service.update_admin_order_status(order_id, "cancelled")

    user_orders = await service.list_user_orders(user_id=user_id)
    assert any(
        order["id"] == order_id and order["status"] == "done" for order in user_orders
    )
    final_detail = await service.get_user_order(order_id, user_id=user_id)
    assert [event["status"] for event in final_detail["timeline"]] == [
        "pending",
        "confirmed",
        "making",
        "delivering",
        "done",
    ]
    assert final_detail["timeline"][1]["note"] == "后台确认订单"


async def test_user_cannot_read_other_users_order(
    service: OrderApplicationService,
) -> None:
    """小程序订单详情必须校验用户归属。"""
    created = await service.create_order(
        {
            "items": [
                {
                    "productId": "p_002",
                    "title": "归属测试蛋糕",
                    "priceFen": 19800,
                    "quantity": 1,
                }
            ],
            "receiverName": "归属测试",
            "receiverPhone": "18800000002",
            "deliveryType": "pickup",
            "deliveryAddress": "",
            "expectTime": "2026-06-18 18:00",
            "remark": "",
        },
        user_id="owner-user",
    )

    with pytest.raises(ValueError, match="订单不存在"):
        await service.get_user_order(created["orderId"], user_id="other-user")


async def test_create_order_uses_catalog_price_when_stock_is_enough(
    db: aiosqlite.Connection,
    service: OrderApplicationService,
) -> None:
    """真实商品库存足够时，应使用商品宽表价格创建订单。"""
    await seed_miniapp_product(
        db,
        item_id=81001,
        title="库存充足蛋糕",
        price_fen=33800,
        stock=3,
    )

    created = await service.create_order(
        {
            "items": [
                {
                    "productId": "81001",
                    "title": "前端传入旧价格",
                    "priceFen": 1,
                    "quantity": 2,
                }
            ],
            "receiverName": "库存测试",
            "receiverPhone": "18800000003",
            "expectTime": "2026-06-18 18:00",
        },
        user_id="stock-ok-user",
    )

    assert created["totalFen"] == 67600
    row = await YouzanProductRepo(db).get_by_id(81001)
    assert row is not None
    assert row["stock"] == 1


async def test_create_order_initializes_unpaid_payment_state(
    service: OrderApplicationService,
) -> None:
    """创建订单后应处于待支付状态。"""
    created = await service.create_order(
        {
            "items": [
                {
                    "productId": "p_payment_initial",
                    "title": "支付初始状态蛋糕",
                    "priceFen": 19800,
                    "quantity": 1,
                }
            ],
            "expectTime": "2026-06-18 18:00",
        },
        user_id="payment-initial-user",
    )

    detail = await service.get_user_order(
        created["orderId"], user_id="payment-initial-user"
    )

    assert detail["paymentStatus"] == "unpaid"
    assert detail["paymentMethod"] == ""


async def test_mock_payment_marks_order_paid(service: OrderApplicationService) -> None:
    """MVP mock 支付应把订单支付状态切到已支付。"""
    user_id = "payment-paid-user"
    created = await service.create_order(
        {
            "items": [
                {
                    "productId": "p_payment_paid",
                    "title": "mock 支付蛋糕",
                    "priceFen": 19800,
                    "quantity": 1,
                }
            ],
            "expectTime": "2026-06-18 18:00",
        },
        user_id=user_id,
    )

    paid = await service.confirm_mock_payment(created["orderId"], user_id=user_id)

    assert paid["paymentStatus"] == "paid"
    assert paid["paymentMethod"] == "mock"
    assert paid["paymentPaidAt"]


async def test_prepare_payment_falls_back_to_mock_without_wechat_config(
    service: OrderApplicationService,
) -> None:
    """微信支付配置不完整时，支付准备应返回 mock 兜底会话。"""
    user_id = "payment-prepare-mock-user"
    created = await service.create_order(
        {
            "items": [
                {
                    "productId": "p_payment_prepare_mock",
                    "title": "mock 支付准备蛋糕",
                    "priceFen": 19800,
                    "quantity": 1,
                }
            ],
            "expectTime": "2026-06-18 18:00",
        },
        user_id=user_id,
    )

    session = await service.prepare_payment(created["orderId"], user_id=user_id)

    assert session["mode"] == "mock"
    assert session["paymentMethod"] == "mock"
    assert session["paymentStatus"] == "unpaid"
    assert session["paymentParams"]["action"] == "mock-pay"


async def test_prepare_payment_returns_wechat_shape_when_configured(
    service: OrderApplicationService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """微信支付配置齐全时，支付准备应返回小程序调起支付字段。"""

    async def fake_prepay(self, order):
        return WechatPayPrepayResult(
            prepay_id=f"wx-prepay-{order.id}", appid="wx-app-id"
        )

    monkeypatch.setattr(wechat_pay.settings, "WECHAT_PAY_ENABLED", True)
    monkeypatch.setattr(wechat_pay.settings, "WECHAT_MINIAPP_APP_ID", "wx-app-id")
    monkeypatch.setattr(wechat_pay.settings, "WECHAT_PAY_MCH_ID", "mch-id")
    monkeypatch.setattr(
        wechat_pay.settings,
        "WECHAT_PAY_NOTIFY_URL",
        "https://example.com/pay/notify",
    )
    monkeypatch.setattr(
        wechat_pay.settings,
        "WECHAT_PAY_PRIVATE_KEY_PATH",
        "D:/secure/apiclient_key.pem",
    )
    monkeypatch.setattr(wechat_pay.settings, "WECHAT_PAY_CERT_SERIAL_NO", "serial-no")
    monkeypatch.setattr(wechat_pay.settings, "WECHAT_PAY_API_V3_KEY", "api-v3-key")
    monkeypatch.setattr(
        OrderPaymentRuntimeService, "_create_wechat_jsapi_prepay", fake_prepay
    )
    monkeypatch.setattr(
        OrderPaymentRuntimeService,
        "_sign_with_rsa",
        lambda self, message: "signed-pay-params",
    )
    user_id = "wx_payment_prepare_wechat_openid"
    created = await service.create_order(
        {
            "items": [
                {
                    "productId": "p_payment_prepare_wechat",
                    "title": "微信支付准备蛋糕",
                    "priceFen": 19800,
                    "quantity": 1,
                }
            ],
            "expectTime": "2026-06-18 18:00",
        },
        user_id=user_id,
    )

    session = await service.prepare_payment(created["orderId"], user_id=user_id)
    params = session["paymentParams"]

    assert session["mode"] == "wechat"
    assert session["paymentMethod"] == "wechat"
    assert session["paymentStatus"] == "unpaid"
    assert set(["timeStamp", "nonceStr", "package", "signType", "paySign"]).issubset(
        params
    )
    assert params["package"].startswith("prepay_id=wx-prepay-")
    assert params["signType"] == "RSA"
    assert params["paySign"] == "signed-pay-params"


async def test_wechat_prepay_requires_bound_openid(
    service: OrderApplicationService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """真实微信支付预下单必须有可用 openid。"""
    monkeypatch.setattr(wechat_pay.settings, "WECHAT_PAY_ENABLED", True)
    monkeypatch.setattr(wechat_pay.settings, "WECHAT_MINIAPP_APP_ID", "wx-app-id")
    monkeypatch.setattr(wechat_pay.settings, "WECHAT_PAY_MCH_ID", "mch-id")
    monkeypatch.setattr(
        wechat_pay.settings,
        "WECHAT_PAY_NOTIFY_URL",
        "https://example.com/pay/notify",
    )
    monkeypatch.setattr(
        wechat_pay.settings,
        "WECHAT_PAY_PRIVATE_KEY_PATH",
        "D:/secure/apiclient_key.pem",
    )
    monkeypatch.setattr(wechat_pay.settings, "WECHAT_PAY_CERT_SERIAL_NO", "serial-no")
    monkeypatch.setattr(wechat_pay.settings, "WECHAT_PAY_API_V3_KEY", "api-v3-key")
    created = await service.create_order(
        {
            "items": [
                {
                    "productId": "p_payment_prepare_no_openid",
                    "title": "缺少 openid 支付蛋糕",
                    "priceFen": 19800,
                    "quantity": 1,
                }
            ],
            "expectTime": "2026-06-18 18:00",
        },
        user_id="demo-user-without-openid",
    )

    with pytest.raises(ValueError, match="当前用户未绑定微信 openid"):
        await service.prepare_payment(
            created["orderId"], user_id="demo-user-without-openid"
        )


async def test_unpaid_timeout_releases_reserved_stock(
    db: aiosqlite.Connection,
    service: OrderApplicationService,
) -> None:
    """未支付超时关闭时应释放真实商品预占库存。"""
    await seed_miniapp_product(
        db,
        item_id=81009,
        title="支付超时释放蛋糕",
        price_fen=19800,
        stock=1,
    )
    created = await service.create_order(
        {
            "items": [
                {
                    "productId": "81009",
                    "title": "支付超时释放蛋糕",
                    "priceFen": 19800,
                    "quantity": 1,
                }
            ],
            "expectTime": "2026-06-18 18:00",
        },
        user_id="payment-timeout-user",
    )
    reserved = await YouzanProductRepo(db).get_by_id(81009)
    assert reserved is not None
    assert reserved["stock"] == 0

    order = await OrderRepo(db).get_order(created["orderId"])
    assert order is not None
    payment_service = OrderPaymentRuntimeService(
        order_repo=OrderRepo(db),
        inventory_service=OrderInventoryService(
            YouzanProductRepo(db),
            YouzanInventoryRepo(db),
        ),
    )
    expired = await payment_service.expire_unpaid_order(
        order.id,
        now=datetime.strptime(order.created_at, "%Y-%m-%d %H:%M:%S")
        + timedelta(minutes=PAYMENT_TIMEOUT_MINUTES),
    )

    released = await YouzanProductRepo(db).get_by_id(81009)
    assert expired["status"] == "cancelled"
    assert expired["paymentStatus"] == "expired"
    assert released is not None
    assert released["stock"] == 1


async def test_expire_timeout_unpaid_orders_only_closes_expired_unpaid(
    db: aiosqlite.Connection,
    service: OrderApplicationService,
) -> None:
    """批量扫描只应关闭超时未支付订单。"""
    await seed_miniapp_product(
        db,
        item_id=81010,
        title="批量超时释放蛋糕",
        price_fen=19800,
        stock=2,
    )
    expired_created = await service.create_order(
        {
            "items": [
                {
                    "productId": "81010",
                    "title": "批量超时释放蛋糕",
                    "priceFen": 19800,
                    "quantity": 1,
                }
            ],
            "expectTime": "2026-06-18 18:00",
        },
        user_id="batch-expired-user",
    )
    fresh_created = await service.create_order(
        {
            "items": [
                {
                    "productId": "p_fresh_unpaid",
                    "title": "未超时蛋糕",
                    "priceFen": 19800,
                    "quantity": 1,
                }
            ],
            "expectTime": "2026-06-18 18:00",
        },
        user_id="batch-fresh-user",
    )
    paid_created = await service.create_order(
        {
            "items": [
                {
                    "productId": "p_paid_unpaid",
                    "title": "已支付蛋糕",
                    "priceFen": 19800,
                    "quantity": 1,
                }
            ],
            "expectTime": "2026-06-18 18:00",
        },
        user_id="batch-paid-user",
    )
    old_created_at = (
        datetime.now() - timedelta(minutes=PAYMENT_TIMEOUT_MINUTES + 1)
    ).strftime("%Y-%m-%d %H:%M:%S")
    await OrderRepo(db).update_payment(
        expired_created["orderId"],
        json.dumps(build_initial_payment(old_created_at), ensure_ascii=False),
        old_created_at,
    )
    await service.confirm_mock_payment(
        paid_created["orderId"], user_id="batch-paid-user"
    )

    result = await service.expire_timeout_unpaid_orders()

    expired_detail = await service.get_admin_order(expired_created["orderId"])
    fresh_detail = await service.get_admin_order(fresh_created["orderId"])
    paid_detail = await service.get_admin_order(paid_created["orderId"])
    row = await YouzanProductRepo(db).get_by_id(81010)
    assert result["expiredCount"] == 1
    assert expired_detail["status"] == "cancelled"
    assert expired_detail["paymentStatus"] == "expired"
    assert fresh_detail["paymentStatus"] == "unpaid"
    assert paid_detail["paymentStatus"] == "paid"
    assert row is not None
    assert row["stock"] == 2


async def test_cancel_pending_order_releases_reserved_stock(
    db: aiosqlite.Connection,
    service: OrderApplicationService,
) -> None:
    """后台取消未履约订单时，应释放小程序下单预占库存。"""
    await seed_miniapp_product(
        db,
        item_id=81005,
        title="取消释放蛋糕",
        price_fen=26800,
        stock=2,
    )

    created = await service.create_order(
        {
            "items": [
                {
                    "productId": "81005",
                    "title": "取消释放蛋糕",
                    "priceFen": 26800,
                    "quantity": 1,
                }
            ],
            "receiverName": "取消测试",
            "receiverPhone": "18800000007",
            "expectTime": "2026-06-18 18:00",
        },
        user_id="cancel-release-user",
    )
    reserved_row = await YouzanProductRepo(db).get_by_id(81005)
    assert reserved_row is not None
    assert reserved_row["stock"] == 1

    updated = await service.update_admin_order_status(created["orderId"], "cancelled")

    released_row = await YouzanProductRepo(db).get_by_id(81005)
    assert updated["status"] == "cancelled"
    assert released_row is not None
    assert released_row["stock"] == 2


async def test_user_cancel_confirmed_order_releases_reserved_stock(
    db: aiosqlite.Connection,
    service: OrderApplicationService,
) -> None:
    """小程序用户取消待确认或已确认订单时，应释放预占库存。"""
    await seed_miniapp_product(
        db,
        item_id=81007,
        title="用户取消蛋糕",
        price_fen=29800,
        stock=2,
    )
    user_id = "user-cancel-release"

    created = await service.create_order(
        {
            "items": [
                {
                    "productId": "81007",
                    "title": "用户取消蛋糕",
                    "priceFen": 29800,
                    "quantity": 1,
                }
            ],
            "receiverName": "用户取消",
            "receiverPhone": "18800000008",
            "expectTime": "2026-06-18 18:00",
        },
        user_id=user_id,
    )
    await service.update_admin_order_status(created["orderId"], "confirmed")

    cancelled = await service.cancel_user_order(created["orderId"], user_id=user_id)

    row = await YouzanProductRepo(db).get_by_id(81007)
    assert cancelled["status"] == "cancelled"
    assert row is not None
    assert row["stock"] == 2


async def test_user_cannot_cancel_making_order(
    service: OrderApplicationService,
) -> None:
    """进入制作中的订单不能再由用户取消。"""
    user_id = "user-cancel-making"
    created = await service.create_order(
        {
            "items": [
                {
                    "productId": "p_cancel_making",
                    "title": "制作中取消测试蛋糕",
                    "priceFen": 19800,
                    "quantity": 1,
                }
            ],
            "receiverName": "用户取消",
            "receiverPhone": "18800000009",
            "expectTime": "2026-06-18 18:00",
        },
        user_id=user_id,
    )
    await service.update_admin_order_status(created["orderId"], "confirmed")
    await service.update_admin_order_status(created["orderId"], "making")

    with pytest.raises(ValueError, match="当前订单状态不允许用户取消"):
        await service.cancel_user_order(created["orderId"], user_id=user_id)


async def test_duplicate_items_are_aggregated_before_stock_reservation(
    db: aiosqlite.Connection,
    service: OrderApplicationService,
) -> None:
    """同一商品重复出现时，应按合计数量预占库存。"""
    await seed_miniapp_product(
        db,
        item_id=81006,
        title="重复项蛋糕",
        price_fen=12800,
        stock=2,
    )

    with pytest.raises(ValueError, match="商品库存不足: 81006"):
        await service.create_order(
            {
                "items": [
                    {
                        "productId": "81006",
                        "title": "重复项蛋糕",
                        "priceFen": 12800,
                        "quantity": 1,
                    },
                    {
                        "productId": "81006",
                        "title": "重复项蛋糕",
                        "priceFen": 12800,
                        "quantity": 2,
                    },
                ],
                "expectTime": "2026-06-18 18:00",
            },
            user_id="duplicate-item-user",
        )

    row = await YouzanProductRepo(db).get_by_id(81006)
    assert row is not None
    assert row["stock"] == 2


async def test_create_order_rejects_insufficient_stock(
    db: aiosqlite.Connection,
    service: OrderApplicationService,
) -> None:
    """真实商品下单数量不能超过库存。"""
    await seed_miniapp_product(
        db,
        item_id=81002,
        title="库存不足蛋糕",
        price_fen=19800,
        stock=1,
    )

    with pytest.raises(ValueError, match="商品库存不足: 81002"):
        await service.create_order(
            {
                "items": [
                    {
                        "productId": "81002",
                        "title": "库存不足蛋糕",
                        "priceFen": 19800,
                        "quantity": 2,
                    }
                ],
                "receiverName": "库存测试",
                "receiverPhone": "18800000004",
                "expectTime": "2026-06-18 18:00",
            },
            user_id="stock-low-user",
        )


async def test_create_order_rejects_sold_out_or_inactive_product(
    db: aiosqlite.Connection,
    service: OrderApplicationService,
) -> None:
    """真实商品售罄或下架时不能创建订单。"""
    await seed_miniapp_product(
        db,
        item_id=81003,
        title="售罄蛋糕",
        price_fen=19800,
        stock=0,
    )
    await seed_miniapp_product(
        db,
        item_id=81004,
        title="下架蛋糕",
        price_fen=19800,
        stock=3,
        is_active=0,
    )

    with pytest.raises(ValueError, match="商品已售罄: 81003"):
        await service.create_order(
            {
                "items": [
                    {
                        "productId": "81003",
                        "title": "售罄蛋糕",
                        "priceFen": 19800,
                        "quantity": 1,
                    }
                ],
                "expectTime": "2026-06-18 18:00",
            },
            user_id="sold-out-user",
        )

    with pytest.raises(ValueError, match="商品已下架: 81004"):
        await service.create_order(
            {
                "items": [
                    {
                        "productId": "81004",
                        "title": "下架蛋糕",
                        "priceFen": 19800,
                        "quantity": 1,
                    }
                ],
                "expectTime": "2026-06-18 18:00",
            },
            user_id="inactive-user",
        )


async def test_create_order_rejects_invalid_expect_time(
    service: OrderApplicationService,
) -> None:
    """预约时间必须使用稳定格式。"""
    with pytest.raises(ValueError, match="预约时间格式应为 YYYY-MM-DD HH:mm"):
        await service.create_order(
            {
                "items": [
                    {
                        "productId": "p_invalid_time",
                        "title": "时间格式测试蛋糕",
                        "priceFen": 19800,
                        "quantity": 1,
                    }
                ],
                "expectTime": "明天下午",
            },
            user_id="invalid-time-user",
        )


async def test_create_order_rejects_time_outside_business_hours(
    service: OrderApplicationService,
) -> None:
    """预约时间必须落在店铺营业时间内。"""
    with pytest.raises(ValueError, match="预约时间不在营业时间内"):
        await service.create_order(
            {
                "items": [
                    {
                        "productId": "p_closed_time",
                        "title": "闭店时间测试蛋糕",
                        "priceFen": 19800,
                        "quantity": 1,
                    }
                ],
                "expectTime": "2026-06-18 08:30",
            },
            user_id="closed-time-user",
        )


async def test_create_order_uses_configured_business_hours(
    db: aiosqlite.Connection,
    service: OrderApplicationService,
) -> None:
    """后台营业时间配置应成为订单预约时间的后端准入规则。"""
    await ConfigRepo(db).set(
        SHOP_OPERATIONS_KEY,
        '{"businessHours": "10:00-19:30"}',
    )

    with pytest.raises(ValueError, match="预约时间不在营业时间内"):
        await service.create_order(
            {
                "items": [
                    {
                        "productId": "p_before_configured_hours",
                        "title": "营业时间配置测试蛋糕",
                        "priceFen": 19800,
                        "quantity": 1,
                    }
                ],
                "expectTime": "2026-06-18 09:30",
            },
            user_id="configured-hours-user",
        )

    created = await service.create_order(
        {
            "items": [
                {
                    "productId": "p_inside_configured_hours",
                    "title": "营业时间内测试蛋糕",
                    "priceFen": 19800,
                    "quantity": 1,
                }
            ],
            "expectTime": "2026-06-18 19:30",
        },
        user_id="configured-hours-user",
    )

    detail = await service.get_user_order(
        created["orderId"], user_id="configured-hours-user"
    )
    assert detail["expectTime"] == "2026-06-18 19:30"


async def test_invalid_expect_time_does_not_reserve_stock(
    db: aiosqlite.Connection,
    service: OrderApplicationService,
) -> None:
    """预约时间非法时不能先扣减真实商品库存。"""
    await seed_miniapp_product(
        db,
        item_id=81008,
        title="非法时间库存测试蛋糕",
        price_fen=19800,
        stock=1,
    )

    with pytest.raises(ValueError, match="预约时间不在营业时间内"):
        await service.create_order(
            {
                "items": [
                    {
                        "productId": "81008",
                        "title": "非法时间库存测试蛋糕",
                        "priceFen": 19800,
                        "quantity": 1,
                    }
                ],
                "expectTime": "2026-06-18 08:30",
            },
            user_id="invalid-time-stock-user",
        )

    row = await YouzanProductRepo(db).get_by_id(81008)
    assert row is not None
    assert row["stock"] == 1
