from app.service.wecom.intelligent_bot_ops_format import short_identifier, transfer_line
from app.service.wecom.intelligent_bot_order_format import (
    build_order_action_items_tool_result,
    build_order_list_tool_result,
    build_order_summary_tool_result,
    employee_order_line,
)


def test_order_agent_next_action_only_mentions_tail_or_backend() -> None:
    summary_result = build_order_summary_tool_result("今天一共多少订单", {}, [])
    list_result = build_order_list_tool_result(
        "还有哪些没发货",
        {},
        [
            {
                "order_no": "E202607031234567890",
                "status": "WAIT_SELLER_SEND_GOODS",
                "product_titles": "伯牙绝弦 x1",
                "amount_fen": 25800,
            }
        ],
    )

    combined_text = "\n".join(
        [summary_result.next_action, list_result.summary, list_result.next_action]
    )

    assert "完整订单号" not in combined_text
    assert "E202607031234567890" not in combined_text
    assert "订单尾号" in combined_text or "尾号" in combined_text


def test_transfer_line_does_not_expose_user_identifier() -> None:
    line = transfer_line(
        {
            "id": "da8f723e-d755-4868-8c48-bf9813a77f40",
            "userRef": "wmLg...ismA",
            "reason": "客户要求人工",
        }
    )

    assert "wmLg" not in line
    assert "ID:" not in line
    assert "da8f723e-d755-4868-8c48-bf9813a77f40" not in line
    assert line == "工单尾号 77f40｜客户要求人工"


def test_short_identifier_keeps_only_suffix() -> None:
    assert short_identifier("da8f723e-d755-4868-8c48-bf9813a77f40") == "77f40"
    assert short_identifier("") == "***"


def test_employee_order_line_marks_refund_without_full_order_no() -> None:
    line = employee_order_line(
        1,
        {
            "order_no": "E202607031234567890",
            "status": "TRADE_CLOSED",
            "product_titles": "售后退款蛋糕 x1",
            "amount_fen": 8800,
            "refund_state": 1,
            "pay_time": "2026-07-03 12:00:00",
        },
    )

    assert "有退款/售后" in line
    assert "E202607031234567890" not in line
    assert "567890" in line


def test_employee_order_line_shows_delivery_time_without_private_fields() -> None:
    line = employee_order_line(
        1,
        {
            "order_no": "E202607031234567891",
            "status": "WAIT_SELLER_SEND_GOODS",
            "product_titles": "快超时蛋糕 x1",
            "amount_fen": 16800,
            "pay_time": "2026-07-03 10:00:00",
            "delivery_time": "2026-07-03 18:00",
        },
    )

    assert "约送 2026-07-03 18:00" in line
    assert "E202607031234567891" not in line
    assert "567891" in line


def test_order_action_items_does_not_expose_private_fields() -> None:
    result = build_order_action_items_tool_result(
        "今天有什么要盯的",
        {"total_count": 1, "total_amount_fen": 16800},
        {"total_count": 1},
        [
            {
                "order_no": "E202607031234567892",
                "status": "WAIT_SELLER_SEND_GOODS",
                "product_titles": "快超时蛋糕 x1",
                "amount_fen": 16800,
                "delivery_time": "2026-07-03 18:00",
                "buyer_id": "buyer_13812345678",
                "delivery_district": "朝阳区",
            }
        ],
        [],
        {"total_count": 0},
        [],
    )

    assert "E202607031234567892" not in result.summary
    assert "567892" in result.summary
    assert "13812345678" not in result.summary
    assert "朝阳区" not in result.summary
