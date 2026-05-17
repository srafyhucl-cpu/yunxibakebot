"""调试向量搜索"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.service.vector_search import VectorSearcher

vs = VectorSearcher()
vs.load("data/vectors.pkl")

# 检查查询的 n-gram
query = "提拉米苏多少钱"
q_ngrams = vs._extract_ngrams(query)
q_set = set(q_ngrams)

print(f"查询 '{query}'")
print(f"  n-grams 总数: {len(q_set)}")
print(f"  在词汇表中: {len([ng for ng in q_set if ng in vs._vocab])} / {len(q_set)}")
print(f"  缺失的: {[ng for ng in q_set if ng not in vs._vocab][:10]}")

# 检查一个应该在的文档
for doc_key in vs._doc_keys:
    if "提拉米苏" in doc_key:
        break
if doc_key:
    d_ngrams = set(vs._extract_ngrams(doc_key))
    shared = q_set & d_ngrams
    print(f"\n文档 '{doc_key}'")
    print(f"  n-grams 总数: {len(d_ngrams)}")
    print(f"  共享 n-grams: {len(shared)} 个: {sorted(shared)}")
    for ng in shared:
        print(f"    '{ng}' -> 词表ID={vs._vocab.get(ng)}, IDF={vs._idf[vs._vocab[ng]]}")

# 手动算 cosine 看看
q_vec = [0.0] * len(vs._vocab)
import math
from collections import Counter
q_counts = Counter(q_ngrams)
for ng, cnt in q_counts.items():
    idx = vs._vocab.get(ng)
    if idx is not None:
        q_vec[idx] = math.log(1+cnt) * vs._idf[idx]
q_norm = math.sqrt(sum(v*v for v in q_vec)) or 1.0
q_vec = [v/q_norm for v in q_vec]

# 找这个文档的向量
for i, key in enumerate(vs._doc_keys):
    if key == doc_key:
        d_vec = vs._doc_vectors[i]
        sim = sum(a*b for a,b in zip(q_vec, d_vec))
        print(f"\ncosine similarity: {sim:.6f}")
        print(f"  查询向量非零特征: {sum(1 for v in q_vec if v>0)}")
        print(f"  文档向量非零特征: {sum(1 for v in d_vec if v>0)}")
        break
