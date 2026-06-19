"""小程序订单支付状态服务。"""

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from pathlib import Path
from typing import Any

import httpx
from urllib.parse import urljoin

from app.config import settings
from app.models.order import Order, OrderStatus
from app.repository.order_repo import OrderRepo
from app.service.miniapp_order_inventory import MiniappOrderInventoryService
from app.service.miniapp_order_serialization import MiniappOrderSerializationService

PAYMENT_STATUS_UNPAID = "unpaid"
PAYMENT_STATUS_PAID = "paid"
PAYMENT_STATUS_EXPIRED = "expired"
PAYMENT_METHOD_MOCK = "mock"
PAYMENT_METHOD_WECHAT = "wechat"
PAYMENT_MODE_MOCK = "mock"
PAYMENT_MODE_WECHAT = "wechat"
PAYMENT_SIGN_TYPE = "RSA"
PAYMENT_TIMEOUT_MINUTES = 30
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
WECHAT_PAY_SUCCESS_STATE = "SUCCESS"


@dataclass(frozen=True)
class PaymentSession:
    """统一支付会话返回结构。"""

    mode: str
    order_id: str
    payment_method: str
    payment_status: str
    payload: dict


@dataclass(frozen=True)
class WechatPayPrepayResult:
    """微信支付预下单结果。"""

    prepay_id: str
    appid: str


def build_initial_payment(now_text: str) -> dict:
    """构建订单初始支付状态。"""
    return {
        "status": PAYMENT_STATUS_UNPAID,
        "method": "",
        "paidAt": "",
        "expiredAt": "",
        "expiredReason": "",
        "createdAt": now_text,
    }


def build_mock_payment_session(order_id: str) -> PaymentSession:
    """构建 mock 支付会话，供开发和无商户配置环境使用。"""
    return PaymentSession(
        mode=PAYMENT_MODE_MOCK,
        order_id=order_id,
        payment_method=PAYMENT_METHOD_MOCK,
        payment_status=PAYMENT_STATUS_UNPAID,
        payload={
            "action": "mock-pay",
            "message": "当前环境未启用微信支付，使用模拟支付兜底",
        },
    )


