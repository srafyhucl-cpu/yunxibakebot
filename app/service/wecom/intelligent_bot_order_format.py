"""企微智能机器人订单展示格式。"""

from __future__ import annotations

import re
from typing import Any

from app.models.employee_agent import ToolResult

ORDER_STATUS_LABELS = {
    "WAIT_BUYER_PAY": "待付款",
    "WAIT_SELLER_SEND_GOODS": "待发货",
    "WAIT_BUYER_CONFIRM_GOODS": "待收货",
    "TRADE_SUCCESS": "交易成功",
    "TRADE_CLOSED": "已关闭",
    "TRADE_PAID": "已付款",
}


def build_order_summary_tool_result(
    query: str,
    summary: dict[str, Any],
    orders: list[dict[str, Any]],
) -> ToolResult:
    """构造员工可读订单统计结果。"""
    total_count = int(summary.get("total_count", 0) or 0)
    total_amount_yuan = int(summary.get("total_amount_fen", 0) or 0) / 100
    status_text = status_counts_text(summary.get("status_counts", {}))
    recent_lines = [
        employee_order_line(index, order) for index, order in enumerate(orders, 1)
    ]
    lines = [
        f"{query}：共 {total_count} 单，合计 {total_amount_yuan:.2f} 元。",
        status_text,
    ]
    if recent_lines:
        lines.append("最近相关订单：")
        lines.extend(recent_lines)
    return ToolResult(
        ok=True,
        summary="\n".join(line for line in lines if line),
        items=[compact_employee_order(order) for order in orders],
        metrics=summary,
        next_action="如需看某一单详情，请带订单尾号追问，或进入后台订单页核对。",
    )


def build_order_list_tool_result(
    query: str,
    summary: dict[str, Any],
    orders: list[dict[str, Any]],
) -> ToolResult:
    """构造员工可读订单列表结果。"""
    if not orders:
        return ToolResult(
            ok=True,
            summary=f"{query}：没有查到匹配订单。",
            metrics=summary,
            next_action="可以换商品名、状态或时间范围再问。",
        )
    lines = [f"{query}：找到 {len(orders)} 单，按最新订单展示："]
    lines.extend(
        employee_order_line(index, order) for index, order in enumerate(orders, 1)
    )
    return ToolResult(
        ok=True,
        summary="\n".join(lines),
        items=[compact_employee_order(order) for order in orders],
        metrics=summary,
        next_action="列表默认只展示订单尾号，排查时可用尾号继续追问。",
    )


def build_top_products_tool_result(
    query: str,
    rows: list[dict[str, Any]],
) -> ToolResult:
    """构造商品销量排行结果。"""
    if not rows:
        return ToolResult(ok=True, summary=f"{query}：没有查到匹配商品订单。")
    lines = [f"{query}：按销量粗略排行如下："]
    for index, row in enumerate(rows, 1):
        amount_yuan = int(row.get("total_amount_fen", 0) or 0) / 100
        lines.append(
            f"{index}. {row.get('product_titles') or '未记录商品'}："
            f"{int(row.get('total_quantity', 0) or 0)} 件，"
            f"{int(row.get('order_count', 0) or 0)} 单，{amount_yuan:.2f} 元"
        )
    return ToolResult(ok=True, summary="\n".join(lines), items=rows)


def status_counts_text(status_counts: Any) -> str:
    """格式化订单状态分布。"""
    if not isinstance(status_counts, dict) or not status_counts:
        return ""
    parts = [
        f"{ORDER_STATUS_LABELS.get(status, status)} {count} 单"
        for status, count in status_counts.items()
    ]
    return "状态分布：" + "，".join(parts) + "。"


def employee_order_line(index: int, order: dict[str, Any]) -> str:
    """格式化员工列表中的单行订单。"""
    amount_yuan = int(order.get("amount_fen", 0) or 0) / 100
    order_tail = order_tail_text(str(order.get("order_no", "")))
    status_label = ORDER_STATUS_LABELS.get(
        str(order.get("status", "")), str(order.get("status", ""))
    )
    pay_time = str(order.get("pay_time") or order.get("created_at") or "未记录时间")
    logistics_text = employee_logistics_text(order)
    refund_text = employee_refund_text(order)
    product_titles = str(order.get("product_titles") or "未记录商品")
    return (
        f"{index}. 尾号 {order_tail}｜{status_label}｜{product_titles}｜"
        f"{amount_yuan:.2f} 元｜{pay_time}｜{logistics_text}{refund_text}"
    )


def compact_employee_order(order: dict[str, Any]) -> dict[str, Any]:
    """压缩订单字段，避免暴露完整订单和隐私字段。"""
    return {
        "orderTail": order_tail_text(str(order.get("order_no", ""))),
        "status": ORDER_STATUS_LABELS.get(
            str(order.get("status", "")), str(order.get("status", ""))
        ),
        "productTitles": str(order.get("product_titles", "")),
        "amountFen": int(order.get("amount_fen", 0) or 0),
        "payTime": str(order.get("pay_time") or order.get("created_at") or ""),
        "logisticsStatus": employee_logistics_text(order),
        "refundStatus": employee_refund_text(order).lstrip("｜"),
    }


def order_tail_text(order_no: str) -> str:
    """只展示订单尾号。"""
    return order_no[-6:] if len(order_no) > 6 else order_no


def employee_logistics_text(order: dict[str, Any]) -> str:
    """格式化员工可读物流状态。"""
    logistics_status = str(order.get("logistics_status") or "")
    logistics_no = str(order.get("logistics_no") or "")
    if logistics_status:
        return logistics_status
    if logistics_no:
        return "有物流单号"
    return "暂无物流"


def employee_refund_text(order: dict[str, Any]) -> str:
    """格式化员工可读退款标记。"""
    try:
        refund_state = int(order.get("refund_state", 0) or 0)
    except (TypeError, ValueError):
        refund_state = 0
    return "｜有退款/售后" if refund_state else ""


def youzan_order_line(order: dict[str, Any]) -> str:
    """格式化有赞订单搜索结果。"""
    amount_yuan = order["amountFen"] / 100
    quantity = order.get("totalQuantity", 0)
    quantity_text = (
        f" x {quantity}"
        if quantity and not product_title_has_quantity(order["productTitles"])
        else ""
    )
    logistics_text = (
        order.get("logisticsStatus") or order.get("logisticsNo") or "暂无物流"
    )
    return (
        f"{order['orderNo']}｜{order['status']}｜{order['productTitles']}{quantity_text}｜"
        f"{amount_yuan:.2f}元｜{order.get('payTime') or '未记录付款时间'}｜{logistics_text}"
    )


def youzan_order_detail_line(order: dict[str, Any]) -> str:
    """格式化有赞订单详情。"""
    amount_yuan = order["amountFen"] / 100
    logistics_text = (
        order.get("logisticsStatus") or order.get("logisticsNo") or "暂无物流"
    )
    message = order.get("message")
    if message and not order.get("productTitles"):
        if logistics_text != "暂无物流":
            return f"{order['orderNo']}｜{logistics_text}"
        return f"{order['orderNo']}｜{message}"
    return (
        f"{order['orderNo']}｜{order['status']}｜{order.get('productTitles', '')}｜"
        f"{amount_yuan:.2f}元｜配送 {order.get('deliveryArea') or '未记录'}｜{logistics_text}"
    )


def product_title_has_quantity(product_titles: str) -> bool:
    """判断商品标题是否已经包含数量。"""
    return bool(re.search(r"(?:x|×)\s*\d+", product_titles, re.IGNORECASE))
