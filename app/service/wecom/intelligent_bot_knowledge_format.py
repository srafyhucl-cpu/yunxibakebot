"""企微智能机器人知识库展示格式。"""

from typing import Any

from app.service.wecom.intelligent_bot_tool_format import knowledge_line

DELIVERY_QUESTION_KEYWORDS = ("配送", "送", "送达", "发货", "物流")
DELIVERY_KNOWLEDGE_FALLBACK = (
    "当前知识库没有命中具体配送安排。员工可回复：配送时间以商品、区域和排期为准，"
    "建议在后台知识库或店铺配送配置中确认后再答复客户。"
)


def knowledge_answer_text(question: str, sources: list[dict[str, Any]]) -> str:
    """格式化员工可读知识库回复。"""
    if sources:
        return "\n".join(knowledge_line(item) for item in sources)
    if _is_delivery_question(question):
        return DELIVERY_KNOWLEDGE_FALLBACK
    return "未找到匹配知识。"


def _is_delivery_question(question: str) -> bool:
    return any(keyword in question for keyword in DELIVERY_QUESTION_KEYWORDS)
