"""
YouzanProductRepo / YouzanOrderRepo 数据访问层单元测试。

覆盖：upsert 写入、get 查询、时序防线（旧时间戳不覆写）、软下架。
"""

import aiosqlite
import pytest

from app.models.order import YouzanOrderData
from app.repository.youzan_order_repo import YouzanOrderRepo
from app.repository.youzan_repo import YouzanProductRepo

_TS_OLD = "2026-01-01 00:00:00"
_TS_NEW = "2026-06-01 00:00:00"


@pytest.fixture
def product_repo(db: aiosqlite.Connection) -> YouzanProductRepo:
    return YouzanProductRepo(db)


@pytest.fixture
def order_repo(db: aiosqlite.Connection) -> YouzanOrderRepo:
    return YouzanOrderRepo(db)


# ───────────── YouzanProductRepo ─────────────


async def test_product_get_by_id_returns_none_when_missing(
    product_repo: YouzanProductRepo,
) -> None:
    """不存在的商品 ID 应返回 None。"""
    assert await product_repo.get_by_id(99999) is None


async def test_product_upsert_and_get_by_id(product_repo: YouzanProductRepo) -> None:
    """写入商品后可按 item_id 读回完整数据。"""
    await product_repo.upsert_product(
        item_id=1001,
        title="草莓蛋糕",
        alias="cake-strawberry",
        price_fen=18800,
        stock=10,
        image="https://img/1.jpg",
        is_active=1,
        updated_at=_TS_NEW,
    )
    row = await product_repo.get_by_id(1001)

    assert row is not None
    assert row["title"] == "草莓蛋糕"
    assert row["price_fen"] == 18800
    assert row["alias"] == "cake-strawberry"


async def test_product_get_by_alias(product_repo: YouzanProductRepo) -> None:
    """写入商品后可按 alias 读回。"""
    await product_repo.upsert_product(
        item_id=1002,
        title="芒果蛋糕",
        alias="cake-mango",
        price_fen=22800,
        stock=5,
        image="",
        is_active=1,
        updated_at=_TS_NEW,
    )
    row = await product_repo.get_by_alias("cake-mango")

    assert row is not None
    assert row["item_id"] == 1002


async def test_product_upsert_newer_timestamp_overwrites(
    product_repo: YouzanProductRepo,
) -> None:
    """新时间戳的 upsert 应覆盖旧数据。"""
    await product_repo.upsert_product(
        item_id=1003,
        title="旧名称",
        alias="cake-old",
        price_fen=10000,
        stock=3,
        image="",
        is_active=1,
        updated_at=_TS_OLD,
    )
    await product_repo.upsert_product(
        item_id=1003,
        title="新名称",
        alias="cake-old",
        price_fen=12000,
        stock=3,
        image="",
        is_active=1,
        updated_at=_TS_NEW,
    )
    row = await product_repo.get_by_id(1003)

    assert row is not None
    assert row["title"] == "新名称"
    assert row["price_fen"] == 12000


async def test_product_upsert_older_timestamp_does_not_overwrite(
    product_repo: YouzanProductRepo,
) -> None:
    """旧时间戳的 upsert 不应覆盖新数据（时序防线）。"""
    await product_repo.upsert_product(
        item_id=1004,
        title="当前名称",
        alias="cake-guard",
        price_fen=15000,
        stock=2,
        image="",
        is_active=1,
        updated_at=_TS_NEW,
    )
    await product_repo.upsert_product(
        item_id=1004,
        title="过时推送",
        alias="cake-guard",
        price_fen=9999,
        stock=2,
        image="",
        is_active=1,
        updated_at=_TS_OLD,
    )
    row = await product_repo.get_by_id(1004)

    assert row is not None
    assert row["title"] == "当前名称"
    assert row["price_fen"] == 15000


