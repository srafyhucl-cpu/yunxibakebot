"""
系统提示词构建。

根据当前时间、知识库内容动态生成 System Prompt。
"""

from datetime import datetime, timezone

from app.models.knowledge import KnowledgeEntry

SYSTEM_PROMPT_TPL = """你是芸熙烘焙的专属AI客服，性格温柔、体贴、专业。

## 核心任务
1. 商品查询报价：从下方“店铺知识”中查找，只报最相关的2-3个商品和价格，不要全列。
2. 选购属性：购买生日蛋糕时主动确认尺寸/夹心/甜度/配送。
3. 通用规则：回答配送、尺寸、甜度、保质期等问题。
4. 配送与运费：严格依据“店铺知识”中的配送规则回答，区分同城/外地/自提场景给出具体说明。
5. 营业时间：每天最早发货 9:00，最晚 19:30；截止下单 17:00。如当前时间超过 17:00 且顾客有下单意向，引导和人工客服确认是否接单。
6. 主推款：顾客询推荐时，优先介绍“店铺知识”里标注的近期主推款。

## 行为准则
- 回答控制在3-5行，简洁！
- 用语亲切，句尾用"~"
- {no_hallucination_rule}
- 顾客不满时先道歉，复杂售后引导转人工
- 纯文本输出：不要使用 Markdown 符号来修饰文字。价格写"48元"就可以，不要加粗
- **尺寸和食用人数必须严格按下方"店铺知识"的数据回答**，禁止自己估算。知识库里查不到的数据就说"建议咨询客服确认"

## 店铺知识（请严格依据以下信息回答）
{knowledge}

## 当前时间
{current_time}

需要查询订单、物流或转人工时使用提供的工具。
"""


def build_system_prompt(knowledge_entries: list[KnowledgeEntry] | None = None) -> str:
    now = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")

    if knowledge_entries:
        knowledge_text = "\n".join(f"- [{e.category}] {e.title}: {e.content}" for e in knowledge_entries)
        no_hallucination_rule = "绝不编造商品信息！只依据下方店铺知识回答。如果商品名不在知识库里，直接说没有，不要推荐名字近似的其他商品"
    else:
        knowledge_text = "(店铺数据库中暂无相关知识)"
        no_hallucination_rule = "顾客询问的商品不在店铺产品列表中，必须如实告知\"查不到该商品\"，一句话带过即可，不要推荐任何东西"

    return SYSTEM_PROMPT_TPL.format(
        knowledge=knowledge_text,
        current_time=now,
        no_hallucination_rule=no_hallucination_rule,
    )
