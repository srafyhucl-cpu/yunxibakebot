"""
管理后台页面路由与鉴权工具。

包含：
- 页面路由（登录 / 概览 / 转人工队列 / AI 对话调试页面）
- 鉴权工具函数（供子路由模块导入复用）
- create_admin_router 工厂（汇总页面路由 + AI 对话 API + 转人工 API）
"""

from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings
from app.service.admin import AdminService
from app.service.chat import ChatService
from app.service.transfer_manager import TransferManager

BASE_DIR = Path(__file__).resolve().parent.parent
_jinja_env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    cache_size=0,
    autoescape=select_autoescape(["html"]),
)

ADMIN_SESSION_MAX_AGE_SECONDS = 86400


def is_valid_admin_token(token: str | None) -> bool:
    return bool(token and settings.ADMIN_API_TOKEN and token == settings.ADMIN_API_TOKEN)


def verify_token(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    token = authorization.removeprefix("Bearer ")
    if not is_valid_admin_token(token):
        raise HTTPException(status_code=403, detail="Token 无效")


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
    from app.api.admin_dialog import create_dialog_router
    from app.api.admin_transfer import create_transfer_router

    router = APIRouter(tags=["admin"])

    @router.get("/admin", response_class=HTMLResponse)
    async def admin_index(request: Request):
        return RedirectResponse(url="/admin/ai-dialog")

    @router.get("/admin/login", response_class=HTMLResponse)
    async def login_page(request: Request, error: str = ""):
        html = _jinja_env.get_template("admin/login.html").render(
            request=request, error=error,
        )
        return HTMLResponse(html)

    @router.post("/admin/login")
    async def login_submit(request: Request):
        form = await request.form()
        token = form.get("token", "")
        if token != settings.ADMIN_API_TOKEN:
            html = _jinja_env.get_template("admin/login.html").render(
                request=request, error="密码错误",
            )
            return HTMLResponse(html)
        resp = RedirectResponse(url="/admin/dashboard", status_code=302)
        resp.set_cookie(
            key="admin_token", value=settings.ADMIN_API_TOKEN,
            max_age=ADMIN_SESSION_MAX_AGE_SECONDS, httponly=False, samesite="strict",
        )
        return resp

    @router.get("/admin/logout")
    async def logout():
        resp = RedirectResponse(url="/admin/login", status_code=302)
        resp.delete_cookie("admin_token")
        return resp

    @router.get("/admin/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request):
        if not check_login(request):
            return RedirectResponse(url="/admin/login", status_code=302)
        pending = await transfer_mgr.get_pending()
        active = await admin_service.get_all_active()
        kb_count = await admin_service.count_knowledge()
        html = _jinja_env.get_template("admin/dashboard.html").render(
            request=request, active="dashboard",
            pending_count=len(pending),
            active_sessions=len(active),
            kb_count=kb_count,
        )
        return HTMLResponse(html)

    @router.get("/admin/transfers", response_class=HTMLResponse)
    async def transfers_page(request: Request):
        if not check_login(request):
            return RedirectResponse(url="/admin/login", status_code=302)
        pending = await transfer_mgr.get_pending()
        recent = await admin_service.get_recent(limit=10)
        transfer_list = []
        for t in pending:
            session = await admin_service.get(t.session_id)
            transfer_list.append({
                "id": t.id,
                "user_id": t.user_id,
                "channel": session.channel if session else "小程序",
                "reason": t.reason,
                "wait_time": "待计算",
            })
        html = _jinja_env.get_template("admin/transfers.html").render(
            request=request, active="transfers",
            transfers=transfer_list,
            recent_sessions=recent,
        )
        return HTMLResponse(html)

    @router.get("/admin/ai-dialog", response_class=HTMLResponse)
    async def ai_dialog_page(request: Request):
        if not check_login(request):
            return RedirectResponse(url="/admin/login", status_code=302)
        html = _jinja_env.get_template("admin/ai_dialog.html").render(
            request=request, active="ai_dialog",
        )
        return HTMLResponse(html)

    router.include_router(create_dialog_router(chat_service, admin_service))
    router.include_router(create_transfer_router(transfer_mgr, admin_service, chat_service))
    return router
