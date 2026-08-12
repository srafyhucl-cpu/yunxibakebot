"""会员积分/优惠券/会员卡全量导入服务。

按客户主档手机号拉取有赞积分余额、会员卡与优惠券，幂等写入
member_balance / coupon_inventory；points_ledger 由 Webhook 增量维护。
"""

import json

from app.logger import setup_logger
from app.models.member import (
    CouponInventoryEntry,
    LedgerSource,
)
from app.repository.coupon_inventory_repo import CouponInventoryRepo
from app.repository.member_balance_repo import MemberBalanceRepo
from app.service.youzan.member_api import YouzanMemberApi
from app.service.youzan.member_helpers import to_fen, to_int

logger = setup_logger()


class MemberLoyaltyImportService:
    """全量导入服务：单客户三类账务数据幂等落库。"""

    def __init__(self, db, youzan_client, tenant_id: str = "yunxi") -> None:
        self._db = db
        self._tenant_id = tenant_id
        self._member_api = YouzanMemberApi(youzan_client)
        self._balance_repo = MemberBalanceRepo(db)
        self._coupon_repo = CouponInventoryRepo(db)

    async def import_one(
        self, mobile: str, customer_id: str = "", *, should_apply: bool
    ) -> dict:
        """导入单个客户账务数据并返回统计；should_apply=False 时只查询不落库。"""
        stats: dict = {
            "points_total": 0,
            "cards": 0,
            "coupons": 0,
            "errors": [],
        }
        try:
            points_total = _extract_points_total(
                await self._member_api.query_points(mobile)
            )
            stats["points_total"] = points_total
            if should_apply:
                await self._balance_repo.upsert_identity(
                    mobile=mobile,
                    customer_id=customer_id,
                    points=points_total,
                )

            cards = await self._member_api.list_customer_cards(mobile)
            stats["cards"] = len(cards)
            if should_apply and cards:
                await self._balance_repo.upsert_identity(
                    mobile=mobile,
                    customer_id=customer_id,
                    card_alias=str(
                        cards[0].get("card_alias") or cards[0].get("alias") or ""
                    ),
                    card_no=str(cards[0].get("card_no") or ""),
                    card_status=str(cards[0].get("status") or ""),
                    is_member=1,
                )

            coupons = await self._member_api.list_customer_coupons(mobile)
            stats["coupons"] = len(coupons)
            if should_apply:
                for coupon in coupons:
                    await self._upsert_coupon(coupon, mobile, customer_id)
        except Exception as exc:
            stats["errors"].append(f"{type(exc).__name__}: {exc}")
            logger.error("会员账务导入失败 mobile=%s err=%s", mobile, exc)
        return stats

    async def _upsert_coupon(self, coupon: dict, mobile: str, customer_id: str) -> None:
        """幂等写入一条优惠券库存记录。"""
        coupon_id = str(coupon.get("coupon_id") or coupon.get("id") or "")
        status = str(coupon.get("status") or "").upper()
        if not coupon_id or not status:
            return
        if await self._coupon_repo.get_by_dedup_key(coupon_id, status, mobile):
            return
        await self._coupon_repo.insert(
            CouponInventoryEntry(
                coupon_id=coupon_id,
                coupon_group_id=str(coupon.get("coupon_group_id") or ""),
                customer_id=customer_id,
                mobile=mobile,
                status=status,
                title=str(coupon.get("title") or coupon.get("coupon_name") or ""),
                value_fen=to_fen(
                    coupon.get("value")
                    or coupon.get("amount")
                    or coupon.get("coupon_value")
                ),
                detail_json=json.dumps(coupon, ensure_ascii=False),
                source=LedgerSource.IMPORT,
                occurred_at="",
            )
        )


def _extract_points_total(payload: dict) -> int:
    """从积分查询响应中提取积分余额，兼容常见字段名。"""
    for key in ("points", "total", "balance", "current_points"):
        raw = payload.get(key)
        if raw is not None:
            return to_int(raw)
    return 0
