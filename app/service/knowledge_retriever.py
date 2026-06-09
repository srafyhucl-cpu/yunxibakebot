"""
知识库检索服务。

支持两种模式：
- 语义向量搜索（EmbeddingSearcher）：语义理解，模糊匹配
- 关键词搜索（SQL LIKE）：精确匹配

调用顺序：向量搜索 → 不够时补充关键词结果。
向量搜索通过 asyncio.to_thread 包裹，不阻塞事件循环。
"""

import asyncio
import urllib.parse

from app.logger import setup_logger
from app.models.config import FEATURED_PRODUCTS_KEY
from app.models.knowledge import KnowledgeEntry
from app.repository.config_repo import ConfigRepo
from app.repository.knowledge_repo import KnowledgeRepo
from app.service.bm25_search import BM25Searcher
from app.service.embedding_search import EmbeddingSearcher
from app.service.retrieval_fusion import DEFAULT_RRF_K, fuse_ranked_results
from app.service.youzan.client import YOUZAN_GOODS_H5_BASE_URL
from app.config import settings

logger = setup_logger()

RECOMMENDABLE_PRODUCT_ACTIVE = 1
MIN_RECOMMENDABLE_STOCK = 1
# 虚拟高库存阈值（生日/定制蛋糕类设置为 >= 此值表示常态化可下单）
VIRTUAL_HIGH_STOCK_THRESHOLD = 200


