"""员工助手 LangGraph application adapter。"""

from app.service.agents.employee.graph import build_employee_agent_graph
from app.service.agents.employee.nodes import EmployeeGraphDependencies


class EmployeeAgentGraphService:
    """员工助手 LangGraph 编排服务。"""

    def __init__(self, dependencies: EmployeeGraphDependencies) -> None:
        self._dependencies = dependencies
        self._graph = None

    async def answer(self, query: str) -> str:
        """执行员工助手 LangGraph 并返回原始确定性回复。"""
        result = await self._compiled_graph().ainvoke({"query": query})
        return str(result.get("reply", ""))

    def _compiled_graph(self):
        if self._graph is None:
            self._graph = build_employee_agent_graph(self._dependencies)
        return self._graph
