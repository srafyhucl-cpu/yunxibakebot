"""会员余额与卡片状态数据访问层。"""

from app.logger import setup_logger
from app.repository.base import BaseRepository
from app.utils import now_str

logger = setup_logger()


class MemberBalanceRepo(BaseRepository):
    """会员余额快照仓储（mobile 唯一，openid 兜底）。

    数值字段（is_member / points / stored_value_fen）传 None 表示不更新，
    显式传 0 会真实覆盖，避免默认值抹掉既有余额。
    """

    async def get_by_mobile(self, mobile: str) -> dict | None:
        """按手机号读取会员余额快照。"""
        rows = await self._db.execute_fetchall(
            "SELECT id, customer_id, mobile, yz_open_id, display_name, is_member, "
            "card_alias, card_no, card_status, points, stored_value_fen, "
            "created_at, updated_at FROM member_balance WHERE mobile = ? LIMIT 1",
            (mobile,),
        )
        return rows[0] if rows else None

    async def get_by_openid(self, yz_open_id: str) -> dict | None:
        """按有赞 openid 读取会员余额快照。"""
        if not yz_open_id:
            return None
        rows = await self._db.execute_fetchall(
            "SELECT id, customer_id, mobile, yz_open_id, display_name, is_member, "
            "card_alias, card_no, card_status, points, stored_value_fen, "
            "created_at, updated_at FROM member_balance WHERE yz_open_id = ? LIMIT 1",
            (yz_open_id,),
        )
        return rows[0] if rows else None

    async def upsert_identity(
        self,
        *,
        mobile: str,
        customer_id: str = "",
        yz_open_id: str = "",
        display_name: str = "",
        is_member: int | None = None,
        card_alias: str = "",
        card_no: str = "",
        card_status: str = "",
        points: int | None = None,
        stored_value_fen: int | None = None,
    ) -> None:
        """按 mobile（openid 兜底）幂等合并会员身份/卡片/余额快照。"""
        now = now_str()
        existing = await self.get_by_mobile(mobile) if mobile else None
        if existing is None and yz_open_id:
            existing = await self.get_by_openid(yz_open_id)
        if existing is None and not mobile and not yz_open_id:
            logger.warning("会员余额快照缺少 mobile 与 yz_open_id，跳过写入")
            return
        if existing is None:
            await self._db.execute(
                "INSERT INTO member_balance (customer_id, mobile, yz_open_id, "
                "display_name, is_member, card_alias, card_no, card_status, points, "
                "stored_value_fen, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    customer_id,
                    mobile,
                    yz_open_id,
                    display_name,
                    is_member if is_member is not None else 0,
                    card_alias,
                    card_no,
                    card_status,
                    points if points is not None else 0,
                    stored_value_fen if stored_value_fen is not None else 0,
                    now,
                    now,
                ),
            )
        else:
            await self._db.execute(
                "UPDATE member_balance SET "
                "customer_id = CASE WHEN ? != '' THEN ? ELSE customer_id END, "
                "yz_open_id = CASE WHEN ? != '' THEN ? ELSE yz_open_id END, "
                "display_name = CASE WHEN ? != '' THEN ? ELSE display_name END, "
                "is_member = CASE WHEN ? IS NOT NULL THEN ? ELSE is_member END, "
                "card_alias = CASE WHEN ? != '' THEN ? ELSE card_alias END, "
                "card_no = CASE WHEN ? != '' THEN ? ELSE card_no END, "
                "card_status = CASE WHEN ? != '' THEN ? ELSE card_status END, "
                "points = CASE WHEN ? IS NOT NULL THEN ? ELSE points END, "
                "stored_value_fen = CASE WHEN ? IS NOT NULL THEN ? ELSE "
                "stored_value_fen END, "
                "updated_at = ? WHERE id = ?",
                (
                    customer_id,
                    customer_id,
                    yz_open_id,
                    yz_open_id,
                    display_name,
                    display_name,
                    is_member,
                    is_member,
                    card_alias,
                    card_alias,
                    card_no,
                    card_no,
                    card_status,
                    card_status,
                    points,
                    points,
                    stored_value_fen,
                    stored_value_fen,
                    now,
                    int(existing["id"]),
                ),
            )
        await self._db.commit()
