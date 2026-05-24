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
from app.models.order import YouzanOrderData
from app.models.youzan_webhook_event import (
    YouzanWebhookBusinessType,
    YouzanWebhookEventUpdate,
    YouzanWebhookStatus,
)
from app.repository.youzan_webhook_event_repo import YouzanWebhookEventRepo

logger = setup_logger()


async def handle_trade_event(
    db,
    youzan_client,
    event_type: str,
    msg_obj: dict,
    updated_at_str: str,
    audit_repo: YouzanWebhookEventRepo | None = None,
    audit_id: int | None = None,
) -> None:
    """
    处理有赞交易系统事件。

    参数：
        db: aiosqlite 数据库连接
        youzan_client: 共享 YouzanClient 单例（避免并发刷新 token 竞态）
        event_type: 事件类型（如 trade_TradeBuyerPay）
        msg_obj: 有赞 Webhook msg 字段解码后的字典
        updated_at_str: 事件时间字符串
    """
    from app.repository.youzan_repo import YouzanOrderRepo, YouzanProductRepo
    from app.repository.analytics_repo import AnalyticsRepo

    tid = msg_obj.get("tid", "")
    if not tid:
        _foi = msg_obj.get("full_order_info", {})
        tid = _foi.get("order_info", {}).get("tid", "")
    if not tid:
        await _mark_trade_audit(
            audit_repo,
            audit_id,
            YouzanWebhookStatus.SKIPPED,
            "trade_missing_tid",
            "missing_tid",
        )
        logger.warning("有赞交易事件缺少 tid")
        return

    logger.info("开始处理有赞交易 Webhook 事件 [%s]: tid=%s", event_type, tid)
    await _mark_trade_audit(
        audit_repo,
        audit_id,
        YouzanWebhookStatus.PROCESSING,
        "trade_api_fetch",
        business_key=tid,
    )

    order_repo = YouzanOrderRepo(db)
    product_repo = YouzanProductRepo(db)
    analytics_repo = AnalyticsRepo(db)

    try:
        old_status = "NONE"
        local_order = await order_repo.get_by_order_no(tid)
        if local_order:
            old_status = local_order["status"]

        raw_order = await youzan_client.get_order(tid)

        outer_data = raw_order.get("data") if isinstance(raw_order, dict) else None
        if not isinstance(outer_data, dict) or "full_order_info" not in outer_data:
            logger.warning("有赞 trade.get 响应缺少 full_order_info，跳过 DB 写入: tid=%s", tid)
            await _mark_trade_audit(
                audit_repo,
                audit_id,
                YouzanWebhookStatus.FAILED,
                "trade_api_bad_response",
                "missing_full_order_info",
                business_key=tid,
            )
            return

        foi = outer_data["full_order_info"]
        order_info = foi.get("order_info", {})
        pay_info = foi.get("pay_info", {})
        buyer_info = foi.get("buyer_info", {})

        addr_info = foi.get("address_info", {})
        status = order_info.get("status", "WAIT_BUYER_PAY")
        payment_fen = int(float(pay_info.get("payment", 0)) * 100)
        total_fee = float(pay_info.get("total_fee", 0))
        post_fee = float(pay_info.get("post_fee", 0))
        post_fee_fen = int(post_fee * 100)
        discount_fen = max(0, int((total_fee + post_fee - float(pay_info.get("payment", 0))) * 100))
        buyer_id = str(buyer_info.get("buyer_id", "") or buyer_info.get("open_id", ""))
        outer_user_id = str(buyer_info.get("outer_user_id", ""))

        order_items = foi.get("orders", [])
        titles_list = []
        total_qty = 0
        items_detail = []
        for item in order_items:
            title = item.get("title", item.get("goods_title", "商品"))
            num = item.get("num", 1)
            titles_list.append(f"{title} x {num}")
            total_qty += num
            items_detail.append({
                "oid": item.get("oid", ""),
                "item_id": item.get("item_id", 0),
                "alias": item.get("alias", ""),
                "title": title,
                "num": num,
                "price": item.get("price", "0"),
                "sku_properties_name": item.get("sku_properties_name", ""),
                "buyer_messages": item.get("buyer_messages", ""),
            })
        product_titles = ", ".join(titles_list)

        await order_repo.upsert_order(YouzanOrderData(
            order_no=tid,
            buyer_id=buyer_id,
            status=status,
            amount_fen=payment_fen,
            logistics_no=local_order["logistics_no"] if local_order else "",
            logistics_status=local_order["logistics_status"] if local_order else "",
            product_titles=product_titles,
            total_quantity=total_qty,
            pay_time=order_info.get("pay_time", ""),
            consign_time=order_info.get("consign_time", ""),
            pay_type_str=order_info.get("pay_type_str", ""),
            express_type=int(order_info.get("express_type", 0)),
            refund_state=int(order_info.get("refund_state", 0)),
            post_fee_fen=post_fee_fen,
            discount_fen=discount_fen,
            delivery_province=addr_info.get("delivery_province", ""),
            delivery_city=addr_info.get("delivery_city", ""),
            delivery_district=addr_info.get("delivery_district", ""),
            delivery_time=addr_info.get("delivery_start_time", ""),
            outer_user_id=outer_user_id,
            order_items_json=json.dumps(items_detail, ensure_ascii=False),
            created_at=order_info.get("created", ""),
            updated_at=updated_at_str,
        ))

        if old_status != status:
            await analytics_repo.add_event(
                session_id=None,
                buyer_id=buyer_id,
                event_type="order_state_change",
                event_source="webhook_youzan",
                ref_id=tid,
                meta_data=json.dumps({"old_status": old_status, "new_status": status}, ensure_ascii=False),
                created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
                        created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    )
                    logger.info(
                        "🎉 完美！AI 导购业绩归因匹配成功！已为 Dashboard 记账绩效: session_id=%s, buyer_id=%s, gmv_fen=%s",
                        ai_session_id, buyer_id, item.get("payment"),
                    )
        await _mark_trade_audit(
            audit_repo,
            audit_id,
            YouzanWebhookStatus.PROCESSED,
            "trade_processed",
            business_key=tid,
        )

    except Exception as exc:
        logger.error("处理有赞交易系统事件失败: tid=%s err=%s", tid, exc)
        await _mark_trade_audit(
            audit_repo,
            audit_id,
            YouzanWebhookStatus.FAILED,
            "trade_failed",
            type(exc).__name__,
            str(exc),
            business_key=tid,
        )


async def _mark_trade_audit(
    audit_repo: YouzanWebhookEventRepo | None,
    audit_id: int | None,
    status: str,
    process_stage: str,
    error_type: str = "",
    error_message: str = "",
    business_key: str = "",
) -> None:
    if audit_repo is None or audit_id is None:
        return
    if status == YouzanWebhookStatus.PROCESSING:
        await audit_repo.mark_processing(
            audit_id,
            process_stage,
            business_type=YouzanWebhookBusinessType.TRADE,
            business_key=business_key,
        )
        return
    await audit_repo.mark_result(
        audit_id,
        YouzanWebhookEventUpdate(
            status=status,
            process_stage=process_stage,
            business_type=YouzanWebhookBusinessType.TRADE,
            business_key=business_key,
            error_type=error_type,
            error_message=error_message,
        ),
    )
