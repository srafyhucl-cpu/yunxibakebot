"""LangChain 适配层测试。"""

import sys


def test_agents_llm_import_does_not_import_langchain_runtime() -> None:
    sys.modules.pop("app.service.agents.llm", None)
    sys.modules.pop("langchain_openai", None)

    import app.service.agents.llm  # noqa: F401

    assert "langchain_openai" not in sys.modules


def test_langchain_chat_model_factory_builds_mimo_model() -> None:
    from app.service.agents.llm import get_langchain_chat_model

    model = get_langchain_chat_model(provider="mimo", model="mimo-test")

    assert model.model_name == "mimo-test"
    assert str(model.openai_api_base).rstrip("/") == "https://api.xiaomimimo.com/v1"
