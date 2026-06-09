import aiosqlite

from app.models.config import FEATURED_PRODUCTS_KEY
from app.repository.config_repo import ConfigRepo
from app.repository.knowledge_product_repo import KnowledgeProductRepo
from app.repository.knowledge_repo import KnowledgeRepo
from app.repository.youzan_repo import YouzanProductRepo
from app.service.knowledge_retriever import KnowledgeRetriever


class _FakeRankSearcher:
    def __init__(self, results: list[tuple[str, float]]) -> None:
        self._results = results
        self.doc_count = len(results)
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, limit: int = 8) -> list[tuple[str, float]]:
        self.calls.append((query, limit))
        return self._results[:limit]


async def _seed_product(
    repo: KnowledgeRepo, item_id: str, title: str, content: str
) -> None:
    prod_repo = KnowledgeProductRepo(repo._db)
    await prod_repo.upsert_product_knowledge(
        youzan_item_id=item_id,
        title=title,
        content=content,
        keywords=title,
        priority=10,
        updated_at="2026-05-24 00:00:00",
    )


async def _seed_live_product(
    repo: YouzanProductRepo,
    item_id: int,
    title: str,
    stock: int,
    is_active: int,
) -> None:
    await repo.upsert_product(
        item_id=item_id,
        title=title,
        alias=f"alias-{item_id}",
        price_fen=23800,
        stock=stock,
        image="https://img.example/product.jpg",
        is_active=is_active,
        updated_at="2026-05-24 00:00:00",
    )


async def test_search_prepends_only_sellable_featured_products(
    db: aiosqlite.Connection,
) -> None:
    knowledge_repo = KnowledgeRepo(db)
    config_repo = ConfigRepo(db)
    product_repo = YouzanProductRepo(db)
    await _seed_product(
        knowledge_repo, "1001", "featured-sellable", "featured-sellable 238 yuan"
    )
    await _seed_product(
        knowledge_repo, "1002", "featured-zero-stock", "featured-zero-stock 238 yuan"
    )
    await _seed_product(
        knowledge_repo, "1003", "featured-inactive", "featured-inactive 238 yuan"
    )
    await _seed_live_product(
        product_repo, 1001, "featured-sellable", stock=5, is_active=1
    )
    await _seed_live_product(
        product_repo, 1002, "featured-zero-stock", stock=0, is_active=1
    )
    await _seed_live_product(
        product_repo, 1003, "featured-inactive", stock=5, is_active=0
    )
    await config_repo.set_list(
        FEATURED_PRODUCTS_KEY,
        [
            "featured-sellable",
            "featured-zero-stock",
            "featured-inactive",
            "featured-missing",
        ],
    )

    retriever = KnowledgeRetriever(knowledge_repo, config_repo=config_repo)

    results = await retriever.search("recommend products", limit=3)

    assert results[0].title == "featured-sellable"
    assert results[0].category == "product"
    assert all(entry.title != "近期主推款" for entry in results)
    assert all(entry.title != "featured-zero-stock" for entry in results)
    assert all(entry.title != "featured-inactive" for entry in results)
    assert all(entry.title != "featured-missing" for entry in results)


async def test_search_keeps_legacy_path_when_hybrid_disabled(
    db: aiosqlite.Connection,
) -> None:
    knowledge_repo = KnowledgeRepo(db)
    await _seed_product(knowledge_repo, "1001", "keyword-target", "legacy keyword hit")
    await _seed_product(knowledge_repo, "1002", "vector-target", "semantic hit")
    vector_searcher = _FakeRankSearcher([("1002", 0.9)])
    bm25_searcher = _FakeRankSearcher([("1001", 10.0)])
    retriever = KnowledgeRetriever(
        knowledge_repo,
        vector_searcher,
        bm25=bm25_searcher,
        enable_hybrid_retrieval=False,
    )

    results = await retriever.search("keyword-target", limit=2)

    assert [entry.title for entry in results[:2]] == [
        "keyword-target",
        "vector-target",
    ]
    assert bm25_searcher.calls == []


async def test_search_uses_rrf_order_when_hybrid_enabled(
    db: aiosqlite.Connection,
) -> None:
    knowledge_repo = KnowledgeRepo(db)
    await _seed_product(knowledge_repo, "1001", "vector-only", "semantic hit")
    await _seed_product(
        knowledge_repo, "1002", "shared-hit", "keyword and semantic hit"
    )
    vector_searcher = _FakeRankSearcher([("1001", 0.95), ("1002", 0.9)])
    bm25_searcher = _FakeRankSearcher([("1002", 10.0)])
    retriever = KnowledgeRetriever(
        knowledge_repo,
        vector_searcher,
        bm25=bm25_searcher,
        enable_hybrid_retrieval=True,
        rrf_k=60,
    )

    results = await retriever.search("shared", limit=2)

    assert [entry.title for entry in results[:2]] == ["shared-hit", "vector-only"]
    assert vector_searcher.calls == [("shared", 6)]
    assert bm25_searcher.calls == [("shared", 6)]
