"""小程序券 API 测试。"""

import aiosqlite
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.channels.storefront.coupons import create_storefront_coupons_router
from app.repository.coupon_inventory_repo import CouponInventoryRepo
from app.repository.coupon_template_repo import CouponTemplateRepo
from app.repository.customer_master_repo import CustomerMasterRepo
from app.repository.order_repo import OrderRepo
from app.service.coupon import CouponService

MOBILE = "13800000005"
OPENID = "openid_m4_coupon_api"
USER_ID = f"wx_{OPENID}"


def _build_app(db: aiosqlite.Connection) -> FastAPI:
    service = CouponService(
        template_repo=CouponTemplateRepo(db),
        inventory_repo=CouponInventoryRepo(db),
        customer_repo=CustomerMasterRepo(db),
        order_repo=OrderRepo(db),
    )
    app = FastAPI()
    app.include_router(create_storefront_coupons_router(service))
    return app


@pytest.fixture
def client(db: aiosqlite.Connection) -> TestClient:
    return TestClient(_build_app(db))


def test_coupons_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/miniapp/coupons")
    assert resp.status_code == 401


def test_coupons_returns_error_when_user_not_member(client: TestClient) -> None:
    resp = client.get("/api/v1/miniapp/coupons", headers={"x-miniapp-user-id": USER_ID})
    assert resp.status_code in (400, 401)
