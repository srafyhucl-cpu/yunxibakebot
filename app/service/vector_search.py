"""
轻量 TF-IDF 向量搜索引擎。

使用字符 n-gram + TF-IDF + cosine similarity 实现语义检索，
零 API 成本、零外部依赖。

原理：
1. 对所有知识条目做 2-gram / 3-gram 切分
2. 计算 TF（词频）和 IDF（逆文档频率）
3. 查询时对查询文本同样做 n-gram 切分
4. cosine similarity 匹配最相似的文档

支持增量追加：add_documents() 可以实时加入新文档。
"""

import math
import pickle
from pathlib import Path
from collections import Counter


class VectorSearcher:
    """TF-IDF 向量搜索：构建词汇表、向量、cosine 检索。"""

    def __init__(self, ngram_min: int = 2, ngram_max: int = 3) -> None:
        self._n_min = ngram_min
        self._n_max = ngram_max
        self._vocab: dict[str, int] = {}       # ngram → feature_id
        self._idf: list[float] = []             # feature_id → idf
        self._doc_vectors: list[list[float]] = []
        self._doc_keys: list[str] = []
        self._ready = False

    # ── 构建与增删 ──

    def build(self, documents: list[tuple[str, str]]) -> None:
        """
        全量构建索引。

        参数：
            documents: [(唯一标识, 文本内容), ...]
        """
        self._vocab = {}
        self._idf = []
        self._doc_vectors = []
        self._doc_keys = []

        # 第一遍：收集 n-gram 建立词汇表（title + content 一起索引）
        doc_ngrams: list[dict[int, int]] = []
        for key, text in documents:
            self._doc_keys.append(key)
            # 关键: 标题和内容一起做 n-gram，确保产品名也能被搜到
            full_text = f"{key} {text}"
            counts = Counter(self._extract_ngrams(full_text))
            doc_ngrams.append(counts)
            for ng in counts:
                if ng not in self._vocab:
                    self._vocab[ng] = len(self._vocab)

        n_feats = len(self._vocab)
        n_docs = len(documents)

        # 第二遍：计算 IDF（逆文档频率）
        self._idf = [0.0] * n_feats
        for ng, idx in self._vocab.items():
            doc_freq = sum(1 for d in doc_ngrams if ng in d)
            self._idf[idx] = math.log((n_docs + 1) / (doc_freq + 1)) + 1.0

        # 第三遍：构建每个文档的 TF-IDF 向量并 L2 归一化
        for counts in doc_ngrams:
            vec = [0.0] * n_feats
            for ng, cnt in counts.items():
                idx = self._vocab.get(ng)
                if idx is not None:
                    tf = math.log(1 + cnt)
                    vec[idx] = tf * self._idf[idx]
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            self._doc_vectors.append([v / norm for v in vec])

        self._ready = True

    def add_documents(self, new_docs: list[tuple[str, str]]) -> None:
        """
        增量追加新文档，更新 IDF 和增强向量。

        参数：
            new_docs: [(唯一标识, 文本内容), ...]
        """
        if not self._ready:
            self.build(new_docs)
            return

        # 收集新文档的 n-gram
        new_ngrams: list[Counter] = []
        for key, text in new_docs:
            self._doc_keys.append(key)
            full_text = f"{key} {text}"
            counts = Counter(self._extract_ngrams(full_text))
            new_ngrams.append(counts)
            for ng in counts:
                if ng not in self._vocab:
                    self._vocab[ng] = len(self._vocab)

        # 如果词汇表增长了，需要扩展所有已存向量
        n_feats = len(self._vocab)
        if n_feats > len(self._idf):
            self._idf.extend([0.0] * (n_feats - len(self._idf)))
            for vec in self._doc_vectors:
                vec.extend([0.0] * (n_feats - len(vec)))

        n_docs = len(self._doc_keys)

        # 重算受影响的 IDF
        all_doc_ngrams = [Counter(self._extract_ngrams(self._doc_keys[i])) for i in range(n_docs)]
        for ng, idx in self._vocab.items():
            doc_freq = sum(1 for d in all_doc_ngrams if ng in d)
            self._idf[idx] = math.log((n_docs + 1) / (doc_freq + 1)) + 1.0

        # 重建所有向量
        self._doc_vectors = []
        for i in range(n_docs):
            counts = all_doc_ngrams[i]
            vec = [0.0] * n_feats
            for ng, cnt in counts.items():
                idx = self._vocab.get(ng)
                if idx is not None:
                    tf = math.log(1 + cnt)
                    vec[idx] = tf * self._idf[idx]
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            self._doc_vectors.append([v / norm for v in vec])

    # ── 检索 ──

    def search(self, query: str, limit: int = 8) -> list[tuple[str, float]]:
        """
        Cosine 相似度检索。

        参数：
            query: 用户查询文本
            limit: 返回最大条数
        返回：
            [(文档 key, similarity), ...] 降序排列
        """
        if not self._ready or not self._doc_vectors:
            return []

        q_counts = Counter(self._extract_ngrams(query))
        n_feats = len(self._vocab)
        q_vec = [0.0] * n_feats

        for ng, cnt in q_counts.items():
            idx = self._vocab.get(ng)
            if idx is not None:
                tf = math.log(1 + cnt)
                q_vec[idx] = tf * self._idf[idx]

        norm = math.sqrt(sum(v * v for v in q_vec)) or 1.0
        q_vec = [v / norm for v in q_vec]

        scored: list[tuple[int, float]] = []
        for i, dv in enumerate(self._doc_vectors):
            sim = sum(a * b for a, b in zip(q_vec, dv))
            if sim > 0:
                scored.append((i, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [(self._doc_keys[i], s) for i, s in scored[:limit]]

    # ── 持久化 ──

    def save(self, path: str | Path) -> None:
        data = (self._vocab, self._idf, self._doc_vectors, self._doc_keys, self._ready)
        with open(path, "wb") as f:
            pickle.dump(data, f)

    def load(self, path: str | Path) -> None:
        with open(path, "rb") as f:
            self._vocab, self._idf, self._doc_vectors, self._doc_keys, self._ready = pickle.load(f)

    # ── 内部 ──

    def _extract_ngrams(self, text: str) -> list[str]:
        chars = list(text)
        ngrams: list[str] = []
        for n in range(self._n_min, self._n_max + 1):
            for i in range(len(chars) - n + 1):
                ngrams.append("".join(chars[i:i + n]))
        return ngrams

    @property
    def doc_count(self) -> int:
        return len(self._doc_keys)
