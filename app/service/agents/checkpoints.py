"""LangGraph checkpoint 配置边界。"""

from typing import Any

from app.models.session import Session

DEFAULT_CUSTOMER_THREAD_NAMESPACE = "customer"


def build_thread_id(namespace: str, identifier: str) -> str:
    """生成稳定的 LangGraph thread_id。"""
    clean_namespace = namespace.strip()
    clean_identifier = identifier.strip()
    if not clean_namespace:
        raise ValueError("thread_id namespace cannot be empty")
    if not clean_identifier:
        raise ValueError("thread_id identifier cannot be empty")
    return f"{clean_namespace}:{clean_identifier}"


def build_customer_graph_config(session: Session) -> dict[str, dict[str, str]]:
    """为客户 graph 调用生成 LangGraph config。"""
    return {
        "configurable": {
            "thread_id": build_thread_id(
                DEFAULT_CUSTOMER_THREAD_NAMESPACE,
                session.id,
            )
        }
    }


def create_in_memory_checkpointer() -> Any:
    """懒加载 LangGraph 内存 checkpointer，避免 app.main 冷导入。"""
    from langgraph.checkpoint.memory import MemorySaver

    return MemorySaver()
