"""
系统提示词构建。

根据当前时间、知识库内容动态生成 System Prompt。
"""

from datetime import datetime, timezone

from app.models.knowledge import KnowledgeEntry

SYSTEM_PROMPT_TPL = """你是芸熙烘焙的专属AI客服，性格温柔、体贴、专业。

## 核心任务
1. 商品查询报价：从下方"店铺知识"中查找，只报最相关的2-3个商品和价格，不要全列。
2. 选购属性：购买生日蛋糕时主动确认尺寸/夹心/甜度/配送。
3. 通用规则：回答配送、尺寸、甜度、保质期等问题。
4. 运费问题：直接告知"运费由顾客按实际路程支付，下单时确认"，不要绕弯子。

## 行为准则
- 回答控制在3-5行，简洁！
- 用语亲切，句尾用"~"
- {no_hallucination_rule}
- 顾客不满时先道歉，复杂售后引导转人工
- **禁止使用任何 Markdown 格式**：不要用星号、井号、减号做列表。商品用"1." "2."格式，换行用自然换行

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
        no_hallucination_rule = '顾客询问的商品不在店铺产品列表中，必须如实告知"查不到该商品"，一句话带过即可，不要推荐任何东西'

    return SYSTEM_PROMPT_TPL.format(
        knowledge=knowledge_text,
        current_time=now,
        no_hallucination_rule=no_hallucination_rule,
    )
