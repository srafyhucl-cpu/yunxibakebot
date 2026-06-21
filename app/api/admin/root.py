"""
管理后台页面路由与鉴权工具。

包含：
- 页面路由（登录 / 概览 / 转人工队列 / AI 对话调试页面）
- 鉴权工具函数（供子路由模块导入复用）
- create_admin_router 工厂（汇总页面路由 + AI 对话 API + 转人工 API）
"""

import hmac

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings
from app.service.admin import AdminService
from app.service.chat import ChatService
from app.service.transfer_manager import TransferManager

ADMIN_SESSION_MAX_AGE_SECONDS = 86400


def is_valid_admin_token(token: str | None) -> bool:
    expected = settings.ADMIN_API_TOKEN
    if not token or not expected:
        return False
    return hmac.compare_digest(token, expected)


def verify_token(
    request: Request, authorization: str | None = Header(default=None)
) -> None:
    if not has_admin_api_access(request, authorization):
        raise HTTPException(status_code=401, detail="未授权")


def require_admin_token(token: str | None) -> None:
    """共享的 admin Token 校验（供各子路由直接调用，缺失→401 / 无效→403）。

    使用 hmac.compare_digest 做定时安全比较，避免按字节比较泄漏 Token。
    """
    if not token:
        raise HTTPException(status_code=401, detail="Missing Token")
    if not is_valid_admin_token(token.replace("Bearer ", "")):
        raise HTTPException(status_code=403, detail="Invalid Token")


def check_login(request: Request) -> bool:
    token = request.cookies.get("admin_token")
    return is_valid_admin_token(token)


def has_admin_api_access(request: Request, authorization: str | None) -> bool:
    """同时兼容 Cookie 与 Bearer，避免登录态判断口径不一致。"""
    if check_login(request):
        return True
    if authorization and authorization.startswith("Bearer "):
        return is_valid_admin_token(authorization.removeprefix("Bearer "))
    return False


def create_admin_router(
    chat_service: ChatService,
    admin_service: AdminService,
    transfer_mgr: TransferManager,
) -> APIRouter:
    """工厂函数：注入依赖后返回完整路由实例（页面 + API）。"""
    from app.api.admin.dialog import create_dialog_router
    from app.api.admin.transfer import create_transfer_router

    router = APIRouter(tags=["admin"])

    router.include_router(create_dialog_router(chat_service, admin_service))
    router.include_router(
        create_transfer_router(transfer_mgr, admin_service, chat_service)
    )
    return router
