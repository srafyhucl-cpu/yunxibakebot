"""
Function Calling 工具定义与分发。

定义 LLM 可调用的工具：查订单、查商品、查物流、搜知识库。
dispatch_tool 根据工具名称路由到对应处理函数。

注意：transfer_to_human 工具由 ChatService 的工具调度循环直接处理，
不经过本模块，因为它需要 TransferManager 的依赖。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.logger import setup_logger
from app.models.session import Session

if TYPE_CHECKING:
    from app.service.knowledge_retriever import KnowledgeRetriever

# 最大连续工具调用轮数，超限后输出兜底回复
MAX_TOOL_ROUNDS = 3
# 知识检索返回条目数上限
PRODUCT_SEARCH_LIMIT = 3
KNOWLEDGE_SEARCH_LIMIT = 5

logger = setup_logger()

# DeepSeek Function Calling 工具定义（按需扩展）
FUNCTION_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_order_info",
            "description": "查询订单详细信息：状态、商品、金额、收货地址等",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_no": {"type": "string", "description": "订单号"},
                },
                "required": ["order_no"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_info",
            "description": "查询商品详情：价格、规格、库存等",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "商品名称"},
                    "product_id": {"type": "string", "description": "商品ID"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_logistics_info",
            "description": "查询物流配送进度",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_no": {"type": "string", "description": "订单号"},
                },
                "required": ["order_no"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_to_human",
            "description": "当用户要求转人工、表达不满或复杂售后问题时，转接人工客服",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "转人工原因"},
                },
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "搜索知识库，查找常见问题、店铺政策、产品介绍等",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                },
                "required": ["query"],
            },
        },
    },
]


async def get_order_info(order_no: str) -> str:
    """
    查询订单信息。

    有赞 API 尚未接入（有赞实名认证审核中），引导用户联系人工客服或自助查看。
    """
    return json.dumps(
        {"order_no": order_no, "available": False, "message": "订单查询暂时无法使用，请在有赞店铺查看或联系人工客服"},
        ensure_ascii=False,
    )


async def get_product_info(
    knowledge_retriever: KnowledgeRetriever,
    product_name: str = "",
    product_id: str = "",
) -> str:
    """使用知识库检索商品信息。"""
    query = product_name or product_id
    if not query:
        return json.dumps({"message": "未提供商品名称或ID"}, ensure_ascii=False)
    try:
        entries = await knowledge_retriever.search(query, limit=PRODUCT_SEARCH_LIMIT)
    except Exception as exc:
        logger.error("商品知识检索失败: query=%s err=%s", query, exc)
        return json.dumps({"message": "商品查询暂时无法使用，请联系人工客服"}, ensure_ascii=False)
    if not entries:
        return json.dumps({"query": query, "results": [], "message": "知识库中未找到相关商品"}, ensure_ascii=False)
    results = [{"title": e.title, "content": e.content, "category": e.category} for e in entries]
    return json.dumps({"query": query, "results": results}, ensure_ascii=False)


async def get_logistics_info(order_no: str) -> str:
    """
    查询物流信息。

    有赞 API 尚未接入（有赞实名认证审核中），引导用户联系人工客服。
    """
    return json.dumps(
        {"order_no": order_no, "available": False, "message": "物流查询暂时无法使用，请联系人工客服获取配送进度"},
        ensure_ascii=False,
    )


async def search_knowledge(knowledge_retriever: KnowledgeRetriever, query: str) -> str:
    """使用知识库检索常见问题、店铺政策、产品介绍等。"""
    try:
        entries = await knowledge_retriever.search(query, limit=KNOWLEDGE_SEARCH_LIMIT)
    except Exception as exc:
        logger.error("知识库检索失败: query=%s err=%s", query, exc)
        return json.dumps({"query": query, "results": [], "message": "知识库查询失败，请稍后重试"}, ensure_ascii=False)
    if not entries:
        return json.dumps({"query": query, "results": [], "message": "未找到相关知识"}, ensure_ascii=False)
    results = [{"title": e.title, "content": e.content, "category": e.category} for e in entries]
    return json.dumps({"query": query, "results": results}, ensure_ascii=False)


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
            return await get_order_info(**args)
        case "get_logistics_info":
            return await get_logistics_info(**args)
        case "get_product_info":
            if knowledge_retriever is None:
                return json.dumps({"message": "商品查询服务暂不可用"}, ensure_ascii=False)
            return await get_product_info(knowledge_retriever, **args)
        case "search_knowledge":
            if knowledge_retriever is None:
                return json.dumps({"message": "知识库服务暂不可用"}, ensure_ascii=False)
            return await search_knowledge(knowledge_retriever, **args)
        case "transfer_to_human":
            # 由 ChatService 工具调度循环拦截处理，此处为安全兜底
            return json.dumps({"status": "pending", "message": "正在为您转接人工客服"}, ensure_ascii=False)
        case _:
            return json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False)
