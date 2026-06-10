from app.service.chat_transfer import build_transfer_summary


def test_build_transfer_summary_returns_decision_note_for_elder_case() -> None:
    history = "\n".join(
        [
            "用户：给老人买个木糖醇的蛋糕",
            "AI：推荐星星人奶油蛋糕",
            "用户：10个人吃推荐一个",
            "AI：星星人支持10寸",
            "用户：星星人也不适合老人啊",
        ]
    )

    note = build_transfer_summary("转人工", history)

    assert "客户诉求：给老人/长辈选蛋糕" in note
    assert "偏木糖醇/低糖" in note
    assert "当前卡点：客户已表达推荐不认可" in note
    assert "优先推荐祝寿/稳重/寓意明确款" in note
    assert "AI：推荐星星人" not in note
