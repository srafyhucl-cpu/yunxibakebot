"""
Webhook API 路由。

接收有赞/企微的消息回调：
- 验证签名（有赞 HMAC-SHA256 / 企微 SHA1）
- 解析消息内容
- 提交到 ChatService 异步处理
- 立即返回 200（不阻塞渠道重试）
"""

from fastapi import APIRouter, Request, HTTPException

from app.config import settings
from app.logger import setup_logger
from app.service.chat import ChatService
from app.service.youzan.webhook import verify_signature as verify_youzan_signature

logger = setup_logger()
router = APIRouter(prefix="/api/v1/webhook", tags=["webhook"])


def create_webhook_router(chat_service: ChatService) -> APIRouter:
    """工厂函数：注入 ChatService 依赖后返回路由实例。"""
    # 高并发内存锁集合，防止同一秒内重复报文冲击
    _processing_msg_ids: set[str] = set()

    @router.post("/youzan")
    async def youzan_webhook(request: Request) -> dict:
        """
        有赞消息回调入口（统一接收客服消息推送与交易/商品事件推送）。

        验证 HMAC-SHA256 签名后异步处理消息。
        通过秒级内存锁与数据库双重防线去重。
        """
        raw_body = await request.body()

        # 1. 验证签名（抗伪造安全防线）
        signature = request.headers.get("X-Youzan-Signature", "")
        if not verify_youzan_signature(settings.YOUZAN_WEBHOOK_TOKEN, raw_body, signature):
            logger.warning("有赞签名验证失败")
            raise HTTPException(status_code=403, detail="签名验证失败")

        # 2. 解析消息
        try:
            payload = await request.json()
        except Exception as exc:
            logger.error("有赞消息解析失败: %s", exc)
            raise HTTPException(status_code=400, detail="无效的 JSON 消息") from exc

        msg_id = payload.get("msg_id", "")
        if not msg_id:
            logger.warning("有赞消息缺少 msg_id")
            raise HTTPException(status_code=400, detail="缺少 msg_id")

        # 3. 秒回防御去重校验（内存锁与数据库双重防线）
        if msg_id in _processing_msg_ids or await chat_service._message_repo.has_processed(msg_id):
            logger.info("有赞推送已在处理或已处理完毕，秒回复成功: %s", msg_id)
            return {"code": 0, "msg": "success"}

        # 锁定当前处理的消息 ID
        _processing_msg_ids.add(msg_id)

        # 4. 判断是买家咨询客服消息，还是有赞系统事件消息（如商品上架、交易付款等）
        event_type = payload.get("type", "")
        if event_type:
            # A 轨：系统事件处理管道（双轨合流分发：物理表数仓 + RAG增量 + Telemetry审计）
            # Webhook 充当极简网关分发，彻底移除所有 repository 导入，契合架构红线
            async def _background_process_system_event() -> None:
                try:
                    import datetime
                    import time
                    timestamp_sec = payload.get("timestamp", int(time.time()))
                    updated_at_str = datetime.datetime.fromtimestamp(timestamp_sec).strftime("%Y-%m-%d %H:%M:%S")

                    await chat_service.handle_youzan_system_event(
                        payload=payload,
                        updated_at_str=updated_at_str,
                        msg_id=msg_id,
                    )
                except Exception as exc:
                    logger.error("有赞系统事件后台业务处理异常 [msg_id=%s]: %s", msg_id, exc)
                finally:
                    _processing_msg_ids.discard(msg_id)

            import asyncio
            asyncio.create_task(_background_process_system_event())
            return {"code": 0, "msg": "success"}

        else:
            # B 轨：普通的买家客服对话消息处理管道（异步handle+立即秒回复，死锁有赞网关3秒重试）
            msg_type = payload.get("msg_type", "text")
            content_obj = payload.get("content", {})
            buyer_id = payload.get("buyer_id", "")

            # 提取文本内容（不同消息类型结构不同）
            text_content = ""
            if msg_type == "text":
                text_content = content_obj.get("text", "") if isinstance(content_obj, dict) else str(content_obj)
            else:
                text_content = f"[{msg_type}] {content_obj}"

            if not text_content:
                _processing_msg_ids.discard(msg_id)
                return {"code": 0, "msg": "success"}

            async def _background_process() -> None:
                try:
                    await chat_service.handle_message_and_reply_youzan(
                        buyer_id=buyer_id,
                        content=text_content,
                        msg_id=msg_id,
                    )
                except Exception as exc:
                    logger.error("有赞后台消息处理异常 [msg_id=%s]: %s", msg_id, exc)
                finally:
                    # 释放内存锁定
                    _processing_msg_ids.discard(msg_id)

            import asyncio
            asyncio.create_task(_background_process())

            # 秒回：主协程小于100ms内极速响应，有赞的3秒生死线安全通过
            return {"code": 0, "msg": "success"}

    return router
