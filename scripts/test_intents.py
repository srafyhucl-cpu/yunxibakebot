"""测试新的 5 意图分类"""
import sys, asyncio, httpx
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

async def test():
    url = "http://127.0.0.1:7001/api/v1/admin/chat-test"
    headers = {"Authorization": "Bearer 100200"}

    tests = [
        ("🚚 明天下午能送到吗", {"content": "明天下午能送到吗", "user_id": "t_delivery"}),
        ("⏰ 你们几点营业", {"content": "你们几点营业", "user_id": "t_hours"}),
        ("💰 运费多少钱", {"content": "运费多少钱", "user_id": "t_fee"}),
        ("📍 门店在哪", {"content": "你们店在哪里", "user_id": "t_address"}),
        ("🍰 提拉米苏", {"content": "提拉米苏多少钱", "user_id": "t_product"}),
        ("😡 退款", {"content": "蛋糕塌了退款", "user_id": "t_refund"}),
        ("👋 闲聊", {"content": "你好呀", "user_id": "t_greeting"}),
    ]

    async with httpx.AsyncClient() as c:
        for label, payload in tests:
            r = await c.post(url, json=payload, headers=headers, timeout=30)
            data = r.json()
            intent = {1:"商品",2:"运费",3:"配送",4:"售后",5:"闲聊"}.get(data.get("intent"), "?")
            reply = (data.get("reply") or "(无回复)")[:120]
            print(f"[{intent}] {label}")
            print(f"  -> {reply}")
            print()

asyncio.run(test())
