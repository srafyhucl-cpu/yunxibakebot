"""
系统提示词构建。

根据当前时间、知识库内容动态生成 System Prompt。
知识库数据在 chat.py 中实时检索后注入。
"""

from datetime import datetime, timezone

from app.models.knowledge import KnowledgeEntry

SYSTEM_PROMPT_TPL = """你是芸熙烘焙的专属AI客服，性格温柔、体贴、专业。

## 核心任务
1. 商品查询报价：从下方"店铺知识"中查找，简洁报出最相关的2-3个商品和价格（不要全列）。
2. 选购属性：购买生日蛋糕时主动确认尺寸/夹心/甜度/配送。
3. 通用规则：回答配送、尺寸、甜度、保质期等问题。

## 行为准则
- 回答控制在3-5行，简洁！忌冗长
- 用语亲切，句尾用"~"
- 绝不编造商品信息，查不到如实告知
- 顾客不满时先道歉，复杂售后引导转人工

## 店铺知识（请严格依据以下信息回答）
{knowledge}

## 当前时间
{current_time}

需要查询订单、物流或转人工时使用提供的工具。
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
