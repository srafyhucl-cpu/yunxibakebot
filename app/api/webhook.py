"""
Webhook API 路由。

接收有赞/企微的消息回调：
- 验证签名（有赞 MD5(client_id+body+client_secret) / 企微 SHA1）
- 解析消息内容
- 提交到 ChatService 异步处理
- 立即返回 200（不阻塞渠道重试）
"""

import asyncio
import hashlib
import time

from fastapi import APIRouter, Request, HTTPException, Depends
from app.database import get_db_session, db_session_scope
from app.config import settings
from app.logger import setup_logger
from app.models.youzan_webhook_event import (
    YouzanWebhookStatus,
    YouzanWebhookEventCreate,
    YouzanWebhookEventUpdate,
)
from app.service.chat import ChatService
from app.service.youzan.webhook import (
    verify_signature as verify_youzan_signature,
)
from app.api.webhook_helpers import (
    extract_trace_id,
    extract_business_fields,
    build_payload_summary,
    is_youzan_hosting_message_event,
    is_youzan_hosting_event,
    parse_youzan_hosting_message,
)

logger = setup_logger()

AUDIT_HTTP_OK = 200
PAYLOAD_PREVIEW_LIMIT = 300


def create_webhook_router(chat_service: ChatService) -> APIRouter:
    """工厂函数：注入 ChatService 依赖后返回路由实例。"""
    import datetime

    router = APIRouter(prefix="/api/v1/webhook", tags=["webhook"])

    # 高并发带滑动窗口自清洗的 TTL 去重容器
    _processing_msg_timestamps: dict[str, float] = {}

    # 持有后台任务强引用，避免任务被 GC 提前回收
    _background_tasks: set[asyncio.Task] = set()

    def _track_task(task: asyncio.Task) -> None:
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    def _cleanup_stale_msg_ids(now: float) -> None:
        try:
            stale_ids = [
                msg_id
                for msg_id, ts in _processing_msg_timestamps.items()
                if now - ts > 30.0
            ]
            for msg_id in stale_ids:
                _processing_msg_timestamps.pop(msg_id, None)
        except Exception as e:
            logger.error("去重容器定时自愈清洗器异常: %s", e)

    async def _create_audit_event(
        payload: dict,
        raw_body: bytes,
        msg_id: str,
        trace_id: str,
        event_type: str,
        buyer_id: str,
    ) -> int | None:
        """创建有赞 Webhook 审计事件，返回审计 ID。"""
        if not hasattr(chat_service, "create_youzan_webhook_audit"):
            return None
        business_type, business_key = extract_business_fields(
            payload, event_type, buyer_id
        )
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
                    payload_summary_json=build_payload_summary(
                        payload, event_type, business_type, business_key
                    ),
                ),
            )
        except Exception as exc:
            logger.error("有赞 webhook 审计收件写入失败 [msg_id=%s]: %s", msg_id, exc)
            return None

    async def _mark_audit_processing(audit_id: int | None, stage: str) -> None:
        if audit_id is None or not hasattr(
            chat_service, "mark_youzan_webhook_processing"
        ):
            return
        try:
            await chat_service.mark_youzan_webhook_processing(audit_id, stage)
        except Exception as exc:
            logger.error(
                "有赞 webhook 审计处理中状态写入失败 [audit_id=%s]: %s", audit_id, exc
            )

    async def _mark_audit_result(
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
            logger.error(
                "有赞 webhook 审计结果写入失败 [audit_id=%s]: %s", audit_id, exc
            )

    async def _mark_audit_failed(
        audit_id: int | None, stage: str, exc: Exception
    ) -> None:
        await _mark_audit_result(
            audit_id, YouzanWebhookStatus.FAILED, stage, type(exc).__name__, str(exc)
        )

    @router.post("/youzan")
    async def youzan_webhook(request: Request, db=Depends(get_db_session)) -> dict:
        """
        有赞消息回调入口（统一接收客服消息推送与交易/商品事件推送）。

        验证 MD5 签名后异步处理消息。
        通过秒级内存锁与数据库双重防线去重。
        """
        now = time.time()
        _cleanup_stale_msg_ids(now)
        raw_body = await request.body()

        # 1. 验证签名
        signature = request.headers.get("event-sign", "")
        if not verify_youzan_signature(
            settings.YOUZAN_CLIENT_ID,
            settings.YOUZAN_CLIENT_SECRET,
            raw_body,
            signature,
        ):
            logger.warning("有赞签名验证失败")
            raise HTTPException(status_code=403, detail="签名验证失败")

        # 2. 解析消息
        try:
            payload = await request.json()
        except Exception as exc:
            logger.error("有赞消息解析失败: %s", exc)
            raise HTTPException(status_code=400, detail="无效的 JSON 消息") from exc

        trace_id = extract_trace_id(request)
        # 3. 审计事件创建
        event_type = payload.get("type", "") or request.headers.get("event-type", "")
        msg_id = payload.get("msg_id") or payload.get("id") or ""
        if is_youzan_hosting_message_event(event_type):
            hosting_msg = parse_youzan_hosting_message(payload)
            msg_id = hosting_msg["msg_id"] or msg_id
        if not msg_id:
            msg_id = trace_id
        if not msg_id:
            logger.warning("有赞消息缺少可用的去重 ID，丢弃")
            return {"code": 0, "msg": "success"}

        buyer_id = payload.get("buyer_id", "")
        audit_id = await _create_audit_event(
            payload, raw_body, msg_id, trace_id, event_type, buyer_id
        )

        # 4. 内存去重校验（10 秒滑动窗口）
        if msg_id in _processing_msg_timestamps:
            last_ts = _processing_msg_timestamps[msg_id]
            if now - last_ts < 10.0:
                logger.info("有赞推送处于 10s 滑动锁定窗口期内，秒回复成功: %s", msg_id)
                await _mark_audit_result(
                    audit_id, YouzanWebhookStatus.DUPLICATE, "in_memory_duplicate"
                )
                return {"code": 0, "msg": "success"}

        # 5. 数据库去重校验
        if await chat_service.has_processed_message(msg_id):
            logger.info("有赞推送已处理完毕，秒回复成功: %s", msg_id)
            await _mark_audit_result(
                audit_id, YouzanWebhookStatus.DUPLICATE, "db_duplicate"
            )
            return {"code": 0, "msg": "success"}

        # 6. 锁定消息 ID
        _processing_msg_timestamps[msg_id] = now

        # 7. 分发处理：系统事件 vs 客服消息
        if is_youzan_hosting_message_event(event_type):
            hosting_msg = parse_youzan_hosting_message(payload)
            hosting_msg_id = hosting_msg["msg_id"] or msg_id
            conversation_id = hosting_msg["conversation_id"]
            yz_open_id = hosting_msg["yz_open_id"]
            msg_type = hosting_msg["msg_type"] or "text"
            content = hosting_msg["content"]

            if not conversation_id or not hosting_msg_id:
                _processing_msg_timestamps.pop(msg_id, None)
                await _mark_audit_result(
                    audit_id,
                    YouzanWebhookStatus.SKIPPED,
                    "hosting_missing_identity",
                )
                return {"code": 0, "msg": "success"}

            if msg_type != "text":
                await _mark_audit_processing(audit_id, "hosting_nontext_fallback")

                async def _background_hosting_nontext_fallback() -> None:
                    try:
                        async with db_session_scope():
                            await chat_service.reply_youzan_hosting_nontext_fallback(
                                conversation_id=conversation_id,
                                msg_id=hosting_msg_id,
                            )
                            await _mark_audit_result(
                                audit_id,
                                YouzanWebhookStatus.PROCESSED,
                                "hosting_nontext_fallback",
                            )
                    except Exception as exc:
                        logger.error(
                            "有赞托管非文本兜底回复异常 [msg_id=%s]: %s",
                            hosting_msg_id,
                            exc,
                        )
                        await _mark_audit_failed(
                            audit_id, "hosting_nontext_failed", exc
                        )
                    finally:
                        _processing_msg_timestamps.pop(msg_id, None)

                _track_task(asyncio.create_task(_background_hosting_nontext_fallback()))
                return {"code": 0, "msg": "success"}

            if not content:
                _processing_msg_timestamps.pop(msg_id, None)
                await _mark_audit_result(
                    audit_id, YouzanWebhookStatus.SKIPPED, "hosting_empty_content"
                )
                return {"code": 0, "msg": "success"}

            await _mark_audit_processing(audit_id, "hosting_chat_dispatched")

            async def _background_process_hosting_message() -> None:
                try:
                    async with db_session_scope():
                        await chat_service.handle_youzan_hosting_message(
                            conversation_id=conversation_id,
                            yz_open_id=yz_open_id,
                            content=content,
                            msg_id=hosting_msg_id,
                        )
                        await _mark_audit_result(
                            audit_id,
                            YouzanWebhookStatus.PROCESSED,
                            "hosting_chat_processed",
                        )
                except Exception as exc:
                    logger.error(
                        "有赞托管消息后台业务处理异常 [msg_id=%s]: %s",
                        hosting_msg_id,
                        exc,
                        exc_info=True,
                    )
                    await _mark_audit_failed(audit_id, "hosting_chat_failed", exc)
                finally:
                    _processing_msg_timestamps.pop(msg_id, None)

            _track_task(asyncio.create_task(_background_process_hosting_message()))
            return {"code": 0, "msg": "success"}

        if is_youzan_hosting_event(event_type):
            await _mark_audit_result(
                audit_id, YouzanWebhookStatus.SKIPPED, "hosting_event_ack"
            )
            _processing_msg_timestamps.pop(msg_id, None)
            return {"code": 0, "msg": "success"}

        if event_type:
            await _mark_audit_processing(audit_id, "system_dispatched")

            # A 轨：系统事件处理管道
            async def _background_process_system_event() -> None:
                try:
                    async with db_session_scope():
                        timestamp_sec = payload.get("timestamp", int(time.time()))
                        updated_at_str = datetime.datetime.fromtimestamp(
                            timestamp_sec
                        ).strftime("%Y-%m-%d %H:%M:%S")
                        await chat_service.handle_youzan_system_event(
                            payload=payload,
                            event_type=event_type,
                            updated_at_str=updated_at_str,
                            msg_id=msg_id,
                            audit_id=audit_id,
                        )
                except Exception as exc:
                    logger.error(
                        "有赞系统事件后台业务处理异常 [msg_id=%s]: %s",
                        msg_id,
                        exc,
                        exc_info=True,
                    )
                    await _mark_audit_failed(audit_id, "system_background_failed", exc)
                finally:
                    _processing_msg_timestamps.pop(msg_id, None)

            _track_task(asyncio.create_task(_background_process_system_event()))
            return {"code": 0, "msg": "success"}

        else:
            # B 轨：客服对话消息处理管道
            msg_type = payload.get("msg_type", "text")
            content_obj = payload.get("content", {})
            buyer_id = payload.get("buyer_id", "")

            # 非文本消息：直接友好兜底回复
            if msg_type != "text":
                await _mark_audit_processing(audit_id, "chat_nontext_fallback")

                async def _background_nontext_fallback() -> None:
                    try:
                        async with db_session_scope():
                            await chat_service.reply_youzan_nontext_fallback(
                                buyer_id, msg_id
                            )
                            await _mark_audit_result(
                                audit_id,
                                YouzanWebhookStatus.PROCESSED,
                                "chat_nontext_fallback",
                            )
                    except Exception as exc:
                        logger.error(
                            "有赞非文本兜底回复异常 [msg_id=%s]: %s", msg_id, exc
                        )
                        await _mark_audit_failed(audit_id, "chat_nontext_failed", exc)
                    finally:
                        _processing_msg_timestamps.pop(msg_id, None)

                _track_task(asyncio.create_task(_background_nontext_fallback()))
                return {"code": 0, "msg": "success"}

            # 文本消息：提取文本内容并处理
            text_content = (
                content_obj.get("text", "")
                if isinstance(content_obj, dict)
                else str(content_obj)
            )
            if not text_content:
                _processing_msg_timestamps.pop(msg_id, None)
                await _mark_audit_result(
                    audit_id, YouzanWebhookStatus.SKIPPED, "chat_empty_content"
                )
                return {"code": 0, "msg": "success"}

            await _mark_audit_processing(audit_id, "chat_dispatched")

            async def _background_process() -> None:
                try:
                    async with db_session_scope():
                        await chat_service.handle_message_and_reply_youzan(
                            buyer_id=buyer_id,
                            content=text_content,
                            msg_id=msg_id,
                        )
                        await _mark_audit_result(
                            audit_id, YouzanWebhookStatus.PROCESSED, "chat_processed"
                        )
                except Exception as exc:
                    logger.error("有赞后台消息处理异常 [msg_id=%s]: %s", msg_id, exc)
                    await _mark_audit_failed(audit_id, "chat_background_failed", exc)
                finally:
                    _processing_msg_timestamps.pop(msg_id, None)

            _track_task(asyncio.create_task(_background_process()))
            return {"code": 0, "msg": "success"}

    return router
