"""意图识别测试。"""

import pytest

from app.exceptions import LLMError
from app.service.llm import intent as intent_module


@pytest.mark.parametrize(
    ("query", "expected_intent"),
    [
        ("提拉米苏多少钱", intent_module.IntentType.PRODUCT_CONSULTATION),
        ("可以开发票吗", intent_module.IntentType.STORE_POLICY),
        ("运费多少钱", intent_module.IntentType.SHIPPING_FEE),
        ("明天下午能送到吗", intent_module.IntentType.DELIVERY_SCHEDULE),
        ("给我开发票", intent_module.IntentType.ORDER_SERVICE),
        ("帮我改一下配送地址", intent_module.IntentType.ORDER_SERVICE),
        ("蛋糕塌了我要退款", intent_module.IntentType.AFTER_SALES_ISSUE),
        ("转人工", intent_module.IntentType.HUMAN_ASSISTANCE),
        ("你好呀", intent_module.IntentType.SMALL_TALK),
    ],
)
def test_match_clear_intent(query: str, expected_intent: intent_module.IntentType) -> None:
    assert intent_module._match_clear_intent(query) == expected_intent


@pytest.mark.asyncio
async def test_detect_intent_uses_llm_for_ambiguous_query(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_llm(*args: object, **kwargs: object) -> str:
        return '{"choices":[{"message":{"content":"2"}}]}'

    monkeypatch.setattr(intent_module, "llm_chat", _fake_llm)

    intent = await intent_module.detect_intent("开发票")

    assert intent == intent_module.IntentType.STORE_POLICY


@pytest.mark.asyncio
async def test_detect_intent_falls_back_when_llm_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _raise_llm_error(*args: object, **kwargs: object) -> str:
        raise LLMError("boom")

    monkeypatch.setattr(intent_module, "llm_chat", _raise_llm_error)

    intent = await intent_module.detect_intent("这个呢")

    assert intent == intent_module.IntentType.PRODUCT_CONSULTATION
