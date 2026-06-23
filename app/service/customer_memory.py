"""热路径顾客记忆只读加载。"""

from typing import Any, Protocol

from app.config import settings
from app.logger import setup_logger
from app.models.customer_profile import CustomerProfile

logger = setup_logger()


class CustomerProfileRepo(Protocol):
    async def get(self, channel: str, user_id: str) -> CustomerProfile | None: ...


async def load_customer_profile(
    customer_profile_repo: CustomerProfileRepo | None,
    channel: str,
    user_id: str,
) -> CustomerProfile | None:
    """按开关只读加载顾客画像，失败时空档案降级。"""
    if not settings.ENABLE_CUSTOMER_MEMORY or customer_profile_repo is None:
        return None

    try:
        return await customer_profile_repo.get(channel, user_id)
    except Exception as exc:
        logger.warning(
            "顾客画像读取失败，空档案继续: channel=%s user=%s err=%s",
            channel,
            user_id,
            exc,
        )
        return None
