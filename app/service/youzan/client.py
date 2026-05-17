from app.config import settings
from app.exceptions import APIError
from app.logger import setup_logger

logger = setup_logger()


class YouzanClient:
    """Youzan REST API client with OAuth2 token management."""

    def __init__(self) -> None:
        self._client_id = settings.YOUZAN_CLIENT_ID
        self._client_secret = settings.YOUZAN_CLIENT_SECRET
        self._kdt_id = settings.YOUZAN_KDT_ID
        self._access_token: str = ""

    async def _refresh_token(self) -> None:
        """Placeholder: implement OAuth2 token refresh."""
        self._access_token = "placeholder_token"
        logger.info("Youzan token refreshed")

    async def send_reply(self, buyer_id: str, content: str, msg_type: str = "text") -> dict:
        """Send a customer service reply to a user."""
        if not self._access_token:
            await self._refresh_token()
        logger.info("Sending reply to buyer=%s type=%s", buyer_id, msg_type)
        return {"code": 0, "message": "待接入有赞 API"}

    async def get_order(self, order_no: str) -> dict:
        """Query order details."""
        logger.info("Querying order=%s", order_no)
        return {"order_no": order_no, "status": "unknown", "message": "待接入有赞 API"}

    async def get_logistics(self, order_no: str) -> dict:
        """Query logistics tracking."""
        logger.info("Querying logistics order=%s", order_no)
        return {"order_no": order_no, "status": "unknown", "message": "待接入有赞 API"}
