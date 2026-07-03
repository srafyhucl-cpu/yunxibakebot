"""企微员工助手订单规划常量。"""

from __future__ import annotations

import re

DEFAULT_RESULT_LIMIT = 5
MAX_RESULT_LIMIT = 10
ORDER_NO_PATTERN = re.compile(r"\bE\d{12,}\b", re.IGNORECASE)
ORDER_PENDING_STATUSES = ("WAIT_SELLER_SEND_GOODS", "WAIT_BUYER_CONFIRM_GOODS")
ORDER_STATUS_KEYWORDS = {
    "WAIT_SELLER_SEND_GOODS": (
        "待发货",
        "没发货",
        "未发货",
        "还没发",
        "发货",
        "没处理",
    ),
    "WAIT_BUYER_CONFIRM_GOODS": ("待收货", "已发货", "配送中"),
    "TRADE_SUCCESS": ("已完成", "交易成功", "完成"),
    "TRADE_CLOSED": ("已关闭", "关闭", "取消"),
    "WAIT_BUYER_PAY": ("待付款", "未付款"),
}
ORDER_QUERY_STOP_WORDS = (
    "今天",
    "今日",
    "昨天",
    "最近",
    "订单",
    "单子",
    "单量",
    "下单",
    "哪些",
    "有哪些",
    "还有",
    "有",
    "多少",
    "几单",
    "一共",
    "总共",
    "卖了",
    "卖得最多",
    "卖得多",
    "卖爆",
    "未发货",
    "没发货",
    "发货",
    "没处理",
    "还没",
    "还",
    "待发货",
    "待处理",
    "哪个",
    "是",
    "商品",
    "库存",
    "还够",
    "够吗",
    "还有吗",
    "里有",
    "物流",
    "出物流",
    "出",
    "咋样",
    "的",
    "吗",
)
ORDER_QUERY_PUNCTUATION_PATTERN = re.compile(r"[，。？！、；：,.?!;:]")
