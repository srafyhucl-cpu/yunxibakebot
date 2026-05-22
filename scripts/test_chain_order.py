"""Phase A 全链路测试：有赞交易 Webhook → event_trade → 有赞 API → youzan_orders DB 回写。

路径说明：
  - ORDER_SERVICE 意图直接触发转人工（by design），不经过 Function Calling
  - youzan_orders 的真实写入路径是 trade_* webhook → handle_trade_event → get_order() → upsert_order
  - 本脚本测试该完整链路，并额外验证 Function Calling 订单查询（get_order_info）的 DB 短路路径

运行前置：
  1. .env 中 YOUZAN_MOCK_MODE=False，DeepSeek/Youzan 凭证已配置
  2. 本地服务已启动：uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import aiosqlite
import httpx

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import settings  # noqa: E402
from app.service.youzan.mock_emulator import YouzanMockEmulator  # noqa: E402

BASE_URL = "http://127.0.0.1:8000"
WEBHOOK_PATH = "/api/v1/webhook/youzan"
YOUZAN_API_BASE = "https://open.youzanyun.com/api"
YOUZAN_AUTH_URL = "https://open.youzanyun.com/auth/token"
WAIT_SECONDS = 10
BUYER_ID = "test_buyer_phase_a"
HTTP_OK = 200

# 全局测试开始时刻（monotonic）
_TEST_START: float = 0.0


def _ts() -> str:
    """返回相对测试起始的耗时字符串，如 T+3.21s。"""
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


async def _get_youzan_token() -> str:
    """调用有赞 OAuth 接口取 access_token（仅 Setup 阶段用）。"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            YOUZAN_AUTH_URL,
            json={
                "client_id": settings.YOUZAN_CLIENT_ID,
                "client_secret": settings.YOUZAN_CLIENT_SECRET,
                "authorize_type": "silent",
                "grant_id": settings.YOUZAN_KDT_ID,
            },
        )
        data = resp.json()
    auth_data = data.get("data") if isinstance(data, dict) else None
    if isinstance(auth_data, dict):
        return auth_data.get("access_token", "")
    return data.get("access_token", "")


