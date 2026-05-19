"""
Webhook API 路由。

接收有赞/企微的消息回调：
- 验证签名（有赞 HMAC-SHA256 / 企微 SHA1）
- 解析消息内容
- 提交到 ChatService 异步处理
- 立即返回 200（不阻塞渠道重试）
"""

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException

from app.config import settings
from app.logger import setup_logger
from app.models.session import Channel
from app.service.chat import ChatService
from app.service.youzan.webhook import verify_signature as verify_youzan_signature

logger = setup_logger()
router = APIRouter(prefix="/api/v1/webhook", tags=["webhook"])


def create_webhook_router(chat_service: ChatService) -> APIRouter:
    """工厂函数：注入 ChatService 依赖后返回路由实例。"""

    @router.post("/youzan")
    async def youzan_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
        """
        有赞消息回调入口。

        验证 HMAC-SHA256 签名后异步处理消息。
        无论处理结果如何都立即返回 200，避免有赞重试。
        """
        raw_body = await request.body()

        # 验证签名
        signature = request.headers.get("X-Youzan-Signature", "")
        if not verify_youzan_signature(settings.YOUZAN_WEBHOOK_TOKEN, raw_body, signature):
            logger.warning("有赞签名验证失败")
            raise HTTPException(status_code=403, detail="签名验证失败")

        # 解析消息
        try:
            payload = await request.json()
        except Exception as exc:
            logger.error("有赞消息解析失败: %s", exc)
            raise HTTPException(status_code=400, detail="无效的 JSON 消息") from exc

        msg_type = payload.get("msg_type", "text")
        content_obj = payload.get("content", {})
        buyer_id = payload.get("buyer_id", "")
        msg_id = payload.get("msg_id", "")

        # 提取文本内容（不同消息类型结构不同）
        text_content = ""
        if msg_type == "text":
            text_content = content_obj.get("text", "") if isinstance(content_obj, dict) else str(content_obj)
        else:
            text_content = f"[{msg_type}] {content_obj}"

        if not text_content:
            return {"code": 0, "message": "empty content"}

        # 异步处理消息（不等待返回）
        background_tasks.add_task(
            chat_service.handle_message,
            channel=Channel.YOUZAN,
            user_id=buyer_id,
            content=text_content,
            channel_msg_id=msg_id,
        )

        return {"code": 0, "message": "ok"}

    return router