class KnowledgeRetriever:
    """知识检索器：向量搜索 + 关键词搜索组合，并优先注入可售主推款。"""

    def __init__(
        self,
        repo: KnowledgeRepo,
        vs: EmbeddingSearcher | None = None,
        config_repo: ConfigRepo | None = None,
        bm25: BM25Searcher | None = None,
        enable_hybrid_retrieval: bool | None = None,
        rrf_k: int | None = None,
    ) -> None:
        self._repo = repo
        self._vs = vs
        self._config_repo = config_repo
        self._bm25 = bm25
        self._enable_hybrid_retrieval = (
            settings.ENABLE_HYBRID_RETRIEVAL
            if enable_hybrid_retrieval is None
            else enable_hybrid_retrieval
        )
        self._rrf_k = settings.RRF_K if rrf_k is None else rrf_k

    async def search(self, query: str, limit: int = 8) -> list[KnowledgeEntry]:
        """
        混合检索：优先向量，不足时补关键词。

        参数：
            query: 用户查询文本
            limit: 返回最大条数
        返回：
            匹配的知识条目列表
        """
        if not query.strip():
            return []

        if self._enable_hybrid_retrieval:
            hybrid_results = await self._search_hybrid(query, limit)
            if hybrid_results:
                results = await self._inject_featured(hybrid_results, limit)
                return await self._prepend_live_data(results)

        entries: list[KnowledgeEntry] = []
        if self._vs and self._vs.doc_count > 0:
            vs_results = await asyncio.to_thread(self._vs.search, query, limit)
            if vs_results:
                keys = [k for k, _ in vs_results]
                entries = await self._repo.get_by_youzan_item_ids(keys, limit=len(keys))
                logger.debug("向量检索 '%s' → %d 条", query[:30], len(entries))

        keyword_results = await self._repo.search(query, limit=limit)
        logger.debug("关键词检索 '%s' → %d 条", query[:30], len(keyword_results))
        merged = self._merge_entries(keyword_results, entries, limit)
        results = await self._inject_featured(merged, limit)
        return await self._prepend_live_data(results)

    async def _search_hybrid(self, query: str, limit: int) -> list[KnowledgeEntry]:
        candidate_limit = max(limit * 3, limit)
        vector_results: list[tuple[str, float]] = []
        bm25_results: list[tuple[str, float]] = []

        if self._vs and self._vs.doc_count > 0:
            vector_results = await asyncio.to_thread(
                self._vs.search, query, candidate_limit
            )
        if self._bm25 and self._bm25.doc_count > 0:
            bm25_results = await asyncio.to_thread(
                self._bm25.search, query, candidate_limit
            )

        fused_keys = fuse_ranked_results(
            [vector_results, bm25_results],
            limit=limit,
            rrf_k=self._rrf_k or DEFAULT_RRF_K,
        )
        if not fused_keys:
            return []

        entries = await self._repo.get_by_youzan_item_ids(
            fused_keys, limit=len(fused_keys)
        )
        entries_by_key = {self._entry_key(entry): entry for entry in entries}
        ordered_entries = [
            entries_by_key[key] for key in fused_keys if key in entries_by_key
        ]
        logger.debug(
            "混合检索 '%s' → vector=%d bm25=%d fused=%d",
            query[:30],
            len(vector_results),
            len(bm25_results),
            len(ordered_entries),
        )
        return ordered_entries

    async def search_keyword_only(
        self, query: str, limit: int = 8
    ) -> list[KnowledgeEntry]:
        if not query.strip():
            return []
        results = await self._repo.search(query, limit=limit)
        logger.debug("精确关键词检索 '%s' → %d 条", query[:30], len(results))
        featured_results = await self._inject_featured(results, limit)
        return await self._prepend_live_data(featured_results)

    async def _prepend_live_data(
        self, entries: list[KnowledgeEntry]
    ) -> list[KnowledgeEntry]:
        """对于含有 youzan_item_id 的知识条目，现场秒级反查 products 物理表并动态拼接最新库存与售价。"""
        if not entries:
            return entries

        from app.repository.youzan_repo import YouzanProductRepo

        product_repo = YouzanProductRepo(self._repo._db)

        for entry in entries:
            if entry.youzan_item_id:
                try:
                    product = await product_repo.get_by_id(int(entry.youzan_item_id))
                    if product:
                        price_yuan = product["price_fen"] / 100.0
                        stock = product["stock"]
                        is_active = product["is_active"]

                        # 构造富提示前置前缀，死锁 AI 回复幻觉风险
                        if is_active == 0:
                            live_prefix = "【芸熙烘焙小程序实时官方数据 — ⚠️商品当前已下架或暂停预定】\n\n"
                        elif stock <= 0:
                            live_prefix = f"【芸熙烘焙小程序实时官方数据 — 当前售价：{price_yuan:.2f}元 | ⚠️商品当前在售但库存已为0，暂无现货，需要提前预约】\n\n"
                        elif stock >= VIRTUAL_HIGH_STOCK_THRESHOLD:
                            # 🎂 生日/选配蛋糕类（虚拟高库存 >= 200）
                            live_prefix = f"【芸熙烘焙小程序实时官方数据 — 当前售价：{price_yuan:.2f}元 | 实时可用库存：充足（常态化现做预定制商品，只要买家下单即可新鲜现做，请告知买家随时可放心下单，无需向其透露具体数字）】\n\n"
                        else:
                            # 🥖 现烤面包/西点类（实体日限量 < 200）
                            live_prefix = f"【芸熙烘焙小程序实时官方数据 — 当前售价：{price_yuan:.2f}元 | 实时可用库存：仅剩 {stock} 件（属于每日限量现烤面包西点，售罄即止，若库存偏低请温和提示买家抢购）】\n\n"

                        entry.content = live_prefix + entry.content

                        # 当商品处于在售状态（is_active == 1）时，向 RAG 召回内容尾部增量组装统一媒体协议（UMP）线性标记
                        if is_active == 1:
                            alias = product["alias"] or ""
                            img_params = urllib.parse.urlencode(
                                {"type": "image", "src": product["image"] or ""},
                                quote_via=urllib.parse.quote,
                            )
                            card_params = urllib.parse.urlencode(
                                {
                                    "type": "card",
                                    "id": entry.youzan_item_id,
                                    "title": entry.title,
                                    "price": f"{price_yuan:.2f}",
                                    "src": product["image"] or "",
                                    "url": f"{YOUZAN_GOODS_H5_BASE_URL}?alias={alias}",
                                },
                                quote_via=urllib.parse.quote,
                            )
                            entry.content += f"\n[UMP: {img_params}]"
                            entry.content += f"\n[UMP: {card_params}]"
                except Exception as exc:
                    logger.warning(
                        "现场反查商品库存（ID: %s）发生非致命异常: %s",
                        entry.youzan_item_id,
                        exc,
                    )

        return entries

    def _merge_entries(
        self,
        preferred_entries: list[KnowledgeEntry],
        fallback_entries: list[KnowledgeEntry],
        limit: int,
    ) -> list[KnowledgeEntry]:
        results: list[KnowledgeEntry] = []
        seen_titles: set[str] = set()
        for entry in [*preferred_entries, *fallback_entries]:
            if entry.title in seen_titles:
                continue
            results.append(entry)
            seen_titles.add(entry.title)
            if len(results) >= limit:
                break
        return results

    @staticmethod
    def _entry_key(entry: KnowledgeEntry) -> str:
        return entry.youzan_item_id if entry.youzan_item_id else f"kb_{entry.id}"

    async def _inject_featured(
        self,
        results: list[KnowledgeEntry],
        limit: int,
    ) -> list[KnowledgeEntry]:
        """Prepend configured featured products only when they are sellable."""
        if not self._config_repo:
            return results
        products = await self._config_repo.get_list(FEATURED_PRODUCTS_KEY)
        if not products:
            return results

        featured_entries = await self._repo.get_by_titles(products, limit=len(products))
        featured_by_title = {entry.title: entry for entry in featured_entries}
        matched_featured_entries = [
            featured_by_title[title] for title in products if title in featured_by_title
        ]
        ordered_featured = await self._filter_recommendable_featured_products(
            matched_featured_entries
        )
        missing_titles = [title for title in products if title not in featured_by_title]
        if missing_titles:
            logger.warning(
                "后台主推款未匹配到启用商品知识: %s",
                "、".join(missing_titles),
            )

        if not ordered_featured:
            return results

        seen_titles = {entry.title for entry in ordered_featured}
        deduped_results = [entry for entry in results if entry.title not in seen_titles]
        return [*ordered_featured, *deduped_results][:limit]

    async def _filter_recommendable_featured_products(
        self,
        entries: list[KnowledgeEntry],
    ) -> list[KnowledgeEntry]:
        """Keep featured products that are active and in stock in youzan_products."""
        if not entries:
            return []

        from app.repository.youzan_repo import YouzanProductRepo

        product_repo = YouzanProductRepo(self._repo._db)

        recommendable_entries: list[KnowledgeEntry] = []
        for entry in entries:
            if not entry.youzan_item_id:
                logger.warning(
                    "后台主推款缺少有赞商品ID，已跳过: %s",
                    entry.title,
                )
                continue
            try:
                product = await product_repo.get_by_id(int(entry.youzan_item_id))
            except (TypeError, ValueError) as exc:
                logger.warning(
                    "后台主推款有赞商品ID无效，已跳过: title=%s id=%s err=%s",
                    entry.title,
                    entry.youzan_item_id,
                    exc,
                )
                continue
            if not product:
                logger.warning(
                    "后台主推款未找到有赞商品物理数据，已跳过: title=%s id=%s",
                    entry.title,
                    entry.youzan_item_id,
                )
                continue
            if product["is_active"] != RECOMMENDABLE_PRODUCT_ACTIVE:
                logger.warning(
                    "后台主推款商品未上架，已跳过: title=%s id=%s",
                    entry.title,
                    entry.youzan_item_id,
                )
                continue
            if product["stock"] < MIN_RECOMMENDABLE_STOCK:
                logger.warning(
                    "后台主推款商品库存不足，已跳过: title=%s id=%s stock=%s",
                    entry.title,
                    entry.youzan_item_id,
                    product["stock"],
                )
                continue
            recommendable_entries.append(entry)

        return recommendable_entries
