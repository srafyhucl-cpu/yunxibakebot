"""企微员工助手订单规划常量。"""

from __future__ import annotations

import re

DEFAULT_RESULT_LIMIT = 5
MAX_RESULT_LIMIT = 10
CHINESE_DAY_NUMBERS = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}
ORDER_REVENUE_KEYWORDS = (
    "营业额",
    "销售额",
    "收入",
    "流水",
    "成交额",
    "卖了多少钱",
)
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
    "本周",
    "这周",
    "本星期",
    "这个星期",
    "近一周",
    "最近一周",
    "订单",
    "单子",
    "单量",
    "下单",
    "哪些",
    "有哪些",
    "还有",
    "有",
    "多少",
    "多少钱",
    "几单",
    "一共",
    "总共",
    "卖了",
    "营业额",
    "销售额",
    "收入",
    "流水",
    "成交额",
    "卖了多少钱",
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
    "怎么样",
    "如何",
    "的",
    "吗",
)
ORDER_QUERY_PUNCTUATION_PATTERN = re.compile(r"[，。？！、；：,.?!;:]")
