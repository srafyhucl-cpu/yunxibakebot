"""
Function Calling 工具实现：订单与物流查询。

提供 get_order_info（本地短路 + 有赞实时）和 get_logistics_info（物流轨迹查询 + 宽表反写）。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.logger import setup_logger

if TYPE_CHECKING:
    from app.service.knowledge_retriever import KnowledgeRetriever
    from app.service.youzan.client import YouzanClient

logger = setup_logger()


async def get_order_info(
    knowledge_retriever: KnowledgeRetriever,
    order_no: str,
    youzan_client: YouzanClient | None = None,
) -> str:
    """
    查询订单详细信息（内置已完成/已关闭订单状态机本地短路流控防线）。

    参数：
        youzan_client: 共享 YouzanClient 单例（由 ChatService 注入，避免并发竞态）
    """
    db = knowledge_retriever._repo._db
    from app.repository.youzan_repo import YouzanOrderRepo
    order_repo = YouzanOrderRepo(db)

    try:
        local_order = await order_repo.get_by_order_no(order_no)
        if local_order and local_order["status"] in ("TRADE_SUCCESS", "TRADE_CLOSED"):
            logger.info("已完成/已关闭订单触发本地状态机短路秒回: order_no=%s", order_no)
            return json.dumps({
                "order_no": order_no,
                "status": local_order["status"],
                "amount_yuan": local_order["amount_fen"] / 100.0,
                "product_titles": local_order["product_titles"],
                "logistics_no": local_order["logistics_no"],
                "logistics_status": local_order["logistics_status"],
                "source": "local_short_circuit",
            }, ensure_ascii=False)

        if youzan_client is None:
            from app.service.youzan.client import YouzanClient as _YZC
            from app.repository.config_repo import ConfigRepo
            youzan_client = _YZC(config_repo=ConfigRepo(db))
        raw_order = await youzan_client.get_order(order_no)

        outer_data = raw_order.get("data") if isinstance(raw_order, dict) else None
        if not isinstance(outer_data, dict) or "full_order_info" not in outer_data:
            return json.dumps({"order_no": order_no, "available": False, "message": "未找到此订单，请检查您的订单号或小程序绑定手机号是否输入正确"}, ensure_ascii=False)

        foi = outer_data["full_order_info"]
        order_info = foi.get("order_info", {})
        pay_info = foi.get("pay_info", {})
        buyer_info = foi.get("buyer_info", {})

        status = order_info.get("status", "WAIT_BUYER_PAY")
        payment_fen = int(float(pay_info.get("payment", 0)) * 100)
        buyer_id = str(buyer_info.get("buyer_id", "") or buyer_info.get("open_id", ""))

        order_items = foi.get("orders", [])
        titles_list = []
        total_qty = 0
        for item in order_items:
            titles_list.append(f"{item.get('title', item.get('goods_title', '商品'))} x {item.get('num', 1)}")
            total_qty += item.get("num", 1)
        product_titles = ", ".join(titles_list)
        created = order_info.get("created", "")
        updated = order_info.get("update_time", "") or order_info.get("created", "")

        await order_repo.upsert_order(
            order_no=order_no,
            buyer_id=buyer_id,
            status=status,
            amount_fen=payment_fen,
            logistics_no=local_order["logistics_no"] if local_order else "",
            logistics_status=local_order["logistics_status"] if local_order else "",
            product_titles=product_titles,
            total_quantity=total_qty,
            created_at=created,
            updated_at=updated,
        )

        address_info = foi.get("address_info", {})
        return json.dumps({
            "order_no": order_no,
            "status": status,
            "amount_yuan": payment_fen / 100.0,
            "product_titles": product_titles,
            "receiver_name": address_info.get("receiver_name", buyer_id),
            "receiver_mobile": address_info.get("receiver_tel", ""),
            "address": (
                address_info.get("state", "") + address_info.get("city", "")
                + address_info.get("county", "") + address_info.get("address", "")
            ),
            "source": "youzan_live_api",
        }, ensure_ascii=False)

    except Exception as exc:
        logger.error("有赞订单查询失败: order_no=%s err=%s", order_no, exc)
        return json.dumps({"order_no": order_no, "available": False, "message": "订单查询发生系统异常，请稍后再试或联系人工客服"}, ensure_ascii=False)


async def get_logistics_info(
    knowledge_retriever: KnowledgeRetriever,
    order_no: str,
    youzan_client: YouzanClient | None = None,
) -> str:
    """
    查询物流配送进度并反写更新 orders 交易物理大宽表。

    参数：
        youzan_client: 共享 YouzanClient 单例（由 ChatService 注入，避免并发竞态）
    """
    db = knowledge_retriever._repo._db

    try:
        if youzan_client is None:
            from app.service.youzan.client import YouzanClient as _YZC
            from app.repository.config_repo import ConfigRepo
            youzan_client = _YZC(config_repo=ConfigRepo(db))
        raw_logistics = await youzan_client.get_logistics(order_no)

        express_data = raw_logistics.get("data") or raw_logistics.get("response") if isinstance(raw_logistics, dict) else None
        if not isinstance(express_data, dict):
            return json.dumps({"order_no": order_no, "available": False, "message": "未查询到物流派送信息，可能商家尚未发货"}, ensure_ascii=False)

        express_id = express_data.get("express_id", "")
        express_name = express_data.get("express_name", "")
        step_descs = [
            f"[{s.get('status_time', '')}] {s.get('status_desc', '')}"
            for s in express_data.get("transit_step_infos", [])
        ]

        from app.repository.youzan_repo import YouzanOrderRepo
        order_repo = YouzanOrderRepo(db)
        local_order = await order_repo.get_by_order_no(order_no)
        if local_order:
            await order_repo.upsert_order(
                order_no=local_order["order_no"],
                buyer_id=local_order["buyer_id"],
                status=local_order["status"],
                amount_fen=local_order["amount_fen"],
                logistics_no=express_id,
                logistics_status=step_descs[-1] if step_descs else "暂无轨迹",
                product_titles=local_order["product_titles"],
                total_quantity=local_order["total_quantity"],
                created_at=local_order["created_at"],
                updated_at=local_order["updated_at"],
            )

        return json.dumps({
            "order_no": order_no,
            "express_name": express_name,
            "express_id": express_id,
            "steps": step_descs[:5],
            "message": "查询成功",
        }, ensure_ascii=False)

    except Exception as exc:
        logger.error("有赞物流查询失败: order_no=%s err=%s", order_no, exc)
        return json.dumps({"order_no": order_no, "available": False, "message": "物流查询发生异常，请稍后再试或联系人工客服获取配送进度"}, ensure_ascii=False)
