"""
基于 Sentence-Transformers 的语义向量搜索引擎。

使用 BAAI/bge-small-zh-v1.5 模型替代 TF-IDF，提升中文语义检索质量。
为 KnowledgeRetriever 提供语义检索能力。

检索原理：
1. build() 时批量编码所有知识条目为稠密向量，L2 归一化后缓存
2. search() 时编码查询（附 BGE 检索指令前缀），与文档向量点积得 cosine 相似度
3. 返回 Top-K 最相关条目，消除 TF-IDF 对同义词/指代词的盲区
"""

import pickle
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from app.logger import setup_logger

logger = setup_logger()

EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
BGE_QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："
MIN_SIMILARITY_SCORE = 0.0


class EmbeddingSearcher:
    """Sentence-Transformers 语义向量搜索，为 KnowledgeRetriever 提供层。"""

    def __init__(self) -> None:
        self._model: SentenceTransformer | None = None
        self._embeddings: np.ndarray | None = None
        self._doc_keys: list[str] = []
        self._ready: bool = False

    def _get_model(self) -> SentenceTransformer:
        """懒加载：首次调用时初始化模型（避免冷启动阻塞）。"""
        if self._model is None:
            self._model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("Embedding 模型已加载: %s", EMBEDDING_MODEL)
        return self._model

    def build(self, documents: list[tuple[str, str]]) -> None:
        """
        全量构建语义向量索引。

        参数：
            documents: [(标题, 内容), ...] — 与 KnowledgeRepo.get_all_titles() 返回格式一致
        """
        model = self._get_model()
        self._doc_keys = []
        texts: list[str] = []
        for key, content in documents:
            self._doc_keys.append(key)
            texts.append(f"{key} {content}")

        raw = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        self._embeddings = np.array(raw, dtype=np.float32)
        self._ready = True
        logger.info("Embedding 索引构建完成: %d 条", len(self._doc_keys))

    def search(self, query: str, limit: int = 8) -> list[tuple[str, float]]:
        """
        语义相似度检索。

        参数：
            query: 用户查询文本
            limit: 返回最大条数
        返回：
            [(文档 key, cosine_similarity), ...] 降序排列
        """
        if not self._ready or self._embeddings is None:
            return []
        model = self._get_model()
        prefixed = BGE_QUERY_PREFIX + query
        q_vec = model.encode([prefixed], normalize_embeddings=True)[0]
        scores: list[float] = (self._embeddings @ q_vec).tolist()
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [
            (self._doc_keys[i], s)
            for i, s in ranked[:limit]
            if s > MIN_SIMILARITY_SCORE
        ]

    def save(self, path: str | Path) -> None:
        """持久化向量索引到磁盘。"""
        try:
            data = (self._doc_keys, self._embeddings, self._ready)
            with open(path, "wb") as f:
                pickle.dump(data, f)
        except (OSError, pickle.PicklingError) as exc:
            logger.error("向量索引保存失败: %s", exc)

    def load(self, path: str | Path) -> None:
        """从磁盘加载已缓存的向量索引（跳过模型推理）。"""
        try:
            with open(path, "rb") as f:
                self._doc_keys, self._embeddings, self._ready = pickle.load(f)
            logger.info("Embedding 索引已从缓存加载: %d 条", len(self._doc_keys))
        except (OSError, pickle.UnpicklingError) as exc:
            logger.warning("向量索引加载失败，将重新构建: %s", exc)
            self._ready = False

    @property
    def doc_count(self) -> int:
        return len(self._doc_keys)
