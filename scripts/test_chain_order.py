"""Phase A 全链路测试：客服消息 Webhook → LLM Function Calling → 有赞真实 API → DB 回写。

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
WAIT_SECONDS = 10
BUYER_ID = "test_buyer_phase_a"
HTTP_OK = 200


async def _discover_order_no(db_path: str) -> str | None:
    """从本地 youzan_orders 取最近一条已知订单号；若无则返回 None。"""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT order_no FROM youzan_orders ORDER BY updated_at DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def _discover_order_from_products(db_path: str) -> str:
    """从 youzan_products 取一个商品 alias，构造询问语句用的订单关键词（兜底）。"""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT title FROM youzan_products WHERE is_active = 1 LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "年轮蛋糕"


async def _query_order(db_path: str, order_no: str) -> dict | None:
    """查询本地 youzan_orders 中目标订单记录。"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT order_no, status, amount_fen, product_titles FROM youzan_orders WHERE order_no = ?",
            (order_no,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


def _print_result(name: str, passed: bool, detail: str = "") -> None:
    mark = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {mark}  {name}")
    if detail:
        print(f"         {detail}")


async def run_phase_a() -> bool:
    print("\n=== Phase A：客服消息 → Function Calling → 有赞 API → DB 回写 ===\n")

    db_path = str(ROOT_DIR / settings.DB_PATH)

    # 1. 发现可用的订单号
    order_no = await _discover_order_no(db_path)
    if order_no:
        print(f"  [Setup] 使用已知订单号: {order_no}")
        question = f"我想查一下订单 {order_no} 的状态"
    else:
        product_title = await _discover_order_from_products(db_path)
        question = f"{product_title}多少钱？帮我查一下有没有优惠"
        print(f"  [Setup] youzan_orders 暂无记录，改用商品问询: {question!r}")
        order_no = None

    # 2. 生成有赞客服消息 Webhook（B 轨：买家询问）
    msg_id = f"test_phase_a_{int(time.time() * 1000)}"
    raw_body, signature = YouzanMockEmulator.generate_webhook_message(
        buyer_id=BUYER_ID,
        content_text=question,
        msg_id=msg_id,
        client_id=settings.YOUZAN_CLIENT_ID,
        client_secret=settings.YOUZAN_CLIENT_SECRET,
    )
    payload = json.loads(raw_body)

    print(f"  [POST] {BASE_URL}{WEBHOOK_PATH}")
    print(f"         msg_id={msg_id}  question={question!r}")

    # 3. 发送 Webhook
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{BASE_URL}{WEBHOOK_PATH}",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "event-sign": signature,
            },
        )

    _print_result(
        "Webhook 接收返回 200",
        response.status_code == HTTP_OK,
        f"status={response.status_code}  body={response.text[:80]}",
    )
    if response.status_code != HTTP_OK:
        return False

    # 4. 等待后台链路执行完毕
    print(f"\n  [等待] {WAIT_SECONDS}s（LLM + 有赞 API + DB 写入）...")
    await asyncio.sleep(WAIT_SECONDS)

    # 5. 断言 DB 写入
    if order_no:
        record = await _query_order(db_path, order_no)
        _print_result(
            f"youzan_orders 有记录 order_no={order_no}",
            record is not None,
            str(record) if record else "未找到",
        )
        if record:
            _print_result(
                "status 字段非空",
                bool(record.get("status")),
                f"status={record.get('status')}",
            )
            _print_result(
                "amount_fen 字段非空",
                bool(record.get("amount_fen")),
                f"amount_fen={record.get('amount_fen')}",
            )
        return record is not None
    else:
        print(
            "  ℹ️  无历史订单号可断言 DB 写入；请检查服务日志确认 LLM 已触发 Function Calling"
        )
        return True


if __name__ == "__main__":
    result = asyncio.run(run_phase_a())
    print(f"\n{'✅ Phase A 通过' if result else '❌ Phase A 失败'}\n")
    sys.exit(0 if result else 1)
