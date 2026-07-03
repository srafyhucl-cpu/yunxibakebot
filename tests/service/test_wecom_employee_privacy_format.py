from app.service.wecom.intelligent_bot_ops_format import short_identifier, transfer_line
from app.service.wecom.intelligent_bot_order_format import (
    build_order_list_tool_result,
    build_order_summary_tool_result,
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
