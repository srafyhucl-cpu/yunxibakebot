"""
Webhook API 路由。

接收有赞/企微的消息回调：
- 验证签名（有赞 MD5(client_id+body+client_secret) / 企微 SHA1）
- 解析消息内容
- 提交到 ChatService 异步处理
- 立即返回 200（不阻塞渠道重试）
"""

import hashlib
import json
import urllib.parse

from fastapi import APIRouter, Request, HTTPException, Depends
from app.database import get_db_session, db_session_scope
from app.config import settings
from app.logger import setup_logger
from app.models.youzan_webhook_event import (
    YouzanWebhookBusinessType,
    YouzanWebhookEventCreate,
    YouzanWebhookEventUpdate,
    YouzanWebhookStatus,
)
from app.service.chat import ChatService
from app.service.youzan.webhook import verify_signature as verify_youzan_signature, parse_item_id

logger = setup_logger()
router = APIRouter(prefix="/api/v1/webhook", tags=["webhook"])

AUDIT_HTTP_OK = 200
PAYLOAD_PREVIEW_LIMIT = 300


def _extract_trace_id(request: Request) -> str:
    rontgen = request.headers.get("x-rontgen", "")
    for part in rontgen.split(";"):
        if part.startswith("traceId="):
            return part[len("traceId="):]
    return ""


def _parse_payload_msg(payload: dict) -> dict:
    raw_msg = payload.get("msg")
    if isinstance(raw_msg, dict):
        return raw_msg
    if not raw_msg:
        return {}
    try:
        parsed = json.loads(urllib.parse.unquote(str(raw_msg)))
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _extract_business_fields(payload: dict, event_type: str, buyer_id: str) -> tuple[str, str]:
    """从 webhook payload 提取业务类型与业务主键，item_id 解析委托给共享工具函数。"""
    event_type_lower = event_type.lower()
    msg_obj = _parse_payload_msg(payload)
    if event_type_lower.startswith("trade_"):
        tid = msg_obj.get("tid", "")
        if not tid:
            order_info = msg_obj.get("full_order_info", {}).get("order_info", {})
            tid = order_info.get("tid", "")
        return YouzanWebhookBusinessType.TRADE, str(tid)
    if event_type_lower.startswith("item_") or event_type_lower == "youzan_item_skustockorsoldnumupdated":
        item_id = parse_item_id(payload, msg_obj)
        return YouzanWebhookBusinessType.ITEM, str(item_id or "")
    if buyer_id:
        return YouzanWebhookBusinessType.CHAT, buyer_id
    return YouzanWebhookBusinessType.UNKNOWN, ""


def _build_payload_summary(payload: dict, event_type: str, business_type: str, business_key: str) -> str:
    summary = {
        "id": payload.get("id", ""),
        "msg_id": payload.get("msg_id", ""),
        "type": event_type,
        "business_type": business_type,
        "business_key": business_key,
        "timestamp": payload.get("timestamp", ""),
        "msg_type": payload.get("msg_type", ""),
        "buyer_id": payload.get("buyer_id", ""),
    }
    return json.dumps(summary, ensure_ascii=False)[:PAYLOAD_PREVIEW_LIMIT]


async def _create_audit_event(
    chat_service: ChatService,
    payload: dict,
    raw_body: bytes,
    msg_id: str,
    trace_id: str,
    event_type: str,
    buyer_id: str,
) -> int | None:
    if not hasattr(chat_service, "create_youzan_webhook_audit"):
        return None
    business_type, business_key = _extract_business_fields(payload, event_type, buyer_id)
    try:
        return await chat_service.create_youzan_webhook_audit(
            YouzanWebhookEventCreate(
                msg_id=msg_id,
                trace_id=trace_id,
                event_type=event_type,
                business_type=business_type,
                business_key=business_key,
                http_status=AUDIT_HTTP_OK,
                payload_hash=hashlib.sha256(raw_body).hexdigest(),
                payload_summary_json=_build_payload_summary(payload, event_type, business_type, business_key),
            ),
        )
    except Exception as exc:
        logger.error("有赞 webhook 审计收件写入失败 [msg_id=%s]: %s", msg_id, exc)
        return None


async def _mark_audit_processing(chat_service: ChatService, audit_id: int | None, stage: str) -> None:
    if audit_id is None or not hasattr(chat_service, "mark_youzan_webhook_processing"):
        return
    try:
        await chat_service.mark_youzan_webhook_processing(audit_id, stage)
    except Exception as exc:
        logger.error("有赞 webhook 审计处理中状态写入失败 [audit_id=%s]: %s", audit_id, exc)


