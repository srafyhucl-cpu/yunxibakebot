from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path
from types import ModuleType


def load_eval_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "eval_retrieval.py"
    spec = importlib.util.spec_from_file_location("eval_retrieval", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_db_path_prefers_explicit_path(tmp_path: Path) -> None:
    eval_retrieval = load_eval_module()
    explicit_db = tmp_path / "custom.db"

    assert eval_retrieval.resolve_db_path(str(explicit_db)) == explicit_db


def test_resolve_db_path_falls_back_to_local_raw_snapshot(
    tmp_path: Path, capsys
) -> None:
    eval_retrieval = load_eval_module()
    default_db = tmp_path / "eval.db"
    raw_db = tmp_path / "bot_raw.db"
    raw_db.write_text("", encoding="utf-8")
    eval_retrieval.DEFAULT_EVALUATION_DB = default_db
    eval_retrieval.LOCAL_RAW_SNAPSHOT_DB = raw_db

    assert eval_retrieval.resolve_db_path("") == raw_db
    assert "bot_raw.db" in capsys.readouterr().err


def test_load_corpus_builds_stable_keys(tmp_path: Path) -> None:
    eval_retrieval = load_eval_module()
    db_path = tmp_path / "eval.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE knowledge_base ("
        "id INTEGER, youzan_item_id TEXT, title TEXT, content TEXT, is_active INTEGER)"
    )
    conn.executemany(
        "INSERT INTO knowledge_base VALUES (?, ?, ?, ?, ?)",
        [
            (1, "1001", "提拉米苏", "经典蛋糕", 1),
            (2, None, "配送规则", "同城配送", 1),
            (3, "1003", "下架商品", "不可售", 0),
        ],
    )
    conn.commit()
    conn.close()

    assert eval_retrieval.load_corpus(db_path) == [
        ("1001", "提拉米苏", "经典蛋糕"),
        ("kb_2", "配送规则", "同城配送"),
    ]


def test_evaluate_calculates_recall_mrr_and_no_gold() -> None:
    eval_retrieval = load_eval_module()

    class StubSearcher:
        def search(self, query: str, limit: int) -> list[tuple[str, float]]:
            results = {
                "命中第二名": [("miss", 0.9), ("p1", 0.8)],
                "未命中": [("miss", 0.9)],
                "无目标": [("p1", 0.8)],
            }
            return results[query][:limit]

    cases = [
        {"id": "hit", "query": "命中第二名", "relevant": [["提拉米苏"]]},
        {"id": "miss", "query": "未命中", "relevant": [["草莓"]]},
        {"id": "no-gold", "query": "无目标", "relevant": [["马卡龙"]]},
    ]
    corpus = [("p1", "提拉米苏", "经典蛋糕"), ("p2", "草莓蛋糕", "当季限定")]

    summary = eval_retrieval.evaluate(cases, corpus, StubSearcher(), k=2)

    assert summary["evaluable"] == 2
    assert summary["no_gold"] == 1
    assert summary["recall_at_k"] == 0.5
    assert summary["mrr"] == 0.25
