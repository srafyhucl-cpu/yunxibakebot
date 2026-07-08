"""客户机器人 LangChain 工具。"""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from app.models.session import Session


@dataclass(frozen=True)
class CustomerToolContext:
    """客户机器人工具运行依赖。"""

    session: Session | None = None
    knowledge_retriever: Any = None
    youzan_client: Any = None
    transfer_handler: Any = None


class OrderInfoArgs(BaseModel):
    order_no: str = Field(description="订单号")


class ProductInfoArgs(BaseModel):
    product_name: str = Field(default="", description="商品名称")
    product_id: str = Field(default="", description="商品ID")


class LogisticsInfoArgs(BaseModel):
    order_no: str = Field(description="订单号")


class TransferToHumanArgs(BaseModel):
    reason: str = Field(description="转人工原因")


class SearchKnowledgeArgs(BaseModel):
    query: str = Field(description="搜索关键词")


def build_customer_tools(context: CustomerToolContext) -> list[Any]:
    """构造客户机器人 LangChain 工具列表。"""
    from langchain_core.tools import StructuredTool

    return [
        _build_order_info_tool(context, StructuredTool),
        _build_product_info_tool(context, StructuredTool),
        _build_logistics_info_tool(context, StructuredTool),
        _build_transfer_tool(context, StructuredTool),
        _build_search_knowledge_tool(context, StructuredTool),
    ]


def _build_order_info_tool(context: CustomerToolContext, structured_tool: Any) -> Any:
    async def get_order_info_tool(order_no: str) -> str:
        from app.service.llm.functions import dispatch_tool

        return await dispatch_tool(
            "get_order_info",
            {"order_no": order_no},
            context.session,
            context.knowledge_retriever,
            context.youzan_client,
        )

    return structured_tool.from_function(
        coroutine=get_order_info_tool,
        name="get_order_info",
        description="查询订单详细信息：状态、商品、金额、收货地址等",
        args_schema=OrderInfoArgs,
    )


def _build_product_info_tool(context: CustomerToolContext, structured_tool: Any) -> Any:
    async def get_product_info_tool(
        product_name: str = "",
        product_id: str = "",
    ) -> str:
        from app.service.llm.functions import dispatch_tool

        return await dispatch_tool(
            "get_product_info",
            {"product_name": product_name, "product_id": product_id},
            context.session,
            context.knowledge_retriever,
            context.youzan_client,
        )

    return structured_tool.from_function(
        coroutine=get_product_info_tool,
        name="get_product_info",
        description="实时查询指定商品的最新价格、规格和库存",
        args_schema=ProductInfoArgs,
    )


def _build_logistics_info_tool(
    context: CustomerToolContext,
    structured_tool: Any,
) -> Any:
    async def get_logistics_info_tool(order_no: str) -> str:
        from app.service.llm.functions import dispatch_tool

        return await dispatch_tool(
            "get_logistics_info",
            {"order_no": order_no},
            context.session,
            context.knowledge_retriever,
            context.youzan_client,
        )

    return structured_tool.from_function(
        coroutine=get_logistics_info_tool,
        name="get_logistics_info",
        description="查询物流配送进度",
        args_schema=LogisticsInfoArgs,
    )


def _build_transfer_tool(context: CustomerToolContext, structured_tool: Any) -> Any:
    async def transfer_to_human_tool(reason: str) -> str:
        if context.transfer_handler is not None:
            return await context.transfer_handler(reason)

        from app.service.llm.functions import dispatch_tool

        return await dispatch_tool(
            "transfer_to_human",
            {"reason": reason},
            context.session,
            context.knowledge_retriever,
            context.youzan_client,
        )

    return structured_tool.from_function(
        coroutine=transfer_to_human_tool,
        name="transfer_to_human",
        description="当用户要求转人工、表达不满或复杂售后问题时转接人工客服",
        args_schema=TransferToHumanArgs,
        return_direct=True,
    )


def _build_search_knowledge_tool(
    context: CustomerToolContext,
    structured_tool: Any,
) -> Any:
    async def search_knowledge_tool(query: str) -> str:
        from app.service.llm.functions import dispatch_tool

        return await dispatch_tool(
            "search_knowledge",
            {"query": query},
            context.session,
            context.knowledge_retriever,
            context.youzan_client,
        )

    return structured_tool.from_function(
        coroutine=search_knowledge_tool,
        name="search_knowledge",
        description="搜索知识库，查找店铺政策、常见问题和产品介绍",
        args_schema=SearchKnowledgeArgs,
    )
