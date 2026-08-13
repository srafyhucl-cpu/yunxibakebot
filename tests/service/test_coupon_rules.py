"""券规则纯函数测试：可用性、抵扣、最新态。"""

from app.service.coupon.rules import (
    SOURCE_PRIORITY,
    calc_discount,
    is_coupon_available,
    latest_state,
)


def _tpl(**overrides: object) -> dict:
    base = {
        "id": "cg_001",
        "name": "满30减5",
        "coupon_type": "FULL_REDUCTION",
        "threshold_fen": 3000,
        "value_fen": 500,
        "discount_bp": 0,
        "cap_fen": 0,
        "valid_from": "2026-08-01",
        "valid_until": "2026-09-30",
        "status": "active",
    }
    base.update(overrides)
    return base


def test_source_priority_order() -> None:
    assert SOURCE_PRIORITY["order"] == 2
    assert SOURCE_PRIORITY["local"] == 2
    assert SOURCE_PRIORITY["webhook"] == 1
    assert SOURCE_PRIORITY["import"] == 1


def test_full_reduction_available_and_discount() -> None:
    tpl = _tpl()
    assert is_coupon_available(tpl, total_fen=3000, now_text="2026-08-10 12:00:00")
    assert not is_coupon_available(tpl, total_fen=2999, now_text="2026-08-10 12:00:00")
    assert calc_discount(tpl, total_fen=4000) == 500


def test_no_threshold_discount_capped() -> None:
    tpl = _tpl(coupon_type="NO_THRESHOLD", threshold_fen=0, value_fen=800)
    assert calc_discount(tpl, total_fen=500) == 500
    assert calc_discount(tpl, total_fen=1000) == 800


def test_discount_type_floor_and_cap() -> None:
    tpl = _tpl(coupon_type="DISCOUNT", discount_bp=9000, cap_fen=300)
    assert calc_discount(tpl, total_fen=10_000) == 300
    assert calc_discount(tpl, total_fen=1000) == 100
    assert is_coupon_available(tpl, total_fen=100, now_text="2026-08-10 12:00:00")


def test_validity_range() -> None:
    tpl = _tpl()
    assert not is_coupon_available(tpl, total_fen=4000, now_text="2026-07-31 23:59:59")
    assert not is_coupon_available(tpl, total_fen=4000, now_text="2026-10-01 00:00:00")
    assert not is_coupon_available(
        _tpl(status="disabled"), total_fen=4000, now_text="2026-08-10 12:00:00"
    )


def test_latest_state_youzan_priority_over_time() -> None:
    """youzan 模式：order/local 权重优先于 webhook/import，即使审计行时间更晚。"""
    rows = [
        {
            "coupon_id": "c1",
            "status": "CONSUME",
            "source": "order",
            "occurred_at": "2026-08-10 09:00:00",
            "created_at": "2026-08-10 09:00:00",
            "id": 2,
        },
        {
            "coupon_id": "c1",
            "status": "BACK",
            "source": "webhook",
            "occurred_at": "2026-08-11 09:00:00",
            "created_at": "2026-08-11 09:00:00",
            "id": 3,
        },
    ]
    assert latest_state(rows, authority="youzan")["status"] == "CONSUME"


def test_latest_state_local_ignores_audit() -> None:
    """local 模式：webhook/import 审计行不参与判定。"""
    rows = [
        {
            "coupon_id": "c1",
            "status": "TAKE",
            "source": "local",
            "occurred_at": "2026-08-10 09:00:00",
            "created_at": "2026-08-10 09:00:00",
            "id": 1,
        },
        {
            "coupon_id": "c1",
            "status": "BACK",
            "source": "webhook",
            "occurred_at": "2026-08-11 09:00:00",
            "created_at": "2026-08-11 09:00:00",
            "id": 2,
        },
    ]
    assert latest_state(rows, authority="local")["status"] == "TAKE"
