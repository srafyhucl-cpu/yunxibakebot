from app.service.wecom.intelligent_bot_ops_format import (
    compact_transfer,
    ops_summary_line,
    transfer_line,
)


class _Transfer:
    id = "da8f723e-d755-4868-8c48-bf9813a77f40"
    session_id = "sess_001"
    user_id = "user_001"
    reason = "客户要求人工确认配送"
    conversation_summary = "客户 13812345678 问配送到隐私路 99 号的时间。"
    created_at = "2026-07-04 09:00:00"


def test_ops_summary_line_uses_staff_readable_status() -> None:
    reply = ops_summary_line(
        {
            "status": "attention",
            "counts": {
                "content_change_failures": 1,
                "webhook_failures": 2,
                "webhook_processing": 0,
                "slow_webhooks": 1,
            },
        }
    )

    assert "系统需要关注" in reply
    assert "Webhook 失败 2 条" in reply
    assert "先看 Webhook 失败记录" in reply
    assert "attention" not in reply


def test_transfer_line_includes_safe_summary_preview() -> None:
    item = compact_transfer(_Transfer())
    reply = transfer_line(item)

    assert "工单尾号 77f40" in reply
    assert "客户要求人工确认配送" in reply
    assert "摘要：" in reply
    assert "13812345678" not in reply
    assert "隐私路 99 号" not in reply
    assert "user_001" not in reply
