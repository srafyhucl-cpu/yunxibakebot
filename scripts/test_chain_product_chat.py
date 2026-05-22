"""Phase C 全链路测试：客服消息（含商品 item_id）→ LLM Function Calling → 有赞 API → 商品数据三路回写。

运行前置：
  1. .env 中 YOUZAN_MOCK_MODE=False，Youzan 凭证已配置
  2. 本地服务已启动：uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
  3. 本地 DB 中 youzan_products 需至少有一条记录
"""

import asyncio
import json
import sys
import time
import hashlib
from pathlib import Path

import aiosqlite
import httpx

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import settings  # noqa: E402
from app.service.youzan.mock_emulator import YouzanMockEmulator  # noqa: E402

BASE_URL = "http://127.0.0.1:8000"
WEBHOOK_PATH = "/api/v1/webhook/youzan"
WAIT_MAX_SECONDS = 30
POLL_INTERVAL = 2
HTTP_OK = 200
_SENTINEL = "2000-01-02 00:00:00"

VS_JSON_PATH = ROOT_DIR / "data" / "embeddings.json"

_TEST_START: float = 0.0


def _ts() -> str:
    return f"T+{time.monotonic() - _TEST_START:.2f}s"


def _step(label: str) -> None:
    print(f"\n  [{_ts()}] ── {label}")


def _ok(label: str, detail: str = "") -> None:
    print(f"  [{_ts()}] ✅ PASS  {label}")
    if detail:
        print(f"              {detail}")


def _fail(label: str, detail: str = "") -> None:
    print(f"  [{_ts()}] ❌ FAIL  {label}")
    if detail:
        print(f"              {detail}")


def _info(msg: str) -> None:
    print(f"  [{_ts()}] ℹ  {msg}")


