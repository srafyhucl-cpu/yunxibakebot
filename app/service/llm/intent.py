"""
意图识别服务。

根据用户输入 + 对话历史，识别顾客意图并返回数字标记：
1=商品查价与咨询, 2=运费查询, 3=配送时间咨询, 4=售后与转人工, 5=日常闲聊与其他
"""

from enum import IntEnum

from openai import AsyncOpenAI

from app.config import settings
from app.logger import setup_logger


class IntentType(IntEnum):
    """意图分类 ID：所有合法意图值的唯一来源"""
    PRODUCT_INQUIRY = 1    # 商品查价与咨询
    SHIPPING_COST = 2      # 运费查询
    DELIVERY_TIME = 3      # 配送时间咨询
    AFTER_SALES = 4        # 售后与转人工
    CASUAL_CHAT = 5        # 日常闲聊与其他

logger = setup_logger()

INTENT_PROMPT = """### 角色
你是一位杰出的意图识别专家，服务于「芸熙烘焙」的 AI 客服系统，具备极为敏锐的洞察力，能够迅速且精准地判断顾客问题的意图类型。

### 技能：精准识别用户意图
依据以下意图列表，仅返回与之对应的数字序号。

| 序号 | 意图 | 描述 |
| :--: | :--- | :--- |
| 1 | 商品查价与咨询 | 询问蛋糕款式、价格、尺寸、口味、推荐、定制、下单、购买，以及积分、优惠券、兑换、会员、店铺规则等通用咨询 |
| 2 | 运费查询 | 询问运费、邮费、配送费、谁出运费等 |
| 3 | 配送时间咨询 | 询问配送时间、送达时间、营业时间、门店地址、预定时间等 |
| 4 | 售后与转人工 | 客诉、催单、修改订单、复杂定制、要求转人工等 |
| 5 | 日常闲聊与其他 | 问候、无关闲聊、或难以理解的输入 |

优先级权重：4 > 1 > 2 > 3 > 5

### 历史使用规则
- 当前用户输入优先级最高，历史记录只用于补全省略信息，不得机械继承上一轮意图。
- 如果历史里出现过售后、投诉、转人工，但当前输入是一个完整明确的新问题（如积分怎么用、优惠券怎么兑换、甜度能选吗），必须按当前输入重新分类，不能继续判为 4。
- 只有当前输入本身明确表达不满、售后、催单、退款、修改订单、要求人工时，才能判为 4。

### 回复格式
仅回复数字：1、2、3、4 或 5。不附带任何解释文字。

历史记录：
{history}
当前用户输入：{user_query}
"""


async def detect_intent(user_query: str, history: str = "") -> IntentType:
    """
    识别用户意图。

    返回：IntentType 枚举值，失败时默认返回 PRODUCT_INQUIRY
    """
    if not user_query.strip():
        return IntentType.CASUAL_CHAT

    client = AsyncOpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )

    prompt = INTENT_PROMPT.format(
        history=history or "无",
        user_query=user_query,
    )

    try:
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4,
        )
        raw = (response.choices[0].message.content or "1").strip()
        # 提取第一个数字
        for ch in raw:
            if ch in "12345":
                intent = IntentType(int(ch))
                logger.debug("意图识别: '%s' -> %s", user_query[:30], intent.name)
                return intent
        return IntentType.PRODUCT_INQUIRY
    except Exception as exc:
        logger.warning("意图识别失败，默认返回 PRODUCT_INQUIRY: %s", exc)
        return IntentType.PRODUCT_INQUIRY
