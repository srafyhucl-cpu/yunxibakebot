from dataclasses import dataclass
from enum import StrEnum


class OrderStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    MAKING = "making"
    DELIVERING = "delivering"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass
class Order:
    id: str
    session_id: str
    channel: str
    user_id: str
    products: str  # JSON
    total_amount: float = 0.0
    delivery: str = "{}"  # JSON
    status: OrderStatus = OrderStatus.PENDING
    remark: str = ""
    created_at: str = ""
    updated_at: str = ""
