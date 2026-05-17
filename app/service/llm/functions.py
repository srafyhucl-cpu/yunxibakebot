"""
Function Calling 工具定义与分发。

定义 LLM 可调用的工具：查订单、查商品、查物流、转人工、搜知识库。
dispatch_tool 根据工具名称路由到对应处理函数。
"""

import json

from app.models.session import Session

# 最大连续工具调用轮数，超限后输出兜底回复
MAX_TOOL_ROUNDS = 3

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
    """TODO: 接入有赞 API 查询订单。"""
    return json.dumps({"order_no": order_no, "status": "unknown", "message": "待接入有赞 API"})


async def get_product_info(product_name: str = "", product_id: str = "") -> str:
    """TODO: 从知识库或有赞 API 查询商品。"""
    return json.dumps({"product": product_name or product_id, "message": "待接入知识库"})


async def get_logistics_info(order_no: str) -> str:
    """TODO: 接入有赞 API 查询物流。"""
    return json.dumps({"order_no": order_no, "status": "unknown", "message": "待接入有赞 API"})


async def search_knowledge(query: str) -> str:
    """TODO: 接入知识库检索。"""
    return json.dumps({"query": query, "results": [], "message": "待接入知识库"})


async def dispatch_tool(
    tool_name: str,
    args: dict,
    session: Session | None = None,
) -> str:
    """
    根据工具名称分发到对应处理函数。

    参数：
        tool_name: 工具名称
        args: 工具参数字典
        session: 当前会话（转人工时需要）
    返回：
        工具执行结果的 JSON 字符串
    """
    match tool_name:
        case "get_order_info":
            return await get_order_info(**args)
        case "get_product_info":
            return await get_product_info(**args)
        case "get_logistics_info":
            return await get_logistics_info(**args)
        case "transfer_to_human":
            return json.dumps({"status": "todo", "message": "转人工功能待实现"})
        case "search_knowledge":
            return await search_knowledge(**args)
        case _:
            return json.dumps({"error": f"未知工具: {tool_name}"})
