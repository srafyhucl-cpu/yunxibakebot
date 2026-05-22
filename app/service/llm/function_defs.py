"""
Function Calling 工具定义常量。

定义 LLM 可调用工具的 schema 列表和相关控制常量，供 functions.py 及各工具模块引用。
"""

# 最大连续工具调用轮数，超限后输出兜底回复
MAX_TOOL_ROUNDS = 3
# 商品知识检索返回条目数上限
PRODUCT_SEARCH_LIMIT = 3
# 通用知识检索返回条目数上限
KNOWLEDGE_SEARCH_LIMIT = 5

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
