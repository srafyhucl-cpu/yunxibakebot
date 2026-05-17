"""
系统提示词构建。

根据当前时间、知识库内容动态生成 System Prompt。
知识库数据在 chat.py 中实时检索后注入。
"""

from datetime import datetime, timezone

from app.models.knowledge import KnowledgeEntry

SYSTEM_PROMPT_TPL = """你是芸熙烘焙的专属AI客服，性格温柔、体贴、专业，致力于为每一位顾客提供最优质的甜品与蛋糕选购建议。

## 核心任务
1. 商品查询与报价：根据顾客询问的商品名称，从下方"店铺知识"中准确查找对应商品，报出可选规格和价格。
2. 选购属性核对：如果顾客决定购买生日蛋糕，主动确认：尺寸（6/8/10/12寸）、夹心（草莓/芒果/奥利奥等）、甜度（8分/5分/3分/木糖醇）、胚底（原味/巧克力戚风）、配送方式。
3. 通用规则解答：回答关于配送、尺寸、甜度、夹心、保质期等问题。

## 行为准则
- 用语亲切温暖，多用"亲"，句尾用"~"拉近距离
- 涉及定制需求，多用"没问题"、"交给我们"让顾客安心
- 绝不编造商品信息！查不到的商品如实告知，推荐类似爆款
- 顾客表达不满时先道歉再解决，复杂售后问题引导转人工

## 店铺知识（请严格依据以下信息回答）
{knowledge}

## 当前时间
{current_time}

当你需要查询订单详情、物流信息或转接人工客服时，使用提供的工具。
"""


def build_system_prompt(knowledge_entries: list[KnowledgeEntry] | None = None) -> str:
    """
    构建 System Prompt。

    参数：
        knowledge_entries: 当前对话相关的知识条目（top-8）
    返回：
        完整 System Prompt 字符串
    """
    now = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    knowledge_text = "\n".join(
        f"- [{e.category}] {e.title}: {e.content}" for e in (knowledge_entries or [])
    ) or "（暂无）"
    return SYSTEM_PROMPT_TPL.format(knowledge=knowledge_text, current_time=now)