async def test_product_delete_soft_deactivates(product_repo: YouzanProductRepo) -> None:
    """delete_product 应将 is_active 置 0（软下架），不物理删除。"""
    await product_repo.upsert_product(
        item_id=1005,
        title="待下架",
        alias="cake-delete",
        price_fen=8800,
        stock=1,
        image="",
        is_active=1,
        updated_at=_TS_OLD,
    )
    await product_repo.delete_product(item_id=1005, updated_at=_TS_NEW)

    row = await product_repo.get_by_id(1005)
    assert row is not None
    assert row["is_active"] == 0


# ───────────── YouzanOrderRepo ─────────────


async def test_order_get_by_order_no_returns_none_when_missing(
    order_repo: YouzanOrderRepo,
) -> None:
    """不存在的订单号应返回 None。"""
    assert await order_repo.get_by_order_no("NO_EXIST_999") is None


async def test_order_upsert_and_get(order_repo: YouzanOrderRepo) -> None:
    """写入订单后可按订单号读回完整数据。"""
    await order_repo.upsert_order(
        YouzanOrderData(
            order_no="E202600001",
            buyer_id="buyer_aaa",
            status="TRADE_PAID",
            amount_fen=18800,
            product_titles="草莓蛋糕 x 1",
            total_quantity=1,
            created_at=_TS_NEW,
            updated_at=_TS_NEW,
        )
    )
    row = await order_repo.get_by_order_no("E202600001")

    assert row is not None
    assert row["status"] == "TRADE_PAID"
    assert row["amount_fen"] == 18800
    assert row["buyer_id"] == "buyer_aaa"


async def test_order_upsert_newer_timestamp_overwrites(
    order_repo: YouzanOrderRepo,
) -> None:
    """新时间戳的 upsert 应覆盖旧订单状态。"""
    await order_repo.upsert_order(
        YouzanOrderData(
            order_no="E202600002",
            buyer_id="buyer_bbb",
            status="TRADE_PAID",
            amount_fen=10000,
            product_titles="芒果蛋糕 x 1",
            total_quantity=1,
            created_at=_TS_OLD,
            updated_at=_TS_OLD,
        )
    )
    await order_repo.upsert_order(
        YouzanOrderData(
            order_no="E202600002",
            buyer_id="buyer_bbb",
            status="TRADE_SUCCESS",
            amount_fen=10000,
            logistics_no="SF1234567890",
            logistics_status="已签收",
            product_titles="芒果蛋糕 x 1",
            total_quantity=1,
            created_at=_TS_OLD,
            updated_at=_TS_NEW,
        )
    )
    row = await order_repo.get_by_order_no("E202600002")

    assert row is not None
    assert row["status"] == "TRADE_SUCCESS"
    assert row["logistics_no"] == "SF1234567890"


async def test_order_upsert_older_timestamp_does_not_overwrite(
    order_repo: YouzanOrderRepo,
) -> None:
    """旧时间戳的 upsert 不应覆盖新订单数据（时序防线）。"""
    await order_repo.upsert_order(
        YouzanOrderData(
            order_no="E202600003",
            buyer_id="buyer_ccc",
            status="TRADE_SUCCESS",
            amount_fen=22000,
            logistics_no="YT9999",
            logistics_status="已签收",
            product_titles="提拉米苏 x 2",
            total_quantity=2,
            created_at=_TS_OLD,
            updated_at=_TS_NEW,
        )
    )
    await order_repo.upsert_order(
        YouzanOrderData(
            order_no="E202600003",
            buyer_id="buyer_ccc",
            status="TRADE_PAID",
            amount_fen=22000,
            product_titles="提拉米苏 x 2",
            total_quantity=2,
            created_at=_TS_OLD,
            updated_at=_TS_OLD,
        )
    )
    row = await order_repo.get_by_order_no("E202600003")

    assert row is not None
    assert row["status"] == "TRADE_SUCCESS"
    assert row["logistics_no"] == "YT9999"
