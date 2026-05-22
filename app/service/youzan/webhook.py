import hashlib
import hmac
import json

from app.exceptions import AuthError
from app.logger import setup_logger

logger = setup_logger()


def verify_signature(client_id: str, client_secret: str, raw_body: bytes, signature_header: str) -> bool:
    """验证有赞消息推送签名：MD5(client_id + raw_body + client_secret)。"""
    expected = hashlib.md5((client_id + raw_body.decode("utf-8", errors="replace") + client_secret).encode()).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def parse_webhook_payload(body: bytes) -> dict:
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        logger.error("Invalid Youzan webhook payload: %s", exc)
        raise AuthError("Invalid JSON payload") from exc
