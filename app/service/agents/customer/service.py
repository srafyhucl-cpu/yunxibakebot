"""客户机器人 LangGraph application adapter。"""

from app.service.agents.customer.graph import build_customer_agent_graph
from app.service.agents.customer.nodes import (
    CustomerGraphDependencies,
    CustomerGraphRequest,
    initial_customer_state,
)


class CustomerAgentGraphService:
    """客户机器人 LangGraph 编排服务。"""

    def __init__(self, dependencies: CustomerGraphDependencies) -> None:
        self._dependencies = dependencies
        self._graph = None

    async def answer(self, request: CustomerGraphRequest) -> str:
        """执行客户机器人 LangGraph 并返回回复。"""
        result = await self._compiled_graph().ainvoke(initial_customer_state(request))
        return str(result.get("reply", ""))

    def _compiled_graph(self):
        if self._graph is None:
            self._graph = build_customer_agent_graph(self._dependencies)
        return self._graph
