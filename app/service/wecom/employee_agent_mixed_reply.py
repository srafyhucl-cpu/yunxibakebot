"""企微员工助手多工具回复整理。"""

from __future__ import annotations

import re

from app.models.employee_agent import AgentIntent, AgentPlan, ToolResult

KNOWLEDGE_MISS_TEXT = "未找到匹配知识。"
LOW_STOCK_THRESHOLD = 5
NO_STOCK_VALUE = 0
STOCK_PATTERN = re.compile(r"库存\s*(\d+)")


def build_mixed_tool_reply(
    query: str,
    plan: AgentPlan,
    tool_results: list[ToolResult],
) -> str | None:
    """为组合工具结果生成更像员工助手的确定性回复。"""
    if plan.intent != AgentIntent.MULTI_TOOL:
        return None
    if plan.tools != ("product_lookup", "knowledge_answer"):
        return None
    if len(tool_results) < 2:
        return None
    product_result, knowledge_result = tool_results[0], tool_results[1]
    if not _is_knowledge_miss(knowledge_result) or not product_result.summary.strip():
        return None
    return "\n".join(
        [
            product_result.summary,
            _product_stock_action_reply(query, product_result),
            _next_action_line(product_result),
        ]
    )


def _is_knowledge_miss(result: ToolResult) -> bool:
    return result.summary.strip() == KNOWLEDGE_MISS_TEXT


def _product_stock_action_reply(query: str, result: ToolResult) -> str:
    stock_values = _extract_stock_values(result)
    if stock_values and max(stock_values) <= NO_STOCK_VALUE:
        return (
            "员工建议：系统显示当前没有可售库存，先不要承诺有货；优先向客户推荐同品类、"
            "相近价位或同场景替代款，并同步确认配送/自提时间。"
        )
    if stock_values and min(stock_values) <= LOW_STOCK_THRESHOLD:
        return (
            "员工建议：当前库存偏低，先确认客户需要的数量、规格和配送/自提时间；"
            "如需求超过库存，再推荐同品类、相近价位或同场景替代款。"
        )
    if "没货" in query or "库存不够" in query:
        return (
            "员工建议：实时商品数据看还有库存，先不要直接说没货；请确认客户需要的数量、"
            "规格和配送/自提时间，如实际需求超过库存，再推荐相近口味、同品类或同价位替代款。"
        )
    return (
        "员工建议：先按实时库存回复客户，并确认客户需要的数量、规格和配送/自提时间；"
        "如当前款式不合适，再推荐相近口味、同品类或同价位替代款。"
    )


def _extract_stock_values(result: ToolResult) -> list[int]:
    values: list[int] = []
    for item in result.items:
        stock = item.get("stock")
        if isinstance(stock, int):
            values.append(stock)
    values.extend(int(value) for value in STOCK_PATTERN.findall(result.summary))
    return values


def _next_action_line(result: ToolResult) -> str:
    if result.next_action.strip():
        return "下一步：" + result.next_action.strip()
    return "下一步：员工回复前再到小程序或后台核对实时库存，避免超卖。"
