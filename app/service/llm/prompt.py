"""
系统提示词构建。

根据当前时间、知识库内容、渠道信息动态生成 System Prompt。
"""

from datetime import datetime, timezone

from app.models.knowledge import KnowledgeEntry

# System Prompt 模板，{knowledge} 和 {current_time} 在运行时替换
SYSTEM_PROMPT_TPL = """你是芸熙烘焙的智能客服机器人，负责回答顾客关于产品、订单、配送、售后等问题。

## 行为准则
- 友好、热情、专业，使用亲切的语气
- 绝不编造订单信息，如果查不到就如实告知
- 对于无法解决的问题，主动引导用户转人工客服
- 回复简洁明了，避免冗长
- 如果顾客表达不满或投诉，先道歉再解决问题

## 店铺知识
{knowledge}

## 当前时间
{current_time}

如果有需要，可以通过提供的工具查询订单、商品信息或转接人工客服。
"""


def build_system_prompt(knowledge_entries: list[KnowledgeEntry] | None = None) -> str:
    """
    构建 System Prompt。

    参数：
        knowledge_entries: 当前对话相关的知识条目（top-5）
    返回：
        完整 System Prompt 字符串
    """
    now = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    knowledge_text = "\n".join(
        f"- [{e.category}] {e.title}: {e.content}" for e in (knowledge_entries or [])
    ) or "（暂无）"
    return SYSTEM_PROMPT_TPL.format(knowledge=knowledge_text, current_time=now)
