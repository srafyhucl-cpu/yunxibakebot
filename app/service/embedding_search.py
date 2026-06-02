from __future__ import annotations

"""
基于 Sentence-Transformers 的语义向量搜索引擎。

使用 BAAI/bge-small-zh-v1.5 模型替代 TF-IDF，提升中文语义检索质量，
为 KnowledgeRetriever 提供语义搜索能力。

检索原理：
1. build() 时批量编码所有知识条目为稠密向量，并在内存中缓存
2. search() 时编码查询文本，与文档向量做 cosine 相似度计算
3. 返回 Top-K 最相关条目，减少 TF-IDF 对同义表达的遗漏
"""

import asyncio
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from app.logger import setup_logger

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = setup_logger()

EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
BGE_QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："
MIN_SIMILARITY_SCORE = 0.35


class _FallbackSentenceTransformer:
    """测试环境使用的轻量编码器，避免特定解释器下真实模型加载崩溃。"""

    def encode(
        self,
        texts: list[str],
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
    ) -> np.ndarray:
        del show_progress_bar
        rows: list[np.ndarray] = []
        for text in texts:
            vector = np.zeros(256, dtype=np.float32)
            for index, char in enumerate(text):
                bucket = (ord(char) + index * 131) % 256
                vector[bucket] += 1.0
            if normalize_embeddings:
                norm = np.linalg.norm(vector)
                if norm > 0:
                    vector = vector / norm
            rows.append(vector)
        if not rows:
            return np.zeros((0, 256), dtype=np.float32)
        return np.vstack(rows)


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
                    self._init_progress["last_build_duration"] = json.load(f).get("last_build_duration", 0.0)
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

    def build(self, documents: list[tuple[str, str, str]], current_db_md5: str = "") -> None:
        """全量构建语义向量索引并分批更新进度。"""
        import time
        model = self._get_model()
        self._doc_keys = []
        texts: list[str] = []
        for doc_key, title, content in documents:
            self._doc_keys.append(str(doc_key))
            texts.append(f"{title} {content}")

        total_docs = len(texts)
        self._init_progress.update({
            "status": "building",
            "total": total_docs,
            "current": 0,
            "start_time": time.time(),
            "elapsed": 0.0,
        })

        all_embeddings = []
        batch_size = 16
        for i in range(0, total_docs, batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_raw = model.encode(batch_texts, normalize_embeddings=True, show_progress_bar=False)
            all_embeddings.append(batch_raw)
            self._init_progress["current"] = min(i + batch_size, total_docs)
            self._init_progress["elapsed"] = time.time() - self._init_progress["start_time"]

        self._embeddings = np.vstack(all_embeddings) if all_embeddings else np.zeros((0, 256), dtype=np.float32)
        self._ready = True
        self._dirty = True
        self._data_hash = current_db_md5
        self._init_progress["status"] = "ready"

        duration = time.time() - self._init_progress["start_time"]
        self._init_progress["last_build_duration"] = duration
        try:
            os.makedirs("data", exist_ok=True)
            with open("data/vector_last_duration.json", "w", encoding="utf-8") as f:
                json.dump({"last_build_duration": duration}, f)
        except Exception:
            pass
        logger.info("Embedding 索引构建完成: %d 条，耗时 %.2f 秒", len(self._doc_keys), duration)

    def search(self, query: str, limit: int = 8) -> list[tuple[str, float]]:
        """按语义相似度检索文档。"""
        if not self._ready or self._embeddings is None:
            return []

        model = self._get_model()
        prefixed = BGE_QUERY_PREFIX + query
        q_vec = model.encode([prefixed], normalize_embeddings=True)[0]
        scores: list[float] = (self._embeddings @ q_vec).tolist()
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
        return [
            (self._doc_keys[index], score)
            for index, score in ranked[:limit]
            if score > MIN_SIMILARITY_SCORE
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
                if self._embeddings is None or self._embeddings.size == 0 or len(self._embeddings.shape) < 2:
                    self._embeddings = np.array([new_vec], dtype=np.float32)
                else:
                    self._embeddings = np.vstack([self._embeddings, new_vec])
                logger.info("已通过内存增量追加单条向量: %s", key)
            self._ready = True
            self._dirty = True
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
                self._save_event.set()
                if not self._doc_keys:
                    self._ready = False
                    self._embeddings = None

    async def save(self, path: str | Path) -> None:
        """将向量索引安全持久化到磁盘。"""
        if not self._dirty:
            logger.debug("向量索引未发生变更，跳过磁盘写入")
            return

        async with self._lock:
            try:
                path = Path(path)
                npy_path = path.with_suffix(".npy")
                json_path = path.with_suffix(".json")
                tmp_npy = npy_path.with_suffix(".tmp.npy")
                tmp_json = json_path.with_suffix(".json.tmp")

                if self._embeddings is not None:
                    np.save(tmp_npy, self._embeddings)
                else:
                    np.save(tmp_npy, np.array([], dtype=np.float32))

                meta = {
                    "doc_keys": self._doc_keys,
                    "ready": self._ready,
                    "data_hash": self._data_hash,
                }
                with open(tmp_json, "w", encoding="utf-8") as file_obj:
                    json.dump(meta, file_obj, ensure_ascii=False, indent=2)

                if tmp_npy.exists():
                    os.replace(str(tmp_npy), str(npy_path))
                if tmp_json.exists():
                    os.replace(str(tmp_json), str(json_path))

                self._dirty = False
                logger.info("已安全持久化向量索引: %d 条", len(self._doc_keys))
            except Exception as exc:
                logger.error("向量索引保存失败: %s", exc)

    async def load(self, path: str | Path) -> None:
        """从磁盘加载缓存的向量索引。"""
        self._init_progress["status"] = "loading"
        async with self._lock:
            try:
                path = Path(path)
                npy_path = path.with_suffix(".npy")
                json_path = path.with_suffix(".json")

                if not npy_path.exists() or not json_path.exists():
                    logger.warning("向量索引缓存文件不存在，将重新构建")
                    self._ready = False
                    return

                with open(json_path, "r", encoding="utf-8") as file_obj:
                    meta = json.load(file_obj)

                self._doc_keys = meta["doc_keys"]
                self._ready = meta["ready"]
                self._data_hash = meta.get("data_hash", "")
                self._embeddings = np.load(npy_path)
                if self._embeddings.size == 0:
                    self._embeddings = None

                self._dirty = False
                self._init_progress["status"] = "ready"
                logger.info("Embedding 索引已从缓存加载: %d 条", len(self._doc_keys))
            except Exception as exc:
                logger.warning("向量索引加载失败，将重新构建: %s", exc)
                self._ready = False

    @property
    def doc_count(self) -> int:
        return len(self._doc_keys)

    async def rebuild_from_db(self, index_dir: str | Path = "") -> None:
        """从数据库读取全部条目，并在后台线程全量重构向量索引并落盘。"""
        self._init_progress["status"] = "loading"
        try:
            from app.database import db_session_scope
            from app.repository.knowledge_repo import KnowledgeRepo
            import hashlib

            async with db_session_scope():
                repo = KnowledgeRepo(None)
                docs = await repo.get_all_titles_with_keys()
                
                sorted_docs = sorted(docs, key=lambda x: x[0])
                concat_text = "".join(f"{d[1]}{d[2]}" for d in sorted_docs)
                current_db_md5 = hashlib.md5(concat_text.encode("utf-8")).hexdigest()
                
                logger.info("后台自愈：开始从数据库全量重构向量索引...")
                await asyncio.to_thread(self.build, docs, current_db_md5)
                
                if index_dir:
                    await self.save(index_dir)
                logger.info("后台自愈：向量索引自愈重构并落盘完成")
        except Exception as exc:
            self._init_progress["status"] = "failed"
            logger.error("后台自愈：异步向量自愈重构遭遇严重异常: %s", exc)
