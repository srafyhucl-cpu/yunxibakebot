"""
有赞交易事件处理器。

处理有赞 Webhook 推送的交易订单状态变更事件（trade_*）：
- 物理宽表 Upsert（orders）
- 触点二：订单履约生命周期状态变更埋点（order_state_change）
- 触点四：24 小时 AI 导购 ROI 付款归因埋点（order_conversion）
"""

import datetime
import json

from app.logger import setup_logger

logger = setup_logger()


async def handle_trade_event(db, event_type: str, msg_obj: dict, updated_at_str: str) -> None:
    """
    处理有赞交易系统事件。

    参数：
        db: aiosqlite 数据库连接
        event_type: 事件类型（如 trade_TradeBuyerPay）
        msg_obj: 有赞 Webhook msg 字段解码后的字典
        updated_at_str: 事件时间字符串
    """
    from app.repository.youzan_repo import YouzanOrderRepo, YouzanProductRepo
    from app.repository.analytics_repo import AnalyticsRepo
    from app.repository.config_repo import ConfigRepo
    from app.service.youzan.client import YouzanClient

    tid = msg_obj.get("tid", "")
    if not tid:
        logger.warning("有赞交易事件缺少 tid")
        return

    logger.info("开始处理有赞交易 Webhook 事件 [%s]: tid=%s", event_type, tid)

    order_repo = YouzanOrderRepo(db)
    product_repo = YouzanProductRepo(db)
    analytics_repo = AnalyticsRepo(db)

    try:
        old_status = "NONE"
        local_order = await order_repo.get_by_order_no(tid)
        if local_order:
            old_status = local_order["status"]

        yz_client = YouzanClient(config_repo=ConfigRepo(db))
        raw_order = await yz_client.get_order(tid)
        await yz_client.close()

        outer_data = raw_order.get("data") or raw_order.get("response") if isinstance(raw_order, dict) else None
        if not isinstance(outer_data, dict) or "trade" not in outer_data:
            return

        trade = outer_data["trade"]
        status = trade.get("status", "WAIT_BUYER_PAY")
        payment_fen = int(float(trade.get("payment", 0)) * 100)
        buyer_id = trade.get("buyer_id", "") or trade.get("open_id", "")

        order_items = trade.get("orders", [])
        titles_list = []
        total_qty = 0
        for item in order_items:
            titles_list.append(f"{item.get('title', '商品')} x {item.get('num', 1)}")
            total_qty += item.get("num", 1)
        product_titles = ", ".join(titles_list)
        created = trade.get("created", "")

        await order_repo.upsert_order(
            order_no=tid,
            buyer_id=buyer_id,
            status=status,
            amount_fen=payment_fen,
            logistics_no=local_order["logistics_no"] if local_order else "",
            logistics_status=local_order["logistics_status"] if local_order else "",
            product_titles=product_titles,
            total_quantity=total_qty,
            created_at=created,
            updated_at=updated_at_str,
        )

        if old_status != status:
            await analytics_repo.add_event(
                session_id=None,
                buyer_id=buyer_id,
                event_type="order_state_change",
                event_source="webhook_youzan",
                ref_id=tid,
                meta_data=json.dumps({"old_status": old_status, "new_status": status}, ensure_ascii=False),
                created_at=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            )
            logger.info("已成功记录订单履约时效埋点: tid=%s, old=%s, new=%s", tid, old_status, status)

        is_payment_event = event_type == "trade_TradeBuyerPay" or (
            old_status in ("NONE", "WAIT_BUYER_PAY")
            and status in ("WAIT_SELLER_SEND_GOODS", "TRADE_PAID", "TRADE_SUCCESS")
        )
        if is_payment_event:
            logger.info("触发 24 小时 AI 导购业绩付款归因校验: buyer=%s", buyer_id)
            for item in order_items:
                item_id = item.get("item_id", 0)
                if not item_id:
                    continue
                product = await product_repo.get_by_id(item_id)
                if not product:
                    continue
                alias = product["alias"]
                ai_session_id = await analytics_repo.check_ai_recommend_for_conversion(
                    buyer_id, alias, lookback_hours=24
                )
                if ai_session_id:
                    await analytics_repo.add_event(
                        session_id=ai_session_id,
                        buyer_id=buyer_id,
                        event_type="order_conversion",
                        event_source="webhook_youzan",
                        ref_id=tid,
                        meta_data=json.dumps({
                            "product_title": item.get("title", ""),
                            "product_alias": alias,
                            "amount_fen": int(float(item.get("payment", 0)) * 100),
                            "lookback": "24_hours",
                        }, ensure_ascii=False),
                        created_at=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    )
                    logger.info(
                        "🎉 完美！AI 导购业绩归因匹配成功！已为 Dashboard 记账绩效: session_id=%s, buyer_id=%s, gmv_fen=%s",
                        ai_session_id, buyer_id, item.get("payment"),
                    )

    except Exception as exc:
        logger.error("处理有赞交易系统事件失败: tid=%s err=%s", tid, exc)
