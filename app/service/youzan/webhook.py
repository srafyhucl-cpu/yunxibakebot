import hashlib
import hmac
import json

from app.exceptions import AuthError
from app.logger import setup_logger

logger = setup_logger()


def verify_signature(secret: str, raw_body: bytes, signature_header: str) -> bool:
    """Verify Youzan webhook HMAC-SHA256 signature."""
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def parse_webhook_payload(body: bytes) -> dict:
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        logger.error("Invalid Youzan webhook payload: %s", exc)
        raise AuthError("Invalid JSON payload") from exc
