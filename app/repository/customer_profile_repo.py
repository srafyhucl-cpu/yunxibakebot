"""顾客长期记忆数据访问层。"""

from uuid import uuid4

from app.models.customer_profile import CustomerProfile, CustomerProfileUpsert
from app.repository.base import BaseRepository
from app.utils import now_str


class CustomerProfileRepo(BaseRepository):
    """顾客画像仓库：读取、写入与刷新最近交互时间。"""

    async def get(self, channel: str, user_id: str) -> CustomerProfile | None:
        rows = await self._db.execute_fetchall(
            "SELECT id, channel, user_id, display_name, preferences_json, "
            "order_summary_json, special_dates_json, allergens_json, consent_status, "
            "source_evidence_json, last_interaction_at, created_at, updated_at "
            "FROM customer_profiles WHERE channel = ? AND user_id = ?",
            (channel, user_id),
        )
        return CustomerProfile(**dict(rows[0])) if rows else None

    async def upsert(self, profile: CustomerProfileUpsert) -> CustomerProfile:
        now = now_str()
        last_interaction_at = profile.last_interaction_at or now
        await self._db.execute(
            "INSERT INTO customer_profiles ("
            "id, channel, user_id, display_name, preferences_json, order_summary_json, "
            "special_dates_json, allergens_json, consent_status, source_evidence_json, "
            "last_interaction_at, created_at, updated_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(channel, user_id) DO UPDATE SET "
            "display_name = excluded.display_name, "
            "preferences_json = excluded.preferences_json, "
            "order_summary_json = excluded.order_summary_json, "
            "special_dates_json = excluded.special_dates_json, "
            "allergens_json = excluded.allergens_json, "
            "consent_status = excluded.consent_status, "
            "source_evidence_json = excluded.source_evidence_json, "
            "last_interaction_at = excluded.last_interaction_at, "
            "updated_at = excluded.updated_at",
            (
                str(uuid4()),
                profile.channel,
                profile.user_id,
                profile.display_name,
                profile.preferences_json,
                profile.order_summary_json,
                profile.special_dates_json,
                profile.allergens_json,
                profile.consent_status,
                profile.source_evidence_json,
                last_interaction_at,
                now,
                now,
            ),
        )
        await self._db.commit()
        saved = await self.get(profile.channel, profile.user_id)
        if saved is None:
            raise RuntimeError("顾客画像写入后未能读回")
        return saved

    async def touch_interaction(self, channel: str, user_id: str) -> None:
        now = now_str()
        await self._db.execute(
            "UPDATE customer_profiles SET last_interaction_at = ?, updated_at = ? "
            "WHERE channel = ? AND user_id = ?",
            (now, now, channel, user_id),
        )
        await self._db.commit()
