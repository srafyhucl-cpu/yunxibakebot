"""
Function Calling 工具分发器。

聚合工具定义与实现子模块，提供 dispatch_tool 路由入口。
向后兼容导出：FUNCTION_DEFINITIONS、MAX_TOOL_ROUNDS 及各工具函数，调用方无需修改 import。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.logger import setup_logger
from app.models.session import Session
from app.service.llm.function_defs import (
    FUNCTION_DEFINITIONS,
    KNOWLEDGE_SEARCH_LIMIT,
    MAX_TOOL_ROUNDS,
    PRODUCT_SEARCH_LIMIT,
)
from app.service.llm.function_tool_order import get_logistics_info, get_order_info
from app.service.llm.function_tool_product import get_product_info, search_knowledge

if TYPE_CHECKING:
    from app.service.knowledge_retriever import KnowledgeRetriever

logger = setup_logger()

__all__ = [
    "FUNCTION_DEFINITIONS",
    "MAX_TOOL_ROUNDS",
    "PRODUCT_SEARCH_LIMIT",
    "KNOWLEDGE_SEARCH_LIMIT",
    "get_order_info",
    "get_logistics_info",
    "get_product_info",
    "search_knowledge",
    "dispatch_tool",
]


async def dispatch_tool(
    tool_name: str,
    args: dict,
    session: Session | None = None,
    knowledge_retriever: KnowledgeRetriever | None = None,
) -> str:
    """
    根据工具名称分发到对应处理函数。

    参数：
        tool_name: 工具名称
        args: 工具参数字典
        session: 当前会话
        knowledge_retriever: 知识检索器（search_knowledge / get_product_info 必传）
    返回：
        工具执行结果的 JSON 字符串
    """
    match tool_name:
        case "get_order_info":
            if knowledge_retriever is None:
                return json.dumps({"message": "订单查询服务暂不可用"}, ensure_ascii=False)
            return await get_order_info(knowledge_retriever, **args)
        case "get_logistics_info":
            if knowledge_retriever is None:
                return json.dumps({"message": "物流查询服务暂不可用"}, ensure_ascii=False)
            return await get_logistics_info(knowledge_retriever, **args)
        case "get_product_info":
            if knowledge_retriever is None:
                return json.dumps({"message": "商品查询服务暂不可用"}, ensure_ascii=False)
            return await get_product_info(knowledge_retriever, session, **args)
        case "search_knowledge":
            if knowledge_retriever is None:
                return json.dumps({"message": "知识库服务暂不可用"}, ensure_ascii=False)
            return await search_knowledge(knowledge_retriever, **args)
        case "transfer_to_human":
            # 由 ChatService 工具调度循环拦截处理，此处为安全兜底
            return json.dumps({"status": "pending", "message": "正在为您转接人工客服"}, ensure_ascii=False)
        case _:
            return json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False)
