from __future__ import annotations

"""
基于 Sentence-Transformers 的语义向量搜索引擎。

使用 BAAI/bge-small-zh-v1.5 模型替代 TF-IDF，提升中文语义检索质量，
为 KnowledgeRetriever 提供语义搜索能力。

检索原理：
1. build() 时批量编码所有知识条目为稠密向量，并在内存中缓存
2. search() 时编码查询文本，与文档向量做 cosine 相似度计算
3. 返回 Top-K 最相关条目，减少 TF-IDF 对同义表达的遗漏

性能优化：
- 使用 numpy.argpartition 替代全量 sorted，将 Top-K 选择降至 O(n) 均摊
- 可选集成 sklearn.neighbors.NearestNeighbors 实现 ANN 近似检索
"""

import asyncio
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from app.logger import setup_logger
from app.service.embedding_model import (
    EMBEDDING_MODEL,
    MIN_SIMILARITY_SCORE,
    BGE_QUERY_PREFIX,
    _FallbackSentenceTransformer,
    NearestNeighbors,  # type: ignore[possibly-undefined]
    SKLEARN_AVAILABLE,
)

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = setup_logger()


class EmbeddingSearcher:
    """Sentence-Transformers 语义向量搜索实现。"""

    def __init__(self) -> None:
        self._model: SentenceTransformer | _FallbackSentenceTransformer | None = None
        self._embeddings: np.ndarray | None = None
        self._doc_keys: list[str] = []
        self._ready = False
        self._dirty = False
        self._data_hash = ""
        self._lock = asyncio.Lock()
        self._save_event = asyncio.Event()
        # sklearn NearestNeighbors 索引（可选加速）
        self._nn_index: NearestNeighbors | None = None
        self._init_progress = {
            "status": "uninitialized",
            "total": 0,
            "current": 0,
            "start_time": 0.0,
            "elapsed": 0.0,
            "last_build_duration": 0.0,
        }
        try:
            duration_file = Path("data/vector_last_duration.json")
            if duration_file.exists():
                with open(duration_file, "r", encoding="utf-8") as f:
                    self._init_progress["last_build_duration"] = json.load(f).get(
                        "last_build_duration", 0.0
                    )
        except Exception:
            pass

    def _get_model(self) -> SentenceTransformer | _FallbackSentenceTransformer:
        """惰性初始化模型，避免模块导入阶段触发重型依赖加载。"""
        if self._model is None:
            if os.getenv("YUNXI_USE_FAKE_EMBEDDING", "0") == "1":
                self._model = _FallbackSentenceTransformer()
                logger.warning("Embedding 检索已切换到测试轻量编码器")
                return self._model

            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            # 关闭 transformers 的异步权重物化，规避 Windows + Python 3.13 下的偶发崩溃。
            os.environ.setdefault("HF_DEACTIVATE_ASYNC_LOAD", "1")

            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(EMBEDDING_MODEL, local_files_only=True)
            logger.info("Embedding 模型已加载: %s", EMBEDDING_MODEL)
        return self._model

    def build(
        self, documents: list[tuple[str, str, str]], current_db_md5: str = ""
    ) -> None:
        """全量构建语义向量索引并分批更新进度。"""
        import time

        model = self._get_model()
        self._doc_keys = []
        texts: list[str] = []
        for doc_key, title, content in documents:
            self._doc_keys.append(str(doc_key))
            texts.append(f"{title} {content}")

        total_docs = len(texts)
        self._init_progress.update(
            {
                "status": "building",
                "total": total_docs,
                "current": 0,
                "start_time": time.time(),
                "elapsed": 0.0,
            }
        )

        all_embeddings = []
        batch_size = 16
        for i in range(0, total_docs, batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_raw = model.encode(
                batch_texts, normalize_embeddings=True, show_progress_bar=False
            )
            all_embeddings.append(batch_raw)
            self._init_progress["current"] = min(i + batch_size, total_docs)
            self._init_progress["elapsed"] = (
                time.time() - self._init_progress["start_time"]
            )

        self._embeddings = (
            np.vstack(all_embeddings)
            if all_embeddings
            else np.zeros((0, 256), dtype=np.float32)
        )
        self._ready = True
        self._dirty = True
        self._data_hash = current_db_md5
        self._init_progress["status"] = "ready"

        # 构建 NearestNeighbors ANN 索引（加速检索）
        if (
            SKLEARN_AVAILABLE
            and self._embeddings is not None
            and len(self._doc_keys) > 0
        ):
            try:
                assert NearestNeighbors is not None
                # 动态计算合理的最近邻数量
                n_neighbors = min(
                    max(50, len(self._doc_keys) // 10), len(self._doc_keys)
                )
                self._nn_index = NearestNeighbors(  # type: ignore[misc]
                    n_neighbors=n_neighbors,
                    metric="cosine",
                    algorithm="auto",
                )
                self._nn_index.fit(self._embeddings)  # type: ignore[union-attr]
                logger.info(
                    "NearestNeighbors ANN 索引构建完成：%d 条", len(self._doc_keys)
                )
            except Exception as e:
                logger.warning("NearestNeighbors 索引构建失败，将使用线性扫描: %s", e)
                self._nn_index = None
        else:
            self._nn_index = None

        duration = time.time() - self._init_progress["start_time"]
        self._init_progress["last_build_duration"] = duration
        try:
            os.makedirs("data", exist_ok=True)
            with open("data/vector_last_duration.json", "w", encoding="utf-8") as f:
                json.dump({"last_build_duration": duration}, f)
        except Exception:
            pass
        logger.info(
            "Embedding 索引构建完成: %d 条，耗时 %.2f 秒", len(self._doc_keys), duration
        )

    def search(self, query: str, limit: int = 8) -> list[tuple[str, float]]:
        """按语义相似度检索文档（优先使用 ANN 索引加速）。"""
        if not self._ready or self._embeddings is None:
            return []

        model = self._get_model()
        prefixed = BGE_QUERY_PREFIX + query
        q_vec = model.encode([prefixed], normalize_embeddings=True)
        q_vec = q_vec[0]  # shape (dim,)

        # 优先使用 NearestNeighbors ANN 索引
        if SKLEARN_AVAILABLE and self._nn_index is not None:
            try:
                import warnings

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    # NearestNeighbors 返回距离（越小越相似），需转换为相似度
                    distances, indices = self._nn_index.kneighbors(
                        q_vec.reshape(1, -1),
                        n_neighbors=min(limit * 2, len(self._doc_keys)),
                    )
                distances = distances[0]
                indices = indices[0]
                # cosine 距离转相似度：similarity = 1 - distance / 2
                scores = 1 - distances / 2
                results = []
                for idx, score in zip(indices.tolist(), scores.tolist()):
                    if score > MIN_SIMILARITY_SCORE:
                        results.append((self._doc_keys[idx], score))
                        if len(results) >= limit:
                            break
                return results
            except Exception as e:
                logger.warning("ANN 检索失败，回退到线性扫描: %s", e)
                # 回退到线性扫描

        # 尝试延迟重建 ANN 索引（向量已变更但未重建索引时）
        if SKLEARN_AVAILABLE and self._nn_index is None and len(self._doc_keys) > 0:
            try:
                assert NearestNeighbors is not None
                n_neighbors = min(
                    max(50, len(self._doc_keys) // 10), len(self._doc_keys)
                )
                self._nn_index = NearestNeighbors(  # type: ignore[misc]
                    n_neighbors=n_neighbors,
                    metric="cosine",
                    algorithm="auto",
                )
                self._nn_index.fit(self._embeddings)  # type: ignore[union-attr]
                logger.info("延迟重建 ANN 索引完成：%d 条", len(self._doc_keys))
                # 递归调用，使用新索引
                return self.search(query, limit)
            except Exception as e:
                logger.warning("延迟重建 ANN 索引失败: %s", e)

        # 线性扫描（使用 argpartition 优化 Top-K 选择）
        scores: np.ndarray = self._embeddings @ q_vec
        if len(scores) > limit:
            # 使用 argpartition 进行部分排序，均摊 O(n) 优于全量 sorted O(n log n)
            top_k_indices = np.argpartition(scores, -limit)[-limit:]
            top_k_indices = top_k_indices[np.argsort(scores[top_k_indices])[::-1]]
        else:
            top_k_indices = np.argsort(scores)[::-1]
        return [
            (self._doc_keys[i], float(scores[i]))
            for i in top_k_indices
            if scores[i] > MIN_SIMILARITY_SCORE
        ]

    async def upsert_one(self, key: str, vector: list[float]) -> None:
        """单条追加或原位替换向量。"""
        async with self._lock:
            new_vec = np.array(vector, dtype=np.float32)
            if key in self._doc_keys:
                index = self._doc_keys.index(key)
                if self._embeddings is not None:
                    self._embeddings[index] = new_vec
                logger.info("已通过内存原子替换增量更新单条向量: %s", key)
            else:
                self._doc_keys.append(key)
                if (
                    self._embeddings is None
                    or self._embeddings.size == 0
                    or len(self._embeddings.shape) < 2
                ):
                    self._embeddings = np.array([new_vec], dtype=np.float32)
                else:
                    self._embeddings = np.vstack([self._embeddings, new_vec])
                logger.info("已通过内存增量追加单条向量: %s", key)
            self._ready = True
            self._dirty = True
            self._nn_index = None  # 向量变更，使 ANN 索引失效
            self._save_event.set()

    async def delete_one(self, key: str) -> None:
        """单条物理删除向量。"""
        async with self._lock:
            if key in self._doc_keys:
                index = self._doc_keys.index(key)
                self._doc_keys.pop(index)
                if self._embeddings is not None:
                    self._embeddings = np.delete(self._embeddings, index, axis=0)
                logger.info("已从内存原子删除单条向量: %s", key)
                self._dirty = True
                self._nn_index = None  # 向量变更，使 ANN 索引失效
                self._save_event.set()
                if not self._doc_keys:
                    self._ready = False
                    self._embeddings = None

    async def save(self, path: str | Path) -> None:
        """将向量索引安全持久化到磁盘。"""
        from app.service.embedding_io import save_index

        await save_index(self, path)

    async def load(self, path: str | Path) -> None:
        """从磁盘加载缓存的向量索引。"""
        from app.service.embedding_io import load_index

        await load_index(self, path)

    @property
    def doc_count(self) -> int:
        return len(self._doc_keys)

    async def rebuild_from_db(self, index_dir: str | Path = "") -> None:
        """从数据库读取全部条目，并在后台线程全量重构向量索引并落盘。"""
        from app.service.embedding_rebuild import rebuild_from_db

        await rebuild_from_db(self, str(index_dir))
