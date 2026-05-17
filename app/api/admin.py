"""
管理后台。

包含：
- 页面路由（登录 / 概览 / 转人工队列）
- API 路由（转人工 CRUD、会话查询、人工回复）
页面使用 Session Cookie 鉴权，API 使用 Bearer Token 鉴权。
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader

from app.config import settings
from app.logger import setup_logger
from app.repository.knowledge_repo import KnowledgeRepo
from app.repository.session_repo import SessionRepo
from app.repository.transfer_repo import TransferRepo
from app.service.chat import ChatService
from app.service.transfer_manager import TransferManager

# 模板引擎（独立初始化，避免 Starlette Jinja2Templates 兼容问题）
BASE_DIR = Path(__file__).resolve().parent.parent
_jinja_env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")))

logger = setup_logger()

# ── API 路由 ──
api_router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def verify_token(authorization: str | None = Header(default=None)) -> None:
    if not settings.ADMIN_API_TOKEN:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    token = authorization.removeprefix("Bearer ")
    if token != settings.ADMIN_API_TOKEN:
        raise HTTPException(status_code=403, detail="Token 无效")


# ── 页面鉴权 ──
def check_login(request: Request) -> str | None:
    return request.cookies.get("admin_token")


def create_admin_router(
    chat_service: ChatService,
    session_repo: SessionRepo,
    transfer_repo: TransferRepo,
    knowledge_repo: KnowledgeRepo | None = None,
) -> APIRouter:
    """工厂函数：注入依赖后返回路由实例。"""
    transfer_mgr = TransferManager(transfer_repo)
    router = APIRouter(tags=["admin"])

    # ────────────────────────────── 页面路由 ──────────────────────────────

    @router.get("/admin", response_class=HTMLResponse)
    async def admin_index(request: Request):
        return RedirectResponse(url="/admin/dashboard")

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
        resp.set_cookie(key="admin_token", value="logged_in", max_age=86400)
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
        active = await session_repo.get_all_active()
        kb_count = await knowledge_repo.count_all() if knowledge_repo else 0
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
        recent = await session_repo.get_recent(limit=10)
        transfer_list = []
        for t in pending:
            session = await session_repo.get(t.session_id)
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

    # ────────────────────────────── API 路由 ──────────────────────────────

    @api_router.get("/transfers/pending", dependencies=[Depends(verify_token)])
    async def list_pending_transfers() -> dict:
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

    @api_router.post("/transfers/{transfer_id}/accept", dependencies=[Depends(verify_token)])
    async def accept_transfer(transfer_id: str, staff_id: str = "") -> dict:
        await transfer_mgr.accept_transfer(transfer_id, staff_id)
        return {"code": 0, "message": "已接单"}

    @api_router.post("/transfers/{transfer_id}/close", dependencies=[Depends(verify_token)])
    async def close_transfer(transfer_id: str) -> dict:
        await transfer_mgr.close_transfer(transfer_id)
        return {"code": 0, "message": "已关闭"}

    @api_router.post("/sessions/{session_id}/reply", dependencies=[Depends(verify_token)])
    async def human_reply(session_id: str, content: str) -> dict:
        if not content.strip():
            raise HTTPException(status_code=422, detail="回复内容不能为空")
        await chat_service.handle_human_reply(session_id, content)
        return {"code": 0, "message": "已发送"}

    @api_router.get("/sessions", dependencies=[Depends(verify_token)])
    async def list_sessions() -> dict:
        return {"code": 0, "data": [], "message": "功能开发中"}

    # 合并路由
    router.include_router(api_router)
    return router
