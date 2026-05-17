"""
管理后台 API 路由。

提供会话管理、转人工处理、人工回复等功能。
所有接口需要 Bearer Token 鉴权。
"""

from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import settings
from app.logger import setup_logger
from app.repository.session_repo import SessionRepo
from app.repository.transfer_repo import TransferRepo
from app.service.chat import ChatService
from app.service.transfer_manager import TransferManager

logger = setup_logger()
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def verify_token(authorization: str | None = Header(default=None)) -> None:
    """简单的 Bearer Token 鉴权。"""
    if not settings.ADMIN_API_TOKEN:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    token = authorization.removeprefix("Bearer ")
    if token != settings.ADMIN_API_TOKEN:
        raise HTTPException(status_code=403, detail="Token 无效")


def create_admin_router(
    chat_service: ChatService,
    session_repo: SessionRepo,
    transfer_repo: TransferRepo,
) -> APIRouter:
    """工厂函数：注入依赖后返回路由实例。"""
    transfer_mgr = TransferManager(transfer_repo)

    @router.get("/transfers/pending", dependencies=[Depends(verify_token)])
    async def list_pending_transfers() -> dict:
        """获取待接单的转人工工单列表。"""
        transfers = await transfer_mgr.get_pending()
        return {"code": 0, "data": [
            {
                "id": t.id,
                "session_id": t.session_id,
                "user_id": t.user_id,
                "reason": t.reason,
                "conversation_summary": t.conversation_summary,
                "created_at": t.created_at,
            }
            for t in transfers
        ]}

    @router.post("/transfers/{transfer_id}/accept", dependencies=[Depends(verify_token)])
    async def accept_transfer(transfer_id: str, staff_id: str = "") -> dict:
        """客服接单。"""
        await transfer_mgr.accept_transfer(transfer_id, staff_id)
        return {"code": 0, "message": "已接单"}

    @router.post("/transfers/{transfer_id}/close", dependencies=[Depends(verify_token)])
    async def close_transfer(transfer_id: str) -> dict:
        """客服结单。"""
        await transfer_mgr.close_transfer(transfer_id)
        return {"code": 0, "message": "已关闭"}

    @router.post("/sessions/{session_id}/reply", dependencies=[Depends(verify_token)])
    async def human_reply(session_id: str, content: str) -> dict:
        """人工客服回复消息。"""
        if not content.strip():
            raise HTTPException(status_code=422, detail="回复内容不能为空")
        await chat_service.handle_human_reply(session_id, content)
        return {"code": 0, "message": "已发送"}

    @router.get("/sessions", dependencies=[Depends(verify_token)])
    async def list_sessions() -> dict:
        """获取所有活跃会话列表。"""
        return {"code": 0, "data": [], "message": "功能开发中"}

    return router