async def _mark_audit_result(
    chat_service: ChatService,
    audit_id: int | None,
    status: str,
    stage: str,
    error_type: str = "",
    error_message: str = "",
) -> None:
    if audit_id is None or not hasattr(chat_service, "mark_youzan_webhook_result"):
        return
    try:
        await chat_service.mark_youzan_webhook_result(
            audit_id,
            YouzanWebhookEventUpdate(
                status=status,
                process_stage=stage,
                error_type=error_type,
                error_message=error_message,
            ),
        )
    except Exception as exc:
        logger.error("有赞 webhook 审计结果写入失败 [audit_id=%s]: %s", audit_id, exc)


async def _mark_audit_failed(chat_service: ChatService, audit_id: int | None, stage: str, exc: Exception) -> None:
    """后台任务异常统一落账 FAILED（携带异常类型与信息）。"""
    await _mark_audit_result(chat_service, audit_id, YouzanWebhookStatus.FAILED, stage, type(exc).__name__, str(exc))


def create_webhook_router(chat_service: ChatService) -> APIRouter:
    """工厂函数：注入 ChatService 依赖后返回路由实例。"""
    import asyncio
    import time

    # 高并发带滑动窗口自清洗的 TTL 去重容器，彻底在长周期连续运行下死锁任何内存泄漏与锁悬挂
    _processing_msg_timestamps: dict[str, float] = {}

    # 持有后台任务强引用，避免任务被 GC 提前回收导致后台处理/回复丢失（N-2）。
    _background_tasks: set[asyncio.Task] = set()

    def _track_task(task: asyncio.Task) -> None:
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    # 定时异步自愈清洗任务（30秒 TTL 自动物理擦除）
    def _cleanup_stale_msg_ids(now: float) -> None:
        try:
            stale_ids = [msg_id for msg_id, ts in _processing_msg_timestamps.items() if now - ts > 30.0]
            for msg_id in stale_ids:
                _processing_msg_timestamps.pop(msg_id, None)
        except Exception as e:
                logger.error("去重容器定时自愈清洗器异常: %s", e)

    # 启动清洗守护协程
    # cleanup is performed opportunistically inside each request to avoid orphan tasks in tests

    @router.post("/youzan")
    async def youzan_webhook(request: Request, db = Depends(get_db_session)) -> dict:
        """
        有赞消息回调入口（统一接收客服消息推送与交易/商品事件推送）。

        验证 MD5 签名后异步处理消息。
        通过秒级内存锁与数据库双重防线去重。
        """
        now = time.time()
        _cleanup_stale_msg_ids(now)
        raw_body = await request.body()

        # 1. 验证签名（抗伪造安全防线）
        signature = request.headers.get("event-sign", "")
        if not verify_youzan_signature(settings.YOUZAN_CLIENT_ID, settings.YOUZAN_CLIENT_SECRET, raw_body, signature):
            logger.warning("有赞签名验证失败")
            raise HTTPException(status_code=403, detail="签名验证失败")

        # 2. 解析消息
        try:
            payload = await request.json()
        except Exception as exc:
            logger.error("有赞消息解析失败: %s", exc)
            raise HTTPException(status_code=400, detail="无效的 JSON 消息") from exc

        trace_id = _extract_trace_id(request)
        msg_id = payload.get("msg_id") or payload.get("id") or ""
        if not msg_id:
            msg_id = trace_id
        if not msg_id:
            logger.warning("有赞消息缺少可用的去重 ID，丢弃")
            return {"code": 0, "msg": "success"}

        # 3. 秒回防御去重校验（内存锁与数据库双重防线）
        event_type = payload.get("type", "") or request.headers.get("event-type", "")
        buyer_id = payload.get("buyer_id", "")
        audit_id = await _create_audit_event(
            chat_service,
            payload,
            raw_body,
            msg_id,
            trace_id,
            event_type,
            buyer_id,
        )

        if msg_id in _processing_msg_timestamps:
            last_ts = _processing_msg_timestamps[msg_id]
            if now - last_ts < 10.0:
                logger.info("有赞推送处于 10s 滑动锁定窗口期内，秒回复成功: %s", msg_id)
                await _mark_audit_result(chat_service, audit_id, YouzanWebhookStatus.DUPLICATE, "in_memory_duplicate")
                return {"code": 0, "msg": "success"}

        if await chat_service.has_processed_message(msg_id):
            logger.info("有赞推送已处理完毕，秒回复成功: %s", msg_id)
            await _mark_audit_result(chat_service, audit_id, YouzanWebhookStatus.DUPLICATE, "db_duplicate")
            return {"code": 0, "msg": "success"}

        # 锁定当前处理的消息 ID 并记录时间戳
        _processing_msg_timestamps[msg_id] = now

        # 4. 判断是买家咨询客服消息，还是有赞系统事件消息（如商品上架、交易付款等）
        if event_type:
            await _mark_audit_processing(chat_service, audit_id, "system_dispatched")
            # A 轨：系统事件处理管道（双轨合流分发：物理表数仓 + RAG增量 + Telemetry审计）
            # Webhook 充当极简网关分发，彻底移除所有 repository 导入，契合架构红线
            async def _background_process_system_event() -> None:
                try:
                    async with db_session_scope():
                        import datetime
                        timestamp_sec = payload.get("timestamp", int(time.time()))
                        updated_at_str = datetime.datetime.fromtimestamp(timestamp_sec).strftime("%Y-%m-%d %H:%M:%S")

                        await chat_service.handle_youzan_system_event(
                            payload=payload,
                            event_type=event_type,
                            updated_at_str=updated_at_str,
                            msg_id=msg_id,
                            audit_id=audit_id,
                        )
                except Exception as exc:
                    logger.error("有赞系统事件后台业务处理异常 [msg_id=%s]: %s", msg_id, exc, exc_info=True)
                    await _mark_audit_failed(chat_service, audit_id, "system_background_failed", exc)
                finally:
                    _processing_msg_timestamps.pop(msg_id, None)

            _track_task(asyncio.create_task(_background_process_system_event()))
            return {"code": 0, "msg": "success"}

        else:
            # B 轨：普通的买家客服对话消息处理管道（异步handle+立即秒回复，死锁有赞网关3秒重试）
            msg_type = payload.get("msg_type", "text")
            content_obj = payload.get("content", {})
            buyer_id = payload.get("buyer_id", "")

            # 非文本消息（图片/语音/视频等）：不喂给 LLM，直接友好兑底回复（N-6）。
            if msg_type != "text":
                await _mark_audit_processing(chat_service, audit_id, "chat_nontext_fallback")

                async def _background_nontext_fallback() -> None:
                    try:
                        async with db_session_scope():
                            await chat_service.reply_youzan_nontext_fallback(buyer_id, msg_id)
                            await _mark_audit_result(chat_service, audit_id, YouzanWebhookStatus.PROCESSED, "chat_nontext_fallback")
                    except Exception as exc:
                        logger.error("有赞非文本兑底回复异常 [msg_id=%s]: %s", msg_id, exc)
                        await _mark_audit_failed(chat_service, audit_id, "chat_nontext_failed", exc)
                    finally:
                        _processing_msg_timestamps.pop(msg_id, None)

                _track_task(asyncio.create_task(_background_nontext_fallback()))
                return {"code": 0, "msg": "success"}

            # 文本消息：提取文本内容
            text_content = content_obj.get("text", "") if isinstance(content_obj, dict) else str(content_obj)

            if not text_content:
                _processing_msg_timestamps.pop(msg_id, None)
                await _mark_audit_result(chat_service, audit_id, YouzanWebhookStatus.SKIPPED, "chat_empty_content")
                return {"code": 0, "msg": "success"}

            await _mark_audit_processing(chat_service, audit_id, "chat_dispatched")

            async def _background_process() -> None:
                try:
                    async with db_session_scope():
                        await chat_service.handle_message_and_reply_youzan(
                            buyer_id=buyer_id,
                            content=text_content,
                            msg_id=msg_id,
                        )
                        await _mark_audit_result(chat_service, audit_id, YouzanWebhookStatus.PROCESSED, "chat_processed")
                except Exception as exc:
                    logger.error("有赞后台消息处理异常 [msg_id=%s]: %s", msg_id, exc)
                    await _mark_audit_failed(chat_service, audit_id, "chat_background_failed", exc)
                finally:
                    # 释放内存锁定
                    _processing_msg_timestamps.pop(msg_id, None)

            _track_task(asyncio.create_task(_background_process()))

            # 秒回：主协程小于100ms内极速响应，有赞的3秒生死线安全通过
            return {"code": 0, "msg": "success"}

    return router
