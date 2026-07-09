"""LangGraph checkpoint 配置测试。"""

from pathlib import Path
import subprocess
import sys

import pytest

from app.models.session import Session
from app.service.agents.checkpoints import (
    build_customer_graph_config,
    build_thread_id,
)


def test_build_thread_id_uses_namespace_and_identifier() -> None:
    assert build_thread_id("customer", "session-1") == "customer:session-1"


def test_build_thread_id_rejects_empty_parts() -> None:
    with pytest.raises(ValueError):
        build_thread_id("", "session-1")
    with pytest.raises(ValueError):
        build_thread_id("customer", " ")


def test_build_customer_graph_config_uses_session_id() -> None:
    config = build_customer_graph_config(
        Session(id="session-1", channel="youzan", user_id="buyer-1")
    )

    assert config == {"configurable": {"thread_id": "customer:session-1"}}


def test_checkpoints_import_does_not_import_langgraph() -> None:
    project_root = Path(__file__).resolve().parents[3]
    command = (
        "import sys; "
        "import app.service.agents.checkpoints; "
        "raise SystemExit(1 if 'langgraph' in sys.modules else 0)"
    )

    result = subprocess.run(
        [sys.executable, "-c", command],
        cwd=project_root,
        check=False,
    )

    assert result.returncode == 0


def test_create_in_memory_checkpointer_loads_langgraph_on_demand() -> None:
    project_root = Path(__file__).resolve().parents[3]
    command = (
        "import sys; "
        "from app.service.agents.checkpoints import create_in_memory_checkpointer; "
        "before = 'langgraph' in sys.modules; "
        "create_in_memory_checkpointer(); "
        "after = 'langgraph' in sys.modules; "
        "raise SystemExit(0 if before is False and after is True else 1)"
    )

    result = subprocess.run(
        [sys.executable, "-c", command],
        cwd=project_root,
        check=False,
    )

    assert result.returncode == 0