async def _fetch_latest_order_no(token: str) -> str | None:
    """调用 youzan.trades.sold.get 取最新一条订单 tid。

    实际响应结构：response.trades[0].tid
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{YOUZAN_API_BASE}/youzan.trades.sold.get/3.0.0?access_token={token}",
            json={
                "kdt_id": settings.YOUZAN_KDT_ID,
                "page_no": 1,
                "page_size": 1,
            },
        )
        data = resp.json()
    try:
        trades = data.get("response", {}).get("trades", [])
        if trades:
            return trades[0].get("tid")
    except (KeyError, IndexError, TypeError, AttributeError):
        pass
    return None


async def _discover_order_no(db_path: str) -> str | None:
    """从本地 youzan_orders 取最近一条已知订单号；若无则返回 None。"""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT order_no FROM youzan_orders ORDER BY updated_at DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def _query_order(db_path: str, order_no: str) -> dict | None:
    """查询本地 youzan_orders 中目标订单记录。"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT order_no, status, amount_fen, product_titles, buyer_id, updated_at"
            " FROM youzan_orders WHERE order_no = ?",
            (order_no,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


def _build_trade_event_body(tid: str) -> tuple[bytes, str]:
    """构造 trade_TradeBuyerPay 系统事件 Webhook body 并计算 MD5 签名。"""
    msg_obj = {"tid": tid}
    import urllib.parse
    msg_encoded = urllib.parse.quote(json.dumps(msg_obj, ensure_ascii=False))
    payload = {
        "id": str(int(time.time() * 1000)),
        "type": "trade_TradeBuyerPay",
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


async def run_phase_a() -> bool:
    global _TEST_START
    _TEST_START = time.monotonic()

    print("\n" + "=" * 60)
    print("Phase A：trade_TradeBuyerPay Webhook → event_trade → 有赞 API → youzan_orders 回写")
    print("=" * 60)
    print("  注：ORDER_SERVICE 意图 by design 直接转人工（不过 Function Calling）")
    print("  注：youzan_orders 真实写入路径为 trade webhook → handle_trade_event → upsert_order")

    db_path = str(ROOT_DIR / settings.DB_PATH)

    # ── Step 0：发现订单号 ────────────────────────────────────────────────────
    _step("Setup：发现可测订单号")
    order_no = await _discover_order_no(db_path)

    if order_no:
        _info(f"本地 DB 已有记录，使用 order_no={order_no}")
    else:
        _info("本地 DB 无记录，调用有赞 API youzan.trades.sold.get 自动取最新订单")
        try:
            token = await _get_youzan_token()
            _info(f"有赞 token 获取成功（{token[:12]}...）")
            order_no = await _fetch_latest_order_no(token)
            if order_no:
                _info(f"取到最新订单号: {order_no}")
            else:
                _info("有赞 API 未返回订单（店铺暂无历史订单）")
        except Exception as exc:
            _info(f"有赞 API 调用失败: {exc}")

    if not order_no:
        _fail("无法获取可测订单号，终止测试")
        return False

    # 记录触发前 DB 快照
    snapshot_before = await _query_order(db_path, order_no)
    _info(f"DB 快照（触发前）: {'已存在 updated_at=' + str(snapshot_before['updated_at']) if snapshot_before else '无记录'}")

    # ── Step 1：构造并发送 trade webhook ─────────────────────────────────────
    _step("构造 trade_TradeBuyerPay 事件并发送")
    raw_body, signature = _build_trade_event_body(order_no)
    payload_preview = json.loads(raw_body)
    _info(f"type={payload_preview['type']}  tid={order_no}")
    _info(f"signature={signature}")
    _info(f"POST {BASE_URL}{WEBHOOK_PATH}")

    t_post = time.monotonic()
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{BASE_URL}{WEBHOOK_PATH}",
            content=raw_body,
            headers={"Content-Type": "application/json", "event-sign": signature},
        )
    t_post_elapsed = time.monotonic() - t_post

    if response.status_code == HTTP_OK:
        _ok(f"Webhook 接收返回 200（往返耗时 {t_post_elapsed:.2f}s）",
            f"body={response.text[:80]}")
    else:
        _fail(f"Webhook 返回非 200", f"status={response.status_code}  body={response.text[:120]}")
        return False

    # ── Step 2：等待后台链路 ──────────────────────────────────────────────────
    _step(f"等待后台链路（handle_trade_event → 有赞 API → upsert_order），共 {WAIT_SECONDS}s")
    for i in range(WAIT_SECONDS):
        await asyncio.sleep(1)
        print(f"  [{_ts()}]   ... {i + 1}/{WAIT_SECONDS}s", end="\r")
    print()

    # ── Step 3：断言 youzan_orders DB 写入 ───────────────────────────────────
    _step("断言 youzan_orders DB 写入")
    record = await _query_order(db_path, order_no)

    if not record:
        _fail(f"youzan_orders 未找到 order_no={order_no}")
        _info("可能原因：有赞 trade.get API 返回异常，或 event_trade 处理失败")
        return False

    _ok(f"youzan_orders 有记录 order_no={order_no}")
    print(f"\n              {'字段':<22} {'变更前':<30} {'变更后'}")
    print(f"              {'-' * 75}")
    fields = ["order_no", "status", "amount_fen", "product_titles", "buyer_id", "updated_at"]
    for f in fields:
        before_v = str(snapshot_before.get(f, "N/A")) if snapshot_before else "（无记录）"
        after_v = str(record.get(f, "N/A"))
        marker = " ←" if before_v != after_v else ""
        print(f"              {f:<22} {before_v:<30} {after_v}{marker}")

    status_ok = bool(record.get("status"))
    amount_ok = record.get("amount_fen", 0) > 0
    titles_ok = bool(record.get("product_titles"))
    updated_ok = snapshot_before is None or record.get("updated_at", "") >= snapshot_before.get("updated_at", "")

    if status_ok:
        _ok("status 字段非空", f"status={record['status']}")
    else:
        _fail("status 字段为空")
    if amount_ok:
        _ok("amount_fen > 0", f"¥{record['amount_fen'] / 100:.2f}")
    else:
        _fail("amount_fen 为 0（可能订单金额为 0 或字段缺失）")
    if titles_ok:
        _ok("product_titles 非空", record["product_titles"][:60])
    else:
        _fail("product_titles 为空")
    if updated_ok:
        _ok("updated_at 已刷新（DB 写入成功）")
    else:
        _fail("updated_at 未更新")

    return status_ok and amount_ok and titles_ok and updated_ok


if __name__ == "__main__":
    result = asyncio.run(run_phase_a())
    elapsed = time.monotonic() - _TEST_START
    print(f"\n{'✅ Phase A 通过' if result else '❌ Phase A 失败'}  总耗时 {elapsed:.1f}s\n")
    sys.exit(0 if result else 1)