async def _get_test_item_id(db_path: str) -> int | None:
    """从本地 youzan_products 取一条在售商品 item_id。"""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT item_id FROM youzan_products WHERE is_active = 1 ORDER BY updated_at DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def _reset_timestamps(db_path: str, item_id: int) -> None:
    """将 youzan_products 和 knowledge_base 的 updated_at 都降到 2000 年。"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE youzan_products SET updated_at=? WHERE item_id=?",
            ("2000-01-01 00:00:00", item_id),
        )
        await db.execute(
            "UPDATE knowledge_base SET updated_at=? WHERE youzan_item_id=?",
            ("2000-01-01 00:00:00", str(item_id)),
        )
        await db.commit()


async def _poll_product_updated(db_path: str, item_id: int) -> dict | None:
    """轮询直到 youzan_products.updated_at 超过哨兵值，返回最新行。"""
    deadline = time.monotonic() + WAIT_MAX_SECONDS
    while time.monotonic() < deadline:
        await asyncio.sleep(POLL_INTERVAL)
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT item_id, title, price_fen, stock, updated_at "
                "FROM youzan_products WHERE item_id = ? AND updated_at > ?",
                (item_id, _SENTINEL),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        print(f"  [{_ts()}]   轮询中，等待 LLM + 有赞 API + DB 写入...", end="\r")
    return None


async def _fetch_knowledge(db_path: str, item_id: int) -> dict | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, updated_at FROM knowledge_base WHERE youzan_item_id = ?",
            (str(item_id),),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


def _snapshot_embeddings() -> tuple[float, set[str]]:
    if not VS_JSON_PATH.exists():
        return 0.0, set()
    mtime = VS_JSON_PATH.stat().st_mtime
    with open(VS_JSON_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)
    return mtime, set(meta.get("doc_keys", []))


def _build_chat_webhook(buyer_id: str, msg_id: str, content: str) -> tuple[bytes, str]:
    """
    构造有赞 B 轨买家客服消息 Webhook body + MD5 签名。
    B 轨特征：不带 'type' 字段（否则进入 A 轨系统事件路由）；
    使用 buyer_id + msg_type + content 结构。
    """
    payload = {
        "id": msg_id,
        "buyer_id": buyer_id,
        "msg_type": "text",
        "content": {"text": content},
        "kdt_id": settings.YOUZAN_KDT_ID,
        "client_id": settings.YOUZAN_CLIENT_ID,
        "timestamp": int(time.time()),
    }
    raw_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    signature = YouzanMockEmulator.calculate_signature(
        settings.YOUZAN_CLIENT_ID, settings.YOUZAN_CLIENT_SECRET, raw_body
    )
    return raw_body, signature


async def run_phase_c() -> bool:
    global _TEST_START
    _TEST_START = time.monotonic()

    print("\n" + "=" * 60)
    print("Phase C：客服消息（含商品 item_id）→ LLM get_product_info")
    print("         → 有赞 API → youzan_products + knowledge_base + 向量三路回写")
    print("=" * 60)
    print("  路径：PRODUCT_INQUIRY 意图 → _ai_conversation_loop → get_product_info(product_id=item_id)")
    print("        → _refresh_product_live → youzan.item.get → upsert_product + upsert_product_knowledge + vs.upsert_one")

    db_path = str(ROOT_DIR / settings.DB_PATH)

    # ── Setup ──────────────────────────────────────────────────────────────────
    _step("Setup：选取测试商品 item_id")
    item_id = await _get_test_item_id(db_path)
    if not item_id:
        _fail("youzan_products 中无在售商品")
        return False
    _info(f"item_id={item_id}")

    _step("重置 youzan_products + knowledge_base updated_at 到 2000 年")
    await _reset_timestamps(db_path, item_id)
    _info(f"item_id={item_id} 两张表 updated_at 已降至 2000-01-01")

    emb_mtime_base, _ = _snapshot_embeddings()
    test_start_ts = time.time()

    # ── 构造聊天消息，含明确 item_id ──────────────────────────────────────────
    _step("构造客服消息（商品咨询措辞，含明确 item_id）")
    buyer_id = f"test_phase_c_{int(time.monotonic() * 1000)}"
    msg_id = f"{buyer_id}_{int(time.time() * 1000)}"
    content = f"这个商品 {item_id} 现在还有货吗，帮我查一下最新库存和价格"
    _info(f"buyer_id={buyer_id}")
    _info(f"消息内容: '{content}'")

    raw_body, signature = _build_chat_webhook(buyer_id, msg_id, content)
    _info(f"signature={signature}")
    _info(f"POST {BASE_URL}{WEBHOOK_PATH}")

    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{BASE_URL}{WEBHOOK_PATH}",
            content=raw_body,
            headers={"Content-Type": "application/json", "event-sign": signature},
        )
    elapsed = time.monotonic() - t0

    if resp.status_code == HTTP_OK:
        _ok(f"Webhook 接收返回 200（往返 {elapsed:.2f}s）", f"body={resp.text}")
    else:
        _fail(f"Webhook 返回 {resp.status_code}", resp.text)
        return False

    # ── 轮询等待 ──────────────────────────────────────────────────────────────
    _step(f"轮询等待 LLM Function Calling → 有赞 API → 三路写入（最长 {WAIT_MAX_SECONDS}s）")
    _info("链路：意图识别 → _ai_conversation_loop → get_product_info → _refresh_product_live → upsert*3")

    updated_row = await _poll_product_updated(db_path, item_id)

    # ── 断言 youzan_products ──────────────────────────────────────────────────
    print()
    _step("断言 youzan_products 回写")
    prod_ok = updated_row is not None
    if prod_ok:
        _ok("youzan_products 有记录（updated_at 超过哨兵，证明本次 Function Calling 写入成功）")
        print(f"\n              {'字段':<22} {'值'}")
        print(f"              {'-' * 55}")
        for k, v in updated_row.items():
            print(f"              {k:<22} {v}")
    else:
        _fail(f"youzan_products 未在 {WAIT_MAX_SECONDS}s 内更新")
        return False

    # ── 断言 knowledge_base ───────────────────────────────────────────────────
    _step("断言 knowledge_base RAG 回写")
    kb = await _fetch_knowledge(db_path, item_id)
    kb_ok = kb is not None and kb["updated_at"] > _SENTINEL
    if kb_ok:
        _ok("knowledge_base 已更新", f"id={kb['id']}  updated_at={kb['updated_at']}")
    elif kb:
        _fail(f"knowledge_base 存在但 updated_at 未刷新（{kb['updated_at']} ≤ {_SENTINEL}）")
    else:
        _fail("knowledge_base 无对应条目")

    # ── 断言向量索引 ──────────────────────────────────────────────────────────
    _step("断言向量索引磁盘刷新（embeddings.json mtime + doc_keys）")
    emb_mtime_r1, emb_keys_r1 = _snapshot_embeddings()
    emb_ok = emb_mtime_r1 > test_start_ts
    if emb_ok:
        _ok("embeddings.json 已刷新落盘", f"mtime 进阶 +{emb_mtime_r1 - test_start_ts:.2f}s，doc_keys 共 {len(emb_keys_r1)} 条")
    else:
        _fail("embeddings.json 未刷新（periodic_save_task 尚未唤醒）")
    key_ok = str(item_id) in emb_keys_r1
    if key_ok:
        _ok("doc_keys 包含目标商品", f"item_id={item_id} 在向量矩阵中（共 {len(emb_keys_r1)} 条）")
    else:
        _fail(f"doc_keys 未找到 item_id={item_id}")

    passed = prod_ok and kb_ok and emb_ok and key_ok
    return passed


if __name__ == "__main__":
    result = asyncio.run(run_phase_c())
    elapsed = time.monotonic() - _TEST_START
    print(f"\n{'✅ Phase C 通过' if result else '❌ Phase C 失败'}  总耗时 {elapsed:.1f}s\n")
    sys.exit(0 if result else 1)
