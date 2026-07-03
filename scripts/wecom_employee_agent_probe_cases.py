"""企微员工助手自由问法探针样本。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class EmployeeAgentProbeCase:
    name: str
    query: str
    expected_intent: str
    expected_tools: tuple[str, ...] = ()
    expected_kind: str = ""
    expected_date_from: str = ""
    expected_date_to: str = ""
    expected_date_field: str = ""
    expected_statuses: tuple[str, ...] = ()
    expected_keyword: str | None = None
    expected_missing_logistics: bool | None = None
    expected_needs_refund: bool | None = None
    expected_fulfillment_risk: bool | None = None
    expected_delivery_time_start: str = ""
    expected_delivery_time_end: str = ""
    required_any_terms: tuple[str, ...] = ()
    required_all_terms: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()


def default_probe_cases(today: date) -> tuple[EmployeeAgentProbeCase, ...]:
    today_text = today.isoformat()
    tomorrow_text = date.fromordinal(today.toordinal() + 1).isoformat()
    after_tomorrow_text = date.fromordinal(today.toordinal() + 2).isoformat()
    weekend_start_text, weekend_end_text = _weekend_text_range(today)
    recent_three_days_text = date.fromordinal(today.toordinal() - 2).isoformat()
    week_start_text = date.fromordinal(today.toordinal() - today.weekday()).isoformat()
    month_day_text = date(today.year, 7, 5).isoformat()
    return (
        *_order_summary_probe_cases(today_text),
        *_order_list_probe_cases(
            today_text,
            tomorrow_text,
            after_tomorrow_text,
            weekend_start_text,
            weekend_end_text,
        ),
        *_order_product_probe_cases(
            today_text,
            recent_three_days_text,
            week_start_text,
            month_day_text,
        ),
        *_channel_tool_probe_cases(),
        *_ops_status_probe_cases(),
        *_ops_business_probe_cases(),
        *_casual_order_probe_cases(today_text),
        *_casual_support_probe_cases(),
    )


def _order_summary_probe_cases(today_text: str) -> tuple[EmployeeAgentProbeCase, ...]:
    return (
        EmployeeAgentProbeCase(
            "today-order-summary",
            "今天一共多少订单",
            "order_query",
            ("order_dynamic_query",),
            "summary",
            today_text,
            today_text,
            expected_keyword="",
            required_any_terms=("单",),
            forbidden_terms=("完整订单号",),
        ),
        EmployeeAgentProbeCase(
            "today-revenue-summary",
            "今天营业额多少",
            "order_query",
            ("order_dynamic_query",),
            "summary",
            today_text,
            today_text,
            expected_keyword="",
            required_any_terms=("元", "营业额", "销售额"),
            forbidden_terms=(
                "完整订单号",
                "手机号",
                "未找到",
                "暂无数据",
                "暂无销售额",
                "暂无营业额",
                "无销售额",
                "无营业额",
                "后台订单页",
                "后台订单页核对",
                "请确认查询条件",
            ),
        ),
        EmployeeAgentProbeCase(
            "today-refund-summary",
            "今天有退款订单吗",
            "order_query",
            ("order_dynamic_query",),
            "summary",
            today_text,
            today_text,
            expected_keyword="",
            expected_needs_refund=True,
            required_any_terms=("退款", "售后", "退单", "单"),
            forbidden_terms=("退款规则", "话术", "完整订单号", "手机号"),
        ),
    )


def _order_list_probe_cases(
    today_text: str,
    tomorrow_text: str,
    after_tomorrow_text: str,
    weekend_start_text: str,
    weekend_end_text: str,
) -> tuple[EmployeeAgentProbeCase, ...]:
    return (
        EmployeeAgentProbeCase(
            "pending-shipment-customer-reply",
            "还有哪些没发货，怎么跟客户说",
            "multi_tool",
            ("order_dynamic_query", "knowledge_answer"),
            "list",
            expected_statuses=("WAIT_SELLER_SEND_GOODS",),
            expected_keyword="",
            required_any_terms=("待发货", "未发货", "发货", "回复", "客户"),
            forbidden_terms=("完整订单号", "手机号", "完整地址"),
        ),
        EmployeeAgentProbeCase(
            "pending-shipment-list",
            "还有哪些没发货",
            "order_query",
            ("order_dynamic_query",),
            "list",
            expected_statuses=("WAIT_SELLER_SEND_GOODS",),
            expected_keyword="",
            required_any_terms=("待发货", "未发货", "发货"),
            forbidden_terms=(
                "完整订单号",
                "手机号",
                "未在系统匹配",
                "未找到匹配商品",
            ),
        ),
        EmployeeAgentProbeCase(
            "missing-logistics-list",
            "还没物流的订单有哪些",
            "order_query",
            ("order_dynamic_query",),
            "list",
            expected_missing_logistics=True,
            expected_keyword="",
            required_any_terms=("物流",),
            forbidden_terms=(
                "完整订单号",
                "手机号",
                "未在系统匹配",
                "未找到匹配商品",
            ),
        ),
        EmployeeAgentProbeCase(
            "fulfillment-risk-list",
            "哪些单快超时了",
            "order_query",
            ("order_dynamic_query",),
            "list",
            expected_statuses=("WAIT_SELLER_SEND_GOODS", "WAIT_BUYER_CONFIRM_GOODS"),
            expected_keyword="",
            expected_fulfillment_risk=True,
            required_any_terms=("超时", "约送", "待发货", "待收货", "发货"),
            forbidden_terms=("完整订单号", "手机号", "完整地址"),
        ),
        EmployeeAgentProbeCase(
            "evening-pending-orders",
            "晚上还有哪些待处理订单",
            "order_query",
            ("order_dynamic_query",),
            "list",
            today_text,
            today_text,
            "delivery_time",
            expected_statuses=("WAIT_SELLER_SEND_GOODS", "WAIT_BUYER_CONFIRM_GOODS"),
            expected_keyword="",
            expected_delivery_time_start="18:00",
            expected_delivery_time_end="23:59",
            required_any_terms=("待处理", "约送", "晚上", "待发货", "待收货"),
            forbidden_terms=("完整订单号", "手机号", "完整地址"),
        ),
        EmployeeAgentProbeCase(
            "tomorrow-pending-orders",
            "明天有哪些待处理订单",
            "order_query",
            ("order_dynamic_query",),
            "list",
            tomorrow_text,
            tomorrow_text,
            "delivery_time",
            expected_statuses=("WAIT_SELLER_SEND_GOODS", "WAIT_BUYER_CONFIRM_GOODS"),
            expected_keyword="",
            required_any_terms=("待处理", "约送", "明天", "待发货", "待收货"),
            forbidden_terms=("完整订单号", "手机号", "完整地址"),
        ),
        EmployeeAgentProbeCase(
            "after-tomorrow-pending-orders",
            "后天有哪些待处理订单",
            "order_query",
            ("order_dynamic_query",),
            "list",
            after_tomorrow_text,
            after_tomorrow_text,
            "delivery_time",
            expected_statuses=("WAIT_SELLER_SEND_GOODS", "WAIT_BUYER_CONFIRM_GOODS"),
            expected_keyword="",
            required_any_terms=("待处理", "约送", "后天", "待发货", "待收货"),
            forbidden_terms=("完整订单号", "手机号", "完整地址"),
        ),
        EmployeeAgentProbeCase(
            "weekend-pending-orders",
            "周末有哪些待处理订单",
            "order_query",
            ("order_dynamic_query",),
            "list",
            weekend_start_text,
            weekend_end_text,
            "delivery_time",
            expected_statuses=("WAIT_SELLER_SEND_GOODS", "WAIT_BUYER_CONFIRM_GOODS"),
            expected_keyword="",
            required_any_terms=("待处理", "约送", "周末", "待发货", "待收货"),
            forbidden_terms=("完整订单号", "手机号", "完整地址"),
        ),
    )


def _order_product_probe_cases(
    today_text: str,
    recent_three_days_text: str,
    week_start_text: str,
    month_day_text: str,
) -> tuple[EmployeeAgentProbeCase, ...]:
    return (
        EmployeeAgentProbeCase(
            "product-order-summary",
            "椰椰凤梨今天卖了几单",
            "order_query",
            ("order_dynamic_query",),
            "summary",
            today_text,
            today_text,
            expected_keyword="椰椰凤梨",
            required_any_terms=("单",),
            forbidden_terms=(
                "完整订单号",
                "手机号",
                "未在系统匹配",
                "未找到匹配商品",
            ),
        ),
        EmployeeAgentProbeCase(
            "recent-days-product-order-summary",
            "最近3天椰椰凤梨卖了几单",
            "order_query",
            ("order_dynamic_query",),
            "summary",
            recent_three_days_text,
            today_text,
            expected_keyword="椰椰凤梨",
            required_any_terms=("单",),
            forbidden_terms=("完整订单号", "手机号"),
        ),
        EmployeeAgentProbeCase(
            "month-day-product-order-summary",
            "7月5日椰椰凤梨卖了几单",
            "order_query",
            ("order_dynamic_query",),
            "summary",
            month_day_text,
            month_day_text,
            expected_keyword="椰椰凤梨",
            required_any_terms=("单",),
            forbidden_terms=("完整订单号", "手机号"),
        ),
        EmployeeAgentProbeCase(
            "top-products",
            "今天哪个商品卖得多",
            "order_query",
            ("order_dynamic_query",),
            "top_products",
            today_text,
            today_text,
            expected_keyword="",
            required_any_terms=("销量",),
            forbidden_terms=("完整订单号", "手机号"),
        ),
        EmployeeAgentProbeCase(
            "this-week-top-products",
            "本周哪个商品卖得多",
            "order_query",
            ("order_dynamic_query",),
            "top_products",
            week_start_text,
            today_text,
            expected_keyword="",
            required_any_terms=("销量",),
            forbidden_terms=("完整订单号", "手机号"),
        ),
        EmployeeAgentProbeCase(
            "this-week-revenue-summary",
            "本周销售额怎么样",
            "order_query",
            ("order_dynamic_query",),
            "summary",
            week_start_text,
            today_text,
            expected_keyword="",
            required_any_terms=("元", "销售额", "营业额"),
            forbidden_terms=(
                "完整订单号",
                "手机号",
                "未找到",
                "暂无数据",
                "暂无销售额",
                "暂无营业额",
                "无销售额",
                "无营业额",
                "后台订单页",
                "后台订单页核对",
                "请确认查询条件",
            ),
        ),
        EmployeeAgentProbeCase(
            "this-week-refund-summary",
            "本周退款多少",
            "order_query",
            ("order_dynamic_query",),
            "summary",
            week_start_text,
            today_text,
            expected_keyword="",
            expected_needs_refund=True,
            required_any_terms=("退款", "售后", "退单", "元", "单"),
            forbidden_terms=("退款规则", "话术", "完整订单号", "手机号"),
        ),
        EmployeeAgentProbeCase(
            "order-product-inventory",
            "今天订单里有伯牙绝弦吗，库存还够吗",
            "multi_tool",
            ("order_dynamic_query", "product_lookup"),
            "list",
            today_text,
            today_text,
            expected_keyword="伯牙绝弦",
            required_all_terms=("库存", "72"),
            forbidden_terms=(
                "完整订单号",
                "手机号",
                "未匹配到商品",
                "未在系统匹配",
                "未找到匹配商品",
            ),
        ),
    )


def _channel_tool_probe_cases() -> tuple[EmployeeAgentProbeCase, ...]:
    return (
        EmployeeAgentProbeCase(
            "casual-inventory",
            "伯牙绝弦还有吗",
            "product_query",
            ("product_lookup",),
            required_all_terms=("库存", "72"),
            forbidden_terms=(
                "完整订单号",
                "手机号",
                "未匹配到商品",
                "未在系统匹配",
                "未找到匹配商品",
            ),
        ),
        EmployeeAgentProbeCase(
            "product-stock-recommend-replacement",
            "伯牙绝弦库存不够怎么推荐替代",
            "multi_tool",
            ("product_lookup", "knowledge_answer"),
            required_all_terms=("库存", "72"),
            required_any_terms=("推荐", "替代", "客户", "回复"),
            forbidden_terms=(
                "完整订单号",
                "手机号",
                "完整地址",
                "未匹配到商品",
                "未在系统匹配",
                "未找到匹配商品",
            ),
        ),
        EmployeeAgentProbeCase(
            "product-stock-customer-reply",
            "伯牙绝弦没货怎么跟客户说",
            "multi_tool",
            ("product_lookup", "knowledge_answer"),
            required_all_terms=("库存", "72"),
            required_any_terms=("客户", "回复", "话术", "替代"),
            forbidden_terms=(
                "完整订单号",
                "手机号",
                "完整地址",
                "未匹配到商品",
                "未在系统匹配",
                "未找到匹配商品",
            ),
        ),
        EmployeeAgentProbeCase(
            "delivery-knowledge",
            "明天能配送吗",
            "knowledge_answer",
            ("knowledge_answer",),
            required_any_terms=("配送",),
            forbidden_terms=("订单尾号", "订单状态", "订单页", "后台订单"),
        ),
    )


def _ops_status_probe_cases() -> tuple[EmployeeAgentProbeCase, ...]:
    return (
        EmployeeAgentProbeCase(
            "ops-status",
            "系统今天有没有异常",
            "ops_query",
            ("ops_summary",),
            required_any_terms=("系统", "观察台", "状态"),
            forbidden_terms=("完整订单号", "手机号"),
        ),
        EmployeeAgentProbeCase(
            "handoff-pending",
            "现在有哪些待人工",
            "ops_query",
            ("handoff_pending",),
            required_any_terms=("待人工", "转人工"),
            forbidden_terms=("买家", "ID:", "user"),
        ),
    )


def _ops_business_probe_cases() -> tuple[EmployeeAgentProbeCase, ...]:
    return (
        EmployeeAgentProbeCase(
            "customer-lookup",
            "查一下张三地址线索",
            "ops_query",
            ("customer_lookup",),
            required_any_terms=("客户", "地址", "线索"),
            forbidden_terms=(
                "完整地址",
                "手机号",
                "买家ID",
                "订单尾号",
                "尾号",
                "后台订单",
            ),
        ),
        EmployeeAgentProbeCase(
            "group-campaign-summary",
            "汇总 campaignId:abc123",
            "ops_query",
            ("group_campaign_summary",),
            required_any_terms=(
                "群活动",
                "客户群",
                "campaignId",
                "campaign",
                "活动批次",
            ),
            forbidden_terms=(
                "手机号",
                "完整地址",
                "库存",
                "小程序商品",
                "退款",
                "后台订单",
            ),
        ),
        EmployeeAgentProbeCase(
            "offline-review-summary",
            "昨晚离线复盘结果",
            "ops_query",
            ("offline_review_summary",),
            required_any_terms=("离线复盘", "复盘"),
            forbidden_terms=("手机号", "完整地址", "买家ID"),
        ),
    )


def _casual_order_probe_cases(today_text: str) -> tuple[EmployeeAgentProbeCase, ...]:
    return (
        EmployeeAgentProbeCase(
            "today-action-items",
            "今天有什么要盯的",
            "order_query",
            ("order_dynamic_query",),
            "action_items",
            today_text,
            today_text,
            expected_keyword="",
            required_any_terms=("待处理", "履约", "退款", "物流", "单"),
            forbidden_terms=("完整订单号", "手机号", "完整地址"),
        ),
        EmployeeAgentProbeCase(
            "casual-order-attention",
            "今天订单有没有需要注意的",
            "order_query",
            ("order_dynamic_query",),
            "action_items",
            today_text,
            today_text,
            expected_keyword="",
            required_any_terms=("待处理", "履约", "退款", "物流", "单"),
            forbidden_terms=("完整订单号", "手机号", "完整地址"),
        ),
        EmployeeAgentProbeCase(
            "refund-order-customer-reply",
            "今天有退款订单，怎么回复客户",
            "multi_tool",
            ("order_dynamic_query", "knowledge_answer"),
            "summary",
            today_text,
            today_text,
            expected_keyword="",
            expected_needs_refund=True,
            required_any_terms=("退款", "售后", "回复", "客户", "单"),
            forbidden_terms=("完整订单号", "手机号", "完整地址"),
        ),
        EmployeeAgentProbeCase(
            "casual-today-orders",
            "今天单量咋样",
            "order_query",
            ("order_dynamic_query",),
            "summary",
            today_text,
            today_text,
            expected_keyword="",
            required_any_terms=("单",),
            forbidden_terms=("完整订单号", "手机号"),
        ),
        EmployeeAgentProbeCase(
            "casual-pending-shipment",
            "发货还有没处理的吗",
            "order_query",
            ("order_dynamic_query",),
            "list",
            expected_statuses=("WAIT_SELLER_SEND_GOODS",),
            expected_keyword="",
            required_any_terms=("待发货", "未发货", "发货"),
            forbidden_terms=("完整订单号", "手机号"),
        ),
        EmployeeAgentProbeCase(
            "casual-fulfillment-pressure",
            "今天发货压力大不大",
            "order_query",
            ("order_dynamic_query",),
            "list",
            today_text,
            today_text,
            expected_statuses=("WAIT_SELLER_SEND_GOODS", "WAIT_BUYER_CONFIRM_GOODS"),
            expected_keyword="",
            expected_fulfillment_risk=True,
            required_any_terms=("发货", "压力", "约送", "待发货", "待收货"),
            forbidden_terms=("完整订单号", "手机号", "完整地址"),
        ),
        EmployeeAgentProbeCase(
            "casual-missing-logistics",
            "哪些单子还没出物流",
            "order_query",
            ("order_dynamic_query",),
            "list",
            expected_missing_logistics=True,
            expected_keyword="",
            required_any_terms=("物流",),
            forbidden_terms=("完整订单号", "手机号"),
        ),
        EmployeeAgentProbeCase(
            "casual-top-product",
            "今天卖爆的是哪个",
            "order_query",
            ("order_dynamic_query",),
            "top_products",
            today_text,
            today_text,
            expected_keyword="",
            required_any_terms=("销量", "卖", "爆款"),
            forbidden_terms=("完整订单号", "手机号"),
        ),
    )


def _casual_support_probe_cases() -> tuple[EmployeeAgentProbeCase, ...]:
    return (
        EmployeeAgentProbeCase(
            "casual-product-stock",
            "帮我看看伯牙绝弦库存",
            "product_query",
            ("product_lookup",),
            required_all_terms=("库存", "72"),
            forbidden_terms=(
                "完整订单号",
                "手机号",
                "未匹配到商品",
                "未在系统匹配",
                "未找到匹配商品",
            ),
        ),
        EmployeeAgentProbeCase(
            "casual-ops-status",
            "后台现在稳不稳",
            "ops_query",
            ("ops_summary",),
            required_any_terms=("系统", "观察台", "状态"),
            forbidden_terms=("完整订单号", "手机号"),
        ),
        EmployeeAgentProbeCase(
            "casual-handoff-pending",
            "有没有需要人接的",
            "ops_query",
            ("handoff_pending",),
            required_any_terms=("待人工", "转人工"),
            forbidden_terms=("买家", "ID:", "user"),
        ),
    )


def _weekend_text_range(today: date) -> tuple[str, str]:
    week_start = date.fromordinal(today.toordinal() - today.weekday())
    weekend_start = date.fromordinal(week_start.toordinal() + 5)
    weekend_end = date.fromordinal(week_start.toordinal() + 6)
    if today > weekend_end:
        weekend_start = date.fromordinal(weekend_start.toordinal() + 7)
        weekend_end = date.fromordinal(weekend_end.toordinal() + 7)
    return weekend_start.isoformat(), weekend_end.isoformat()
