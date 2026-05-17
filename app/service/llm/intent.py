"""
意图识别服务。

根据用户输入 + 对话历史，识别顾客意图并返回数字标记：
1=商品查价与咨询, 2=规则与物流咨询, 3=售后与转人工, 4=日常闲聊
"""

from openai import AsyncOpenAI

from app.config import settings
from app.logger import setup_logger

logger = setup_logger()

INTENT_PROMPT = """### 角色
你是一位杰出的意图识别专家，服务于「芸熙烘焙」的 AI 客服系统，具备极为敏锐的洞察力，能够迅速且精准地判断顾客问题的意图类型。

### 技能：精准识别用户意图
依据以下意图列表，仅返回与之对应的数字序号。

| 序号 | 意图 | 描述 |
| :--: | :--- | :--- |
| 1 | 商品查价与咨询 | 询问蛋糕款式、价格、尺寸、口味、推荐、定制等 |
| 2 | 规则与物流咨询 | 预定时间、配送、运费、门店地址、营业时间等 |
| 3 | 售后与转人工 | 客诉、催单、修改订单、复杂定制、要求转人工等 |
| 4 | 日常闲聊与其他 | 问候、无关闲聊、或难以理解的输入 |

优先级权重：3 > 1 > 2 > 4

### 回复格式
仅回复数字：1、2、3 或 4。不附带任何解释文字。

历史记录：
{history}
当前用户输入：{user_query}
"""


async def detect_intent(user_query: str, history: str = "") -> int:
    """
    识别用户意图。

    返回：1-4 的数字标记，失败时默认返回 1
    """
    if not user_query.strip():
        return 4

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
            if ch in "1234":
                intent = int(ch)
                logger.debug("意图识别: '%s' -> %d", user_query[:30], intent)
                return intent
        return 1
    except Exception as exc:
        logger.debug("意图识别失败，默认返回 1: %s", exc)
        return 1
