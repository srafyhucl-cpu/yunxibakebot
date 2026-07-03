"""企微智能机器人 URL 回调服务。"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass
from typing import Any

from app.logger import setup_logger
from app.service.wecom.crypto import (
    decrypt,
    encrypt,
    generate_signature,
    verify_signature,
)
from app.service.wecom.intelligent_bot_dispatcher import WeComBotMessageDispatcher
from app.service.wecom.intelligent_bot_messages import (
    build_stream_reply,
    is_message_callback,
)

logger = setup_logger()

RECEIVE_ID = ""
ERROR_REPLY = "查询失败，请稍后重试或进入后台核对。"
STREAM_ID_FALLBACK_PREFIX = "yunxi"


@dataclass(frozen=True)
class WeComBotCallbackConfig:
    """企微智能机器人 URL 回调配置。"""

    token: str
    encoding_aes_key: str

    @property
    def is_ready(self) -> bool:
        return bool(self.token.strip() and self.encoding_aes_key.strip())


@dataclass(frozen=True)
class WeComBotEncryptedReply:
    """企微智能机器人被动回复密文包。"""

    encrypt: str
    msgsignature: str
    timestamp: int
    nonce: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "encrypt": self.encrypt,
            "msgsignature": self.msgsignature,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        }


class WeComBotCallbackError(ValueError):
    """智能机器人回调处理错误。"""


class WeComBotCallbackService:
    """处理企微智能机器人 URL 回调验签、解密和被动回复。"""

    def __init__(
        self,
        *,
        config: WeComBotCallbackConfig,
        dispatcher: WeComBotMessageDispatcher,
    ) -> None:
        self._config = config
        self._dispatcher = dispatcher

    def verify_url(
        self,
        *,
        msg_signature: str,
        timestamp: str,
        nonce: str,
        echostr: str,
    ) -> str:
        """验证智能机器人 URL 回调配置。"""
        self._ensure_ready()
        if not verify_signature(
            self._config.token,
            timestamp,
            nonce,
            echostr,
            msg_signature,
        ):
            raise WeComBotCallbackError("签名验证失败")
        return decrypt(self._config.encoding_aes_key, echostr)

    async def handle_callback(
        self,
        *,
        encrypted_payload: dict[str, Any],
        msg_signature: str,
        timestamp: str,
        nonce: str,
    ) -> WeComBotEncryptedReply | None:
        """处理智能机器人 POST 回调。"""
        self._ensure_ready()
        msg_encrypt = _extract_encrypt(encrypted_payload)
        if not verify_signature(
            self._config.token,
            timestamp,
            nonce,
            msg_encrypt,
            msg_signature,
        ):
            raise WeComBotCallbackError("签名验证失败")
        message = self._decrypt_message(msg_encrypt)
        if not is_message_callback(message):
            logger.info("收到企微智能机器人非消息回调 type=%s", message.get("msgtype"))
            return None
        reply_text = await self._dispatch_message(message)
        return self._encrypt_reply(_build_message_reply(message, reply_text), nonce)

    def _decrypt_message(self, msg_encrypt: str) -> dict[str, Any]:
        plaintext = decrypt(self._config.encoding_aes_key, msg_encrypt)
        try:
            message = json.loads(plaintext)
        except json.JSONDecodeError as exc:
            raise WeComBotCallbackError("明文 JSON 解析失败") from exc
        if not isinstance(message, dict):
            raise WeComBotCallbackError("明文不是 JSON 对象")
        return message

    async def _dispatch_message(self, message: dict[str, Any]) -> str:
        try:
            return await self._dispatcher.dispatch_message(message)
        except Exception as exc:
            logger.error("企微智能机器人消息处理失败: %s", exc)
            return ERROR_REPLY

    def _encrypt_reply(
        self,
        reply_payload: dict[str, Any],
        nonce: str,
    ) -> WeComBotEncryptedReply:
        timestamp = int(time.time())
        plaintext = json.dumps(reply_payload, ensure_ascii=False, separators=(",", ":"))
        msg_encrypt = encrypt(self._config.encoding_aes_key, plaintext, RECEIVE_ID)
        msg_signature = generate_signature(
            self._config.token,
            str(timestamp),
            nonce,
            msg_encrypt,
        )
        return WeComBotEncryptedReply(
            encrypt=msg_encrypt,
            msgsignature=msg_signature,
            timestamp=timestamp,
            nonce=nonce,
        )

    def _ensure_ready(self) -> None:
        if not self._config.is_ready:
            raise WeComBotCallbackError(
                "企微智能机器人回调 Token 或 EncodingAESKey 未配置"
            )


def _extract_encrypt(encrypted_payload: dict[str, Any]) -> str:
    msg_encrypt = encrypted_payload.get("encrypt")
    if not isinstance(msg_encrypt, str) or not msg_encrypt.strip():
        raise WeComBotCallbackError("缺少 encrypt 字段")
    return msg_encrypt.strip()


def _build_message_reply(message: dict[str, Any], reply_text: str) -> dict[str, Any]:
    return build_stream_reply(
        _build_stream_id(message),
        reply_text,
        finish=True,
    )


def _build_stream_id(message: dict[str, Any]) -> str:
    msgid = message.get("msgid")
    if isinstance(msgid, str) and msgid.strip():
        return msgid.strip()
    return f"{STREAM_ID_FALLBACK_PREFIX}-{new_nonce()}"


def new_nonce() -> str:
    """生成回调回复随机串。"""
    return secrets.token_hex(8)
