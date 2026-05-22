"""Phase B 全链路测试：商品系统事件 Webhook → 有赞 API → DB + RAG + 埋点写入（含幂等验证）。

运行前置：
  1. .env 中 YOUZAN_MOCK_MODE=False，Youzan 凭证已配置
  2. 本地服务已启动：uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
  3. 本地 DB 中 youzan_products 需至少有一条记录
"""

import asyncio
import json
import sys
import time
import urllib.parse
from pathlib import Path

import aiosqlite
import httpx

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import settings  # noqa: E402
from app.service.youzan.mock_emulator import YouzanMockEmulator  # noqa: E402

BASE_URL = "http://127.0.0.1:8000"
WEBHOOK_PATH = "/api/v1/webhook/youzan"
WAIT_SECONDS = 6
HTTP_OK = 200


async def _get_test_item_id(db_path: str) -> int | None:
    """从本地 youzan_products 取一条在售商品 item_id。"""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT item_id FROM youzan_products WHERE is_active = 1 ORDER BY updated_at DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def _snapshot_product(db_path: str, item_id: int) -> dict | None:
    """读取商品当前快照（updated_at）。"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT item_id, title, updated_at, is_active FROM youzan_products WHERE item_id = ?",
            (item_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def _count_analytics(db_path: str, item_id: int) -> int:
    """统计 analytics_events 中与该商品相关的 price_sync / stock_alert 埋点数。"""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM analytics_events WHERE event_type IN ('price_sync','stock_alert') AND ref_id = ?",
            (str(item_id),),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def _check_knowledge(db_path: str, item_id: int) -> bool:
    """确认 knowledge_base 中存在该商品的知识条目。"""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM knowledge_base WHERE youzan_item_id = ?",
            (str(item_id),),
        ) as cursor:
            row = await cursor.fetchone()
            return (row[0] if row else 0) > 0


def _build_system_event_body(item_id: int) -> tuple[bytes, str]:
    """构造 item_ItemUpdate 系统事件 Webhook body 并计算 MD5 签名。"""
    msg_obj = {"item_id": item_id}
    msg_encoded = urllib.parse.quote(json.dumps(msg_obj, ensure_ascii=False))
    payload = {
        "id": str(int(time.time() * 1000)),
        "type": "item_ItemUpdate",
        "kdt_id": settings.YOUZAN_KDT_ID,
        "msg": msg_encoded,
        "client_id": settings.YOUZAN_CLIENT_ID,
        "timestamp": int(time.time()),
        "version": "1.0",
    }
    raw_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    signature = YouzanMockEmulator.calculate_signature(
        settings.YOUZAN_CLIENT_ID, settings.YOUZAN_CLIENT_SECRET, raw_body
    )
    return raw_body, signature


def _print_result(name: str, passed: bool, detail: str = "") -> None:
    mark = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {mark}  {name}")
    if detail:
        print(f"         {detail}")


async def _post_event(raw_body: bytes, signature: str) -> int:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{BASE_URL}{WEBHOOK_PATH}",
            content=raw_body,
            headers={"Content-Type": "application/json", "event-sign": signature},
        )
    return response.status_code


async def run_phase_b() -> bool:
    print("\n=== Phase B：商品系统事件 Webhook → DB + RAG + 埋点（含幂等验证）===\n")

    db_path = str(ROOT_DIR / settings.DB_PATH)

    # 1. 选取测试商品
    item_id = await _get_test_item_id(db_path)
    if not item_id:
        print("  ❌ youzan_products 中无在售商品，请先同步商品数据")
        return False
    print(f"  [Setup] 测试商品 item_id={item_id}")

    # 2. 基线快照
    snapshot_before = await _snapshot_product(db_path, item_id)
    analytics_before = await _count_analytics(db_path, item_id)
    print(f"  [基线] updated_at={snapshot_before['updated_at'] if snapshot_before else 'N/A'}")
    print(f"  [基线] analytics_events(price_sync/stock_alert)={analytics_before}")

    # ── Run 1 ──────────────────────────────────────────────────────────────────
    print(f"\n  ── Run 1（首次推送，期望触发同步与埋点）──")
    raw_body, sig = _build_system_event_body(item_id)
    status = await _post_event(raw_body, sig)
    _print_result("Webhook 接收返回 200", status == HTTP_OK, f"status={status}")
    if status != HTTP_OK:
        return False

    print(f"  [等待] {WAIT_SECONDS}s（有赞 API + DB 写入）...")
    await asyncio.sleep(WAIT_SECONDS)

    snapshot_run1 = await _snapshot_product(db_path, item_id)
    analytics_run1 = await _count_analytics(db_path, item_id)
    knowledge_exists = await _check_knowledge(db_path, item_id)

    updated = (
        snapshot_run1 is not None
        and (
            snapshot_before is None
            or snapshot_run1["updated_at"] >= snapshot_before["updated_at"]
        )
    )
    _print_result(
        "youzan_products.updated_at 已更新",
        updated,
        f"before={snapshot_before['updated_at'] if snapshot_before else 'N/A'}  after={snapshot_run1['updated_at'] if snapshot_run1 else 'N/A'}",
    )
    _print_result(
        "knowledge_base 有该商品条目",
        knowledge_exists,
        f"item_id={item_id}",
    )
    analytics_increased = analytics_run1 >= analytics_before
    _print_result(
        f"analytics_events 数量 ≥ 基线（{analytics_before} → {analytics_run1}）",
        analytics_increased,
        "price_sync / stock_alert 至少持平",
    )

    # ── Run 2（幂等验证）──────────────────────────────────────────────────────
    print(f"\n  ── Run 2（重复推送，期望 analytics 无新增——幂等验证）──")
    raw_body2, sig2 = _build_system_event_body(item_id)
    status2 = await _post_event(raw_body2, sig2)
    _print_result("Run 2 Webhook 接收返回 200", status2 == HTTP_OK, f"status={status2}")

    print(f"  [等待] {WAIT_SECONDS}s...")
    await asyncio.sleep(WAIT_SECONDS)

    analytics_run2 = await _count_analytics(db_path, item_id)
    idempotent = analytics_run2 == analytics_run1
    _print_result(
        f"Run 2 analytics_events 无新增（{analytics_run1} → {analytics_run2}）",
        idempotent,
        "幂等验证",
    )

    passed = updated and knowledge_exists and analytics_increased and (status == HTTP_OK) and (status2 == HTTP_OK)
    return passed


if __name__ == "__main__":
    result = asyncio.run(run_phase_b())
    print(f"\n{'✅ Phase B 通过' if result else '❌ Phase B 失败'}\n")
    sys.exit(0 if result else 1)
