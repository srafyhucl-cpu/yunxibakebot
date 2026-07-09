"""LangChain RAG Retriever 适配测试。"""

import pytest

from app.models.knowledge import KnowledgeEntry
from app.service.agents.rag.documents import knowledge_entry_to_document
from app.service.agents.rag.query import (
    RagQueryPlan,
    RagQueryVariant,
    build_customer_rag_query_plan,
)
from app.service.agents.rag.retriever import LangChainKnowledgeRetriever


class _FakeKnowledgeRetriever:
    def __init__(self, entries: list[KnowledgeEntry]) -> None:
        self.entries = entries
        self.calls: list[tuple[str, int]] = []

    async def search(self, query: str, limit: int = 8) -> list[KnowledgeEntry]:
        self.calls.append((query, limit))
        return self.entries[:limit]


class _FakeMultiQueryKnowledgeRetriever:
    def __init__(self, entries_by_query: dict[str, list[KnowledgeEntry]]) -> None:
        self.entries_by_query = entries_by_query
        self.calls: list[tuple[str, int]] = []

    async def search(self, query: str, limit: int = 8) -> list[KnowledgeEntry]:
        self.calls.append((query, limit))
        return self.entries_by_query.get(query, [])[:limit]


def test_knowledge_entry_to_document_preserves_metadata() -> None:
    entry = KnowledgeEntry(
        id=7,
        category="product",
        content_type="product",
        title="草莓蛋糕",
        content="草莓蛋糕 48 元",
        audience="customer",
        review_status="published",
        youzan_item_id="1001",
        priority=30,
        valid_from="2026-07-01",
        valid_until="2026-07-31",
        last_sync_source="youzan",
        last_sync_ref="item:1001",
    )

    document = knowledge_entry_to_document(entry)

    assert document.page_content == "草莓蛋糕 48 元"
    assert document.metadata["knowledge_id"] == 7
    assert document.metadata["title"] == "草莓蛋糕"
    assert document.metadata["category"] == "product"
    assert document.metadata["audience"] == "customer"
    assert document.metadata["youzan_item_id"] == "1001"


@pytest.mark.asyncio
async def test_langchain_knowledge_retriever_returns_documents() -> None:
    entries = [
        KnowledgeEntry(id=1, title="配送范围", content="三公里内可配送"),
        KnowledgeEntry(id=2, title="退款规则", content="未制作可退款"),
    ]
    fake_retriever = _FakeKnowledgeRetriever(entries)
    retriever = LangChainKnowledgeRetriever(fake_retriever, limit=1).as_retriever()

    documents = await retriever.ainvoke("配送")

    assert fake_retriever.calls == [("配送", 1)]
    assert len(documents) == 1
    assert documents[0].page_content == "三公里内可配送"
    assert documents[0].metadata["title"] == "配送范围"


def test_customer_rag_query_plan_expands_refund_question() -> None:
    plan = build_customer_rag_query_plan("  蛋糕坏了 可以退款吗  ")

    assert plan.original_query == "蛋糕坏了 可以退款吗"
    assert [variant.query for variant in plan.variants] == [
        "蛋糕坏了 可以退款吗",
        "退款规则 售后政策",
        "售后处理 转人工",
    ]


@pytest.mark.asyncio
async def test_langchain_knowledge_retriever_supports_multi_query_metadata() -> None:
    delivery_entry = KnowledgeEntry(
        id=1,
        title="配送范围",
        content="三公里内可配送",
        youzan_item_id="1001",
    )
    refund_entry = KnowledgeEntry(
        id=2,
        title="退款规则",
        content="未制作可退款",
        youzan_item_id="1002",
    )
    fake_retriever = _FakeMultiQueryKnowledgeRetriever(
        {
            "原始退款问题": [delivery_entry],
            "退款规则 售后政策": [delivery_entry, refund_entry],
        }
    )

    def query_planner(query: str) -> RagQueryPlan:
        return RagQueryPlan(
            original_query=query,
            variants=(
                RagQueryVariant(query=query, reason="original"),
                RagQueryVariant(query="退款规则 售后政策", reason="rule_expand"),
            ),
        )

    retriever = LangChainKnowledgeRetriever(
        fake_retriever,
        limit=2,
        query_planner=query_planner,
    ).as_retriever()

    documents = await retriever.ainvoke("原始退款问题")

    assert fake_retriever.calls == [
        ("原始退款问题", 2),
        ("退款规则 售后政策", 2),
    ]
    assert [document.metadata["title"] for document in documents] == [
        "配送范围",
        "退款规则",
    ]
    assert documents[0].metadata["original_query"] == "原始退款问题"
    assert documents[1].metadata["retrieval_query"] == "退款规则 售后政策"
    assert documents[1].metadata["query_variant_index"] == 1