class MiniappPaymentService:
    """处理支付确认和未支付超时释放。"""

    def __init__(
        self,
        order_repo: OrderRepo,
        inventory_service: MiniappOrderInventoryService,
    ) -> None:
        self._order_repo = order_repo
        self._inventory_service = inventory_service
        self._serializer = MiniappOrderSerializationService()

    async def prepare_payment(self, order_id: str, *, user_id: str) -> PaymentSession:
        """准备订单支付会话。"""
        order = await self._get_user_order(order_id, user_id=user_id)
        current_status = self._status_value(order)
        if current_status == OrderStatus.CANCELLED.value:
            raise ValueError("订单已取消")
        payment = self._loads_payment(order.payment)
        payment_status = str(payment.get("status", PAYMENT_STATUS_UNPAID))
        if payment_status == PAYMENT_STATUS_PAID:
            return PaymentSession(
                mode=PAYMENT_MODE_WECHAT,
                order_id=order.id,
                payment_method=str(
                    payment.get("method", PAYMENT_METHOD_WECHAT)
                    or PAYMENT_METHOD_WECHAT
                ),
                payment_status=PAYMENT_STATUS_PAID,
                payload={},
            )
        if payment_status == PAYMENT_STATUS_EXPIRED:
            raise ValueError("订单支付已超时")
        if not self._wechat_pay_ready():
            return build_mock_payment_session(order.id)
        prepay = await self._create_wechat_jsapi_prepay(order)
        payment_params = self._build_wechat_payment_params(prepay.prepay_id)
        return PaymentSession(
            mode=PAYMENT_MODE_WECHAT,
            order_id=order.id,
            payment_method=PAYMENT_METHOD_WECHAT,
            payment_status=PAYMENT_STATUS_UNPAID,
            payload=payment_params,
        )

    async def confirm_mock_payment(self, order_id: str, *, user_id: str) -> dict:
        """MVP mock 支付确认，真实微信支付接入后复用同一状态流转。"""
        order = await self._get_user_order(order_id, user_id=user_id)
        current_status = self._status_value(order)
        if current_status == OrderStatus.CANCELLED.value:
            raise ValueError("订单已取消")
        payment = self._loads_payment(order.payment)
        payment_status = str(payment.get("status", PAYMENT_STATUS_UNPAID))
        if payment_status == PAYMENT_STATUS_PAID:
            return self._serializer.serialize(order)
        if payment_status == PAYMENT_STATUS_EXPIRED:
            raise ValueError("订单支付已超时")
        now = self._now_text()
        payment.update(
            {
                "status": PAYMENT_STATUS_PAID,
                "method": PAYMENT_METHOD_MOCK,
                "paidAt": now,
            }
        )
        updated = await self._order_repo.update_payment(
            order.id, self._dumps_payment(payment), now
        )
        if updated is None:
            raise ValueError("订单不存在")
        return self._serializer.serialize(updated)

    async def handle_wechat_payment_notify(
        self,
        *,
        raw_body: bytes,
        headers: dict[str, str],
    ) -> dict:
        """处理微信支付结果通知。"""
        if not self._verify_wechat_notify_signature(raw_body, headers):
            raise ValueError("微信支付通知签名无效")
        payload = self._loads_json(raw_body.decode("utf-8"))
        resource = payload.get("resource")
        if not isinstance(resource, dict):
            raise ValueError("微信支付通知缺少 resource")
        transaction = self._decrypt_wechat_resource(resource)
        order_id = str(transaction.get("out_trade_no", "")).strip()
        if not order_id:
            raise ValueError("微信支付通知缺少订单号")
        trade_state = str(transaction.get("trade_state", "")).strip()
        if trade_state != WECHAT_PAY_SUCCESS_STATE:
            return {"orderId": order_id, "ignored": True, "tradeState": trade_state}
        paid_at = self._format_wechat_success_time(
            str(transaction.get("success_time", ""))
        )
        transaction_id = str(transaction.get("transaction_id", "")).strip()
        updated = await self._mark_wechat_payment_paid(
            order_id,
            paid_at=paid_at,
            transaction_id=transaction_id,
        )
        return self._serializer.serialize(updated)

    async def expire_unpaid_order(
        self,
        order_id: str,
        *,
        now: datetime | None = None,
        force: bool = False,
    ) -> dict:
        """关闭单个未支付订单并释放预占库存。"""
        order = await self._order_repo.get_order(order_id)
        if order is None:
            raise ValueError("订单不存在")
        current_time = now or datetime.now()
        if force and not self._is_unpaid_active(order):
            return self._serializer.serialize(order)
        if not force and not self._is_expirable(order, current_time):
            return self._serializer.serialize(order)
        expired = await self._expire_order(order, current_time)
        return self._serializer.serialize(expired)

    async def expire_unpaid_orders(
        self, orders: list[Order], *, now: datetime | None = None
    ) -> list[dict]:
        """批量关闭超时未支付订单。"""
        current_time = now or datetime.now()
        expired_orders: list[dict] = []
        for order in orders:
            if not self._is_expirable(order, current_time):
                continue
            expired = await self._expire_order(order, current_time)
            expired_orders.append(self._serializer.serialize(expired))
        return expired_orders

    async def _get_user_order(self, order_id: str, *, user_id: str) -> Order:
        order = await self._order_repo.get_order(order_id)
        if order is None or order.user_id != user_id:
            raise ValueError("订单不存在")
        return order

    async def _expire_order(self, order: Order, now: datetime) -> Order:
        payment = self._loads_payment(order.payment)
        now_text = now.strftime(TIME_FORMAT)
        payment.update(
            {
                "status": PAYMENT_STATUS_EXPIRED,
                "expiredAt": now_text,
                "expiredReason": "payment_timeout",
            }
        )
        updated = await self._order_repo.update_payment(
            order.id, self._dumps_payment(payment), now_text
        )
        if updated is None:
            raise ValueError("订单不存在")
        await self._inventory_service.release_reserved_inventory(
            self._inventory_service.items_from_order(updated)
        )
        cancelled = await self._order_repo.update_status(
            order.id,
            OrderStatus.CANCELLED.value,
            now_text,
        )
        if cancelled is None:
            raise ValueError("订单不存在")
        return cancelled

    async def _mark_wechat_payment_paid(
        self,
        order_id: str,
        *,
        paid_at: str,
        transaction_id: str,
    ) -> Order:
        order = await self._order_repo.get_order(order_id)
        if order is None:
            raise ValueError("订单不存在")
        if self._status_value(order) == OrderStatus.CANCELLED.value:
            raise ValueError("订单已取消")
        payment = self._loads_payment(order.payment)
        payment_status = str(payment.get("status", PAYMENT_STATUS_UNPAID))
        if payment_status == PAYMENT_STATUS_PAID:
            return order
        if payment_status == PAYMENT_STATUS_EXPIRED:
            raise ValueError("订单支付已超时")
        now = paid_at or self._now_text()
        payment.update(
            {
                "status": PAYMENT_STATUS_PAID,
                "method": PAYMENT_METHOD_WECHAT,
                "paidAt": now,
                "transactionId": transaction_id,
            }
        )
        updated = await self._order_repo.update_payment(
            order.id, self._dumps_payment(payment), now
        )
        if updated is None:
            raise ValueError("订单不存在")
        return updated

    def _is_expirable(self, order: Order, now: datetime) -> bool:
        if not self._is_unpaid_active(order):
            return False
        payment = self._loads_payment(order.payment)
        created_at = self._parse_time(str(payment.get("createdAt") or order.created_at))
        return created_at is not None and now - created_at >= timedelta(
            minutes=PAYMENT_TIMEOUT_MINUTES
        )

    def _is_unpaid_active(self, order: Order) -> bool:
        if self._status_value(order) == OrderStatus.CANCELLED.value:
            return False
        payment = self._loads_payment(order.payment)
        return (
            str(payment.get("status", PAYMENT_STATUS_UNPAID)) == PAYMENT_STATUS_UNPAID
        )

    def _status_value(self, order: Order) -> str:
        return (
            order.status.value if hasattr(order.status, "value") else str(order.status)
        )

    def _loads_payment(self, raw: str) -> dict:
        try:
            value = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return build_initial_payment("")
        return value if isinstance(value, dict) else build_initial_payment("")

    def _dumps_payment(self, payment: dict) -> str:
        return json.dumps(payment, ensure_ascii=False)

    def _loads_json(self, raw: str) -> dict:
        try:
            value = json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("微信支付通知 JSON 无效") from exc
        if not isinstance(value, dict):
            raise ValueError("微信支付通知 JSON 无效")
        return value

    def _parse_time(self, value: str) -> datetime | None:
        try:
            return datetime.strptime(value, TIME_FORMAT)
        except ValueError:
            return None

    def _now_text(self) -> str:
        return datetime.now().strftime(TIME_FORMAT)

    def _wechat_pay_ready(self) -> bool:
        return bool(
            settings.WECHAT_PAY_ENABLED
            and settings.WECHAT_MINIAPP_APP_ID
            and settings.WECHAT_PAY_MCH_ID
            and settings.WECHAT_PAY_NOTIFY_URL
            and settings.WECHAT_PAY_PRIVATE_KEY_PATH
            and settings.WECHAT_PAY_CERT_SERIAL_NO
            and settings.WECHAT_PAY_API_V3_KEY
        )

    def _verify_wechat_notify_signature(
        self, raw_body: bytes, headers: dict[str, str]
    ) -> bool:
        if not settings.WECHAT_PAY_PLATFORM_CERT_PATH:
            return False
        timestamp = headers.get("wechatpay-timestamp", "")
        nonce = headers.get("wechatpay-nonce", "")
        signature = headers.get("wechatpay-signature", "")
        serial = headers.get("wechatpay-serial", "")
        if not timestamp or not nonce or not signature or not serial:
            return False
        cert_path = Path(settings.WECHAT_PAY_PLATFORM_CERT_PATH)
        if not cert_path.exists():
            return False
        message = b"\n".join(
            [timestamp.encode("utf-8"), nonce.encode("utf-8"), raw_body, b""]
        )
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding

            cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
            cert.public_key().verify(
                base64.b64decode(signature),
                message,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except Exception:
            return False
        expected_serial = (
            cert.serial_number.to_bytes(
                (cert.serial_number.bit_length() + 7) // 8, "big"
            )
            .hex()
            .upper()
        )
        return compare_digest(expected_serial, serial.upper())

    def _decrypt_wechat_resource(self, resource: dict) -> dict:
        ciphertext = str(resource.get("ciphertext", ""))
        nonce = str(resource.get("nonce", ""))
        associated_data = str(resource.get("associated_data", ""))
        if not ciphertext or not nonce:
            raise ValueError("微信支付通知 resource 无效")
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM

            aesgcm = AESGCM(settings.WECHAT_PAY_API_V3_KEY.encode("utf-8"))
            plaintext = aesgcm.decrypt(
                nonce.encode("utf-8"),
                base64.b64decode(ciphertext),
                associated_data.encode("utf-8"),
            )
        except Exception as exc:
            raise ValueError("微信支付通知解密失败") from exc
        return self._loads_json(plaintext.decode("utf-8"))

    def _format_wechat_success_time(self, value: str) -> str:
        text = value.strip()
        if not text:
            return self._now_text()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return self._now_text()
        return parsed.strftime(TIME_FORMAT)

    def _build_order_description(self, order: Order) -> str:
        products = self._loads_products(order.products)
        first_item = products[0] if products else {}
        title = str(first_item.get("title", "")).strip()
        return title[:127] or "芸熙烘焙订单"

    def _loads_products(self, raw: str) -> list[dict[str, Any]]:
        try:
            value = json.loads(raw or "[]")
        except json.JSONDecodeError:
            return []
        return value if isinstance(value, list) else []

    def _extract_openid(self, user_id: str) -> str:
        value = str(user_id or "").strip()
        if value.startswith("wx_"):
            return value[3:]
        if value.startswith("openid_"):
            return value
        return ""

    def _build_wechat_auth_header(
        self, method: str, request_path: str, body: str
    ) -> str:
        timestamp = str(int(datetime.now().timestamp()))
        nonce_str = sha256(
            f"{timestamp}:{request_path}:{body}".encode("utf-8")
        ).hexdigest()[:32]
        message = "\n".join(
            [method.upper(), request_path, timestamp, nonce_str, body, ""]
        )
        signature = self._sign_with_rsa(message)
        return (
            "WECHATPAY2-SHA256-RSA2048 "
            f'mchid="{settings.WECHAT_PAY_MCH_ID}",'
            f'nonce_str="{nonce_str}",'
            f'timestamp="{timestamp}",'
            f'serial_no="{settings.WECHAT_PAY_CERT_SERIAL_NO}",'
            f'signature="{signature}"'
        )

    async def _create_wechat_jsapi_prepay(self, order: Order) -> WechatPayPrepayResult:
        """调用微信支付 API v3 JSAPI 下单并返回 prepay_id。"""
        request_path = "/v3/pay/transactions/jsapi"
        total_fen = int(round(float(order.total_amount) * 100))
        payer_openid = self._extract_openid(order.user_id)
        if not payer_openid:
            raise ValueError("当前用户未绑定微信 openid")
        body = {
            "appid": settings.WECHAT_MINIAPP_APP_ID,
            "mchid": settings.WECHAT_PAY_MCH_ID,
            "description": self._build_order_description(order),
            "out_trade_no": order.id,
            "notify_url": settings.WECHAT_PAY_NOTIFY_URL,
            "amount": {"total": total_fen, "currency": "CNY"},
            "payer": {"openid": payer_openid},
        }
        payload = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        auth_header = self._build_wechat_auth_header("POST", request_path, payload)
        async with httpx.AsyncClient(
            timeout=settings.WECHAT_MINIAPP_HTTP_TIMEOUT_SECONDS,
            trust_env=False,
        ) as client:
            response = await client.post(
                f"{settings.WECHAT_PAY_API_BASE.rstrip('/')}{request_path}",
                headers={
                    "Authorization": auth_header,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                content=payload.encode("utf-8"),
            )
            response.raise_for_status()
            data = response.json()
        prepay_id = str(data.get("prepay_id", "")).strip()
        if not prepay_id:
            raise ValueError("微信支付预下单失败")
        return WechatPayPrepayResult(
            prepay_id=prepay_id,
            appid=settings.WECHAT_MINIAPP_APP_ID,
        )

    def _build_wechat_payment_params(self, prepay_id: str) -> dict:
        """构造小程序调起支付所需参数。"""
        timestamp = str(int(datetime.now().timestamp()))
        nonce_str = sha256(f"{prepay_id}:{timestamp}".encode("utf-8")).hexdigest()[:32]
        package = f"prepay_id={prepay_id}"
        message = "\n".join(
            [
                settings.WECHAT_MINIAPP_APP_ID,
                timestamp,
                nonce_str,
                package,
                "",
            ]
        )
        sign = self._sign_with_rsa(message)
        return {
            "timeStamp": timestamp,
            "nonceStr": nonce_str,
            "package": package,
            "signType": PAYMENT_SIGN_TYPE,
            "paySign": sign,
        }

    def _sign_with_rsa(self, message: str) -> str:
        """使用商户私钥对调起支付参数做签名。"""
        private_key_path = Path(settings.WECHAT_PAY_PRIVATE_KEY_PATH)
        if not private_key_path.exists():
            raise ValueError("微信支付私钥文件不存在")
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
        except Exception as exc:  # pragma: no cover - 依赖缺失时明确报错
            raise ValueError("微信支付签名依赖不可用") from exc
        private_key = serialization.load_pem_private_key(
            private_key_path.read_bytes(),
            password=None,
        )
        signature = private_key.sign(
            message.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")
