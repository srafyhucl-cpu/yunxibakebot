"""客户机器人 LangGraph 编排测试。"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from app.models.session import Session
from app.service.agents.customer.nodes import (
    CustomerGraphDependencies,
    CustomerGraphRequest,
)
from app.service.agents.customer.service import CustomerAgentGraphService
from app.service.llm.intent import IntentType


class _FakeSessionManager:
    async def build_context(self, session_id: str) -> list[dict[str, str]]:
        return [{"role": "user", "content": f"history:{session_id}"}]


class _FakeKnowledgeRetriever:
    async def search(self, query: str, limit: int = 8) -> list:
        return []

    async def search_keyword_only(self, query: str, limit: int = 8) -> list:
        return []


class _FakeTool:
    name = "search_knowledge"

    async def ainvoke(self, args: dict[str, Any]) -> str:
        return f"tool:{args['query']}"


async def _fake_alerter(message: str) -> None:
    raise AssertionError(message)


@pytest.mark.asyncio
async def test_customer_graph_runs_tool_round_then_returns_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.service.agents.customer import nodes as customer_nodes

    tool_call = SimpleNamespace(
        id="tool-1",
        function=SimpleNamespace(
            name="search_knowledge",
            arguments='{"query": "配送范围"}',
        ),
    )
    requests: list[list[dict]] = []

    async def fake_request_llm_choice(context: Any) -> Any:
        requests.append(context.messages)
        if len(requests) == 1:
            return SimpleNamespace(
                fallback_reply=None,
                choice=SimpleNamespace(finish_reason="tool_calls"),
                message=SimpleNamespace(content=None, tool_calls=[tool_call]),
                first_llm_started_at=1.0,
            )
        return SimpleNamespace(
            fallback_reply=None,
            choice=SimpleNamespace(finish_reason="stop"),
            message=SimpleNamespace(content="最终回复", tool_calls=[]),
            first_llm_started_at=1.0,
        )

    def fake_build_tools(scope: str, **kwargs: Any) -> list[_FakeTool]:
        assert scope == "customer"
        return [_FakeTool()]

    monkeypatch.setattr(customer_nodes, "request_llm_choice", fake_request_llm_choice)
    monkeypatch.setattr(customer_nodes, "build_tools", fake_build_tools)
    service = CustomerAgentGraphService(
        CustomerGraphDependencies(
            session_mgr=_FakeSessionManager(),
            knowledge=_FakeKnowledgeRetriever(),
            transfer_mgr=object(),
            session_repo=object(),
            youzan_client=object(),
            fallback_reply="fallback",
            timeout_reply="timeout",
            failure_alerter=_fake_alerter,
        )
    )
    timing: dict[str, Any] = {}

    reply = await service.answer(
        CustomerGraphRequest(
            session=Session(id="session-1", channel="youzan", user_id="buyer-1"),
            user_query="配送范围",
            intent=IntentType.PRODUCT_CONSULTATION,
            timing=timing,
        )
    )

    assert reply == "最终回复"
    assert len(requests) == 2
    assert timing["tool_rounds"] == 1
    assert "tool:配送范围" in timing["guard_source_text"]
    assert timing["context_budget"]["tool_result_message_count"] == 1


def test_customer_service_import_does_not_import_langgraph() -> None:
    project_root = Path(__file__).resolve().parents[3]
    command = (
        "import sys; "
        "import app.service.chat_ai_loop; "
        "raise SystemExit(1 if 'langgraph' in sys.modules else 0)"
    )

    result = subprocess.run(
        [sys.executable, "-c", command],
        cwd=project_root,
        check=False,
    )

    assert result.returncode == 0
