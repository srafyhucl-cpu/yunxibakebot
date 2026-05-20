"""意图识别服务。"""

import json

from app.exceptions import LLMError
from app.logger import setup_logger
from app.service.llm.client import chat_completion as llm_chat
from app.service.llm.intent_taxonomy import AFTER_SALES_KEYWORDS
from app.service.llm.intent_taxonomy import DELIVERY_SCHEDULE_KEYWORDS
from app.service.llm.intent_taxonomy import HUMAN_ASSISTANCE_KEYWORDS
from app.service.llm.intent_taxonomy import INTENT_ID_CHARACTERS
from app.service.llm.intent_taxonomy import INTENT_PROMPT
from app.service.llm.intent_taxonomy import ORDER_ACTION_KEYWORDS
from app.service.llm.intent_taxonomy import ORDER_CONTEXT_KEYWORDS
from app.service.llm.intent_taxonomy import ORDER_SERVICE_TOPIC_KEYWORDS
from app.service.llm.intent_taxonomy import PRODUCT_KEYWORDS
from app.service.llm.intent_taxonomy import QUESTION_KEYWORDS
from app.service.llm.intent_taxonomy import SHIPPING_FEE_KEYWORDS
from app.service.llm.intent_taxonomy import SMALL_TALK_KEYWORDS
from app.service.llm.intent_taxonomy import STORE_POLICY_KEYWORDS
from app.service.llm.intent_types import IntentType

logger = setup_logger()


def _contains_any(user_query: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in user_query for keyword in keywords)


def _looks_like_question(user_query: str) -> bool:
    return _contains_any(user_query, QUESTION_KEYWORDS)


def _match_clear_intent(user_query: str) -> IntentType | None:
    has_question_signal = _looks_like_question(user_query)
    if _contains_any(user_query, HUMAN_ASSISTANCE_KEYWORDS):
        return IntentType.HUMAN_ASSISTANCE
    if _contains_any(user_query, AFTER_SALES_KEYWORDS):
        return IntentType.AFTER_SALES_ISSUE
    has_order_action = _contains_any(user_query, ORDER_ACTION_KEYWORDS)
    has_order_context = _contains_any(user_query, ORDER_CONTEXT_KEYWORDS)
    has_order_topic = _contains_any(user_query, ORDER_SERVICE_TOPIC_KEYWORDS)
    if has_order_topic and (has_order_action or (has_order_context and not has_question_signal)):
        return IntentType.ORDER_SERVICE
    if _contains_any(user_query, SMALL_TALK_KEYWORDS) and len(user_query) <= 12 and not has_question_signal:
        return IntentType.SMALL_TALK
    if not has_question_signal:
        return None
    if _contains_any(user_query, SHIPPING_FEE_KEYWORDS):
        return IntentType.SHIPPING_FEE
    if _contains_any(user_query, DELIVERY_SCHEDULE_KEYWORDS):
        return IntentType.DELIVERY_SCHEDULE
    if _contains_any(user_query, STORE_POLICY_KEYWORDS):
        return IntentType.STORE_POLICY
    if _contains_any(user_query, PRODUCT_KEYWORDS):
        return IntentType.PRODUCT_CONSULTATION
    return None


def _extract_intent(raw_content: str) -> IntentType:
    try:
        # 清理可能包含的 Markdown json 包裹标记
        cleaned_content = raw_content.strip()
        if cleaned_content.startswith("```json"):
            cleaned_content = cleaned_content.removeprefix("```json")
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content.removesuffix("```")
        cleaned_content = cleaned_content.strip()

        data = json.loads(cleaned_content)
        if isinstance(data, int):
            primary = data
            secondaries = []
        elif isinstance(data, dict):
            primary = int(data.get("primary_intent", 1))
            secondaries = [int(i) for i in data.get("secondary_intents", [])]
        else:
            raise TypeError("Expected dict or int")

        all_intents = [primary] + secondaries

        # 优先级晋升：人工服务 (7) > 售后异常 (6) > 订单办理 (5)
        if 7 in all_intents:
            return IntentType.HUMAN_ASSISTANCE
        if 6 in all_intents:
            return IntentType.AFTER_SALES_ISSUE
        if 5 in all_intents:
            return IntentType.ORDER_SERVICE

        # 兜底返回主意图
        if primary in (1, 2, 3, 4, 8):
            return IntentType(primary)
        return IntentType.PRODUCT_CONSULTATION
    except (json.JSONDecodeError, ValueError, TypeError, KeyError):
        # 兜底：如果 JSON 无法解析，回退到数字提取
        for character in raw_content:
            if character in INTENT_ID_CHARACTERS:
                val = int(character)
                # 优先级判定
                if val in (5, 6, 7):
                    if val == 7:
                        return IntentType.HUMAN_ASSISTANCE
                    if val == 6:
                        return IntentType.AFTER_SALES_ISSUE
                    return IntentType.ORDER_SERVICE
                return IntentType(val)
        return IntentType.PRODUCT_CONSULTATION


async def detect_intent(user_query: str, history: str = "") -> IntentType:
    normalized_query = "".join(user_query.split())
    # 1. 过滤极端噪声（空白、纯标点、纯 emoji 符号）
    if not normalized_query or not any(char.isalnum() for char in normalized_query):
        return IntentType.SMALL_TALK

    # 2. 0 成本强动作拦截 (最前端直接 Return 拦截，不准引发任何后续的大模型接口请求)
    if _contains_any(normalized_query, HUMAN_ASSISTANCE_KEYWORDS):
        logger.debug("转人工强动作拦截命中: \"%s\" -> HUMAN_ASSISTANCE", normalized_query[:30])
        return IntentType.HUMAN_ASSISTANCE

    # 3. 其它明确规则的前置判定
    matched_intent = _match_clear_intent(normalized_query)
    if matched_intent is not None:
        logger.debug("意图识别前置命中: \"%s\" -> %s", normalized_query[:30], matched_intent.name)
        return matched_intent

    # 4. 大模型多标签打标与 Token 溢出防线
    prompt = INTENT_PROMPT.format(history=history or "无", user_query=normalized_query)
    try:
        raw_response = await llm_chat(
            [{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=32,  # 放宽 Token 约束到 32
        )
        response = json.loads(raw_response)
        raw_content = response["choices"][0]["message"].get("content", "1").strip()
        intent = _extract_intent(raw_content)
        logger.debug("意图识别: \"%s\" -> %s", normalized_query[:30], intent.name)
        return intent
    except (LLMError, KeyError, IndexError, json.JSONDecodeError) as exc:
        logger.warning("意图识别失败，默认返回 PRODUCT_CONSULTATION: %s", exc)
        return IntentType.PRODUCT_CONSULTATION
