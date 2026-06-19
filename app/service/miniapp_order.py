"""小程序订单服务。"""

import json
from datetime import datetime
from uuid import uuid4

from app.models.order import Order, OrderEvent, OrderStatus
from app.models.session import SessionCreate
from app.constants.miniapp import MINIAPP_CHANNEL, MINIAPP_DEMO_USER_ID
from app.repository.config_repo import ConfigRepo
from app.repository.order_event_repo import OrderEventRepo
from app.repository.order_repo import OrderRepo
from app.repository.session_repo import SessionRepo
from app.repository.youzan_inventory_repo import YouzanInventoryRepo
from app.repository.youzan_repo import YouzanProductRepo
from app.service.miniapp_order_inventory import MiniappOrderInventoryService
from app.service.miniapp_order_schedule import MiniappOrderScheduleService
from app.service.miniapp_order_serialization import MiniappOrderSerializationService
from app.service.miniapp_payment import MiniappPaymentService, build_initial_payment
from app.service.shop_operations import ShopOperationsService

DEFAULT_PAGE_SIZE = 30
USER_CANCELABLE_STATUSES = {
    OrderStatus.PENDING.value,
    OrderStatus.CONFIRMED.value,
}
ADMIN_ORDER_BOARD_FILTERS = [
    {
        "key": "all",
        "label": "全部订单",
        "description": "当前筛选范围",
    },
    {
        "key": "unpaid",
        "label": "待支付",
        "description": "需要跟进付款",
    },
    {
        "key": "pending",
        "label": "待确认",
        "description": "新订单待接单",
    },
    {
        "key": "fulfilling",
        "label": "履约中",
        "description": "确认/制作/配送",
    },
    {
        "key": "done",
        "label": "已完成",
        "description": "已交付订单",
    },
    {
        "key": "closed",
        "label": "已关闭",
        "description": "取消或支付超时",
    },
]
ADMIN_ORDER_FULFILLING_STATUSES = {
    OrderStatus.CONFIRMED.value,
    OrderStatus.MAKING.value,
    OrderStatus.DELIVERING.value,
}
ADMIN_ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    OrderStatus.PENDING.value: {
        OrderStatus.CONFIRMED.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.CONFIRMED.value: {
        OrderStatus.MAKING.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.MAKING.value: {OrderStatus.DELIVERING.value, OrderStatus.DONE.value},
    OrderStatus.DELIVERING.value: {OrderStatus.DONE.value},
    OrderStatus.DONE.value: set(),
    OrderStatus.CANCELLED.value: set(),
}


class MiniappOrderService:
    """处理小程序订单草稿和后台订单查询。"""

    def __init__(
        self,
        order_repo: OrderRepo,
        session_repo: SessionRepo,
        product_repo: YouzanProductRepo,
        inventory_repo: YouzanInventoryRepo,
        config_repo: ConfigRepo,
        event_repo: OrderEventRepo | None = None,
    ) -> None:
        self._order_repo = order_repo
        self._session_repo = session_repo
        self._event_repo = event_repo
        self._inventory_service = MiniappOrderInventoryService(
            product_repo, inventory_repo
        )
        self._schedule_service = MiniappOrderScheduleService(
            ShopOperationsService(config_repo)
        )
        self._serialization_service = MiniappOrderSerializationService()
        self._payment_service = MiniappPaymentService(
            order_repo, self._inventory_service
        )

    async def create_order(
        self, payload: dict, *, user_id: str = MINIAPP_DEMO_USER_ID
    ) -> dict:
        """创建小程序订单草稿。"""
        order_items = await self._inventory_service.normalize_items(
            payload.get("items", [])
        )
        if not order_items:
            raise ValueError("订单商品不能为空")
        delivery = await self._schedule_service.build_delivery(payload)
        await self._inventory_service.reserve_inventory(order_items)
        total_fen = sum(item.price_fen * item.quantity for item in order_items)
        try:
            session = await self._session_repo.get_or_create(
                SessionCreate(id="", channel=MINIAPP_CHANNEL, user_id=user_id)
            )
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            order_id = f"mp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
            order = Order(
                id=order_id,
                session_id=session.id,
                channel=MINIAPP_CHANNEL,
                user_id=user_id,
                products=json.dumps(
                    [item.__dict__ for item in order_items], ensure_ascii=False
                ),
                total_amount=total_fen / 100,
                delivery=json.dumps(delivery, ensure_ascii=False),
                payment=json.dumps(build_initial_payment(now), ensure_ascii=False),
                status=OrderStatus.PENDING,
                remark=str(payload.get("remark", "")).strip(),
                created_at=now,
                updated_at=now,
            )
            await self._order_repo.create_order(order)
            await self._record_event(
                order_id=order.id,
                status=OrderStatus.PENDING.value,
                operator=f"miniapp:{user_id}",
                note="用户提交订单",
                created_at=now,
            )
            return {"orderId": order.id, "status": "pending", "totalFen": total_fen}
        except Exception:
            await self._inventory_service.release_reserved_inventory(order_items)
            raise

    async def list_user_orders(
        self, *, user_id: str = MINIAPP_DEMO_USER_ID
    ) -> list[dict]:
        """读取当前小程序用户订单。"""
        orders = await self._order_repo.list_by_user(user_id)
        return [self._serialization_service.serialize(order) for order in orders]

    async def get_user_order(
        self,
        order_id: str,
        *,
        user_id: str = MINIAPP_DEMO_USER_ID,
    ) -> dict:
        """读取当前小程序用户的单个订单。"""
        order = await self._order_repo.get_order(order_id)
        if order is None or order.user_id != user_id:
            raise ValueError("订单不存在")
        return self._serialization_service.serialize(
            order,
            events=await self._list_events(order_id),
        )

    async def cancel_user_order(
        self,
        order_id: str,
        *,
        user_id: str = MINIAPP_DEMO_USER_ID,
    ) -> dict:
        """小程序用户取消自己的未制作订单。"""
        order = await self._order_repo.get_order(order_id)
        if order is None or order.user_id != user_id:
            raise ValueError("订单不存在")
        current_status = (
            order.status.value if hasattr(order.status, "value") else str(order.status)
        )
        if current_status == OrderStatus.CANCELLED.value:
            return self._serialization_service.serialize(
                order,
                events=await self._list_events(order_id),
            )
        if current_status not in USER_CANCELABLE_STATUSES:
            raise ValueError("当前订单状态不允许用户取消")
        updated = await self._order_repo.update_status(
            order_id,
            OrderStatus.CANCELLED.value,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        if updated is None:
            raise ValueError("订单不存在")
        await self._record_event(
            order_id=order_id,
            status=OrderStatus.CANCELLED.value,
            operator=f"miniapp:{user_id}",
            note="用户取消订单",
            created_at=updated.updated_at,
        )
        await self._inventory_service.release_reserved_inventory(
            self._inventory_service.items_from_order(updated)
        )
        return self._serialization_service.serialize(
            updated,
            events=await self._list_events(order_id),
        )

    async def confirm_mock_payment(
        self,
        order_id: str,
        *,
        user_id: str = MINIAPP_DEMO_USER_ID,
    ) -> dict:
        """MVP mock 支付确认。"""
        return await self._payment_service.confirm_mock_payment(
            order_id, user_id=user_id
        )

    async def prepare_payment(
        self,
        order_id: str,
        *,
        user_id: str = MINIAPP_DEMO_USER_ID,
    ) -> dict:
        """准备小程序订单支付参数。"""
        session = await self._payment_service.prepare_payment(order_id, user_id=user_id)
        return {
            "mode": session.mode,
            "orderId": session.order_id,
            "paymentMethod": session.payment_method,
            "paymentStatus": session.payment_status,
            "paymentParams": session.payload,
        }

    async def handle_wechat_payment_notify(
        self,
        *,
        raw_body: bytes,
        headers: dict[str, str],
    ) -> dict:
        """处理微信支付结果通知。"""
        return await self._payment_service.handle_wechat_payment_notify(
            raw_body=raw_body,
            headers=headers,
        )

    async def expire_unpaid_order(self, order_id: str) -> dict:
        """后台手动关闭未支付订单。"""
        expired = await self._payment_service.expire_unpaid_order(order_id, force=True)
        await self._record_event(
            order_id=order_id,
            status=OrderStatus.CANCELLED.value,
            operator="admin",
            note="后台关闭未支付订单",
            created_at=str(expired.get("updatedAt", "")),
        )
        return await self.get_admin_order(order_id)

    async def expire_timeout_unpaid_orders(self) -> dict:
        """扫描并关闭已超时未支付订单。"""
        candidates = await self._order_repo.list_by_status(OrderStatus.PENDING.value)
        expired_orders = await self._payment_service.expire_unpaid_orders(candidates)
        for order in expired_orders:
            await self._record_event(
                order_id=str(order.get("id", "")),
                status=OrderStatus.CANCELLED.value,
                operator="system",
                note="未支付超时自动关闭",
                created_at=str(order.get("updatedAt", "")),
            )
        return {
            "expiredCount": len(expired_orders),
            "orders": [
                await self.get_admin_order(str(order.get("id", "")))
                for order in expired_orders
            ],
        }

    async def list_admin_orders(
        self,
        *,
        page: int = 1,
        keyword: str = "",
        status: str = "",
        board_filter: str = "",
    ) -> dict:
        """后台分页读取小程序订单。"""
        safe_page = max(page, 1)
        offset = (safe_page - 1) * DEFAULT_PAGE_SIZE
        orders = await self._order_repo.list_orders(
            keyword=keyword,
            status=status,
            board_filter=self._normalize_board_filter(board_filter),
            limit=DEFAULT_PAGE_SIZE,
            offset=offset,
        )
        total = await self._order_repo.count_orders(
            keyword=keyword,
            status=status,
            board_filter=self._normalize_board_filter(board_filter),
        )
        return {
            "items": [self._serialization_service.serialize(order) for order in orders],
            "total": total,
            "page": safe_page,
            "pageSize": DEFAULT_PAGE_SIZE,
        }

    async def get_admin_order_summary(self, *, keyword: str = "") -> dict:
        """后台读取订单经营看板汇总。"""
        rows = await self._order_repo.summarize_orders(keyword=keyword)
        cards = []
        total_count = 0
        total_fen = 0
        for config in ADMIN_ORDER_BOARD_FILTERS:
            matched_rows = [
                row for row in rows if self._summary_row_matches(config["key"], row)
            ]
            count = sum(int(row.get("order_count", 0) or 0) for row in matched_rows)
            amount_fen = sum(
                int(round(float(row.get("total_amount", 0) or 0) * 100))
                for row in matched_rows
            )
            if config["key"] == "all":
                total_count = count
                total_fen = amount_fen
            cards.append(
                {
                    **config,
                    "count": count,
                    "totalFen": amount_fen,
                }
            )
        return {
            "cards": cards,
            "totalCount": total_count,
            "totalFen": total_fen,
            "keyword": keyword,
        }

    async def get_admin_order(self, order_id: str) -> dict:
        """后台读取订单详情。"""
        order = await self._order_repo.get_order(order_id)
        if order is None:
            raise ValueError("订单不存在")
        return self._serialization_service.serialize(
            order,
            events=await self._list_events(order_id),
        )

    async def update_admin_order_status(self, order_id: str, status: str) -> dict:
        """后台更新订单履约状态。"""
        target_status = self._normalize_status(status)
        order = await self._order_repo.get_order(order_id)
        if order is None:
            raise ValueError("订单不存在")
        current_status = (
            order.status.value if hasattr(order.status, "value") else str(order.status)
        )
        if target_status == current_status:
            return self._serialization_service.serialize(order)
        if target_status not in ADMIN_ALLOWED_STATUS_TRANSITIONS.get(
            current_status, set()
        ):
            raise ValueError("当前订单状态不允许切换到目标状态")
        updated = await self._order_repo.update_status(
            order_id,
            target_status,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        if updated is None:
            raise ValueError("订单不存在")
        if target_status == OrderStatus.CANCELLED.value:
            await self._inventory_service.release_reserved_inventory(
                self._inventory_service.items_from_order(updated)
            )
        await self._record_event(
            order_id=order_id,
            status=target_status,
            operator="admin",
            note=_event_note_for_status(target_status),
            created_at=updated.updated_at,
        )
        return self._serialization_service.serialize(
            updated,
            events=await self._list_events(order_id),
        )

    def _normalize_status(self, status: str) -> str:
        value = str(status or "").strip()
        allowed = {item.value for item in OrderStatus}
        if value not in allowed:
            raise ValueError("订单状态不支持")
        return value

    def _normalize_board_filter(self, board_filter: str) -> str:
        value = str(board_filter or "").strip()
        allowed = {item["key"] for item in ADMIN_ORDER_BOARD_FILTERS}
        return value if value in allowed and value != "all" else ""

    def _summary_row_matches(self, board_filter: str, row: dict) -> bool:
        status = str(row.get("status", ""))
        payment_status = str(row.get("payment_status", "unpaid") or "unpaid")
        if board_filter == "all":
            return True
        if board_filter == "unpaid":
            return payment_status == "unpaid" and status != OrderStatus.CANCELLED.value
        if board_filter == "pending":
            return status == OrderStatus.PENDING.value
        if board_filter == "fulfilling":
            return status in ADMIN_ORDER_FULFILLING_STATUSES
        if board_filter == "done":
            return status == OrderStatus.DONE.value
        if board_filter == "closed":
            return status == OrderStatus.CANCELLED.value or payment_status == "expired"
        return False

    async def _record_event(
        self,
        *,
        order_id: str,
        status: str,
        operator: str,
        note: str,
        created_at: str,
    ) -> None:
        if self._event_repo is None:
            return
        await self._event_repo.add(
            OrderEvent(
                order_id=order_id,
                status=status,
                operator=operator,
                note=note,
                created_at=created_at,
            )
        )

    async def _list_events(self, order_id: str) -> list[OrderEvent]:
        if self._event_repo is None:
            return []
        return await self._event_repo.list_by_order(order_id)


def _event_note_for_status(status: str) -> str:
    notes = {
        OrderStatus.PENDING.value: "用户提交订单",
        OrderStatus.CONFIRMED.value: "后台确认订单",
        OrderStatus.MAKING.value: "后台标记制作中",
        OrderStatus.DELIVERING.value: "后台标记配送/待取",
        OrderStatus.DONE.value: "后台完成订单",
        OrderStatus.CANCELLED.value: "后台取消订单",
    }
    return notes.get(status, "订单状态更新")
