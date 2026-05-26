"""
管理后台。

包含：
- 页面路由（登录 / 概览 / 转人工队列）
- API 路由（转人工 CRUD、会话查询、人工回复）
页面使用 Session Cookie 鉴权，API 使用 Bearer Token 鉴权。
"""

import json
import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings
from app.logger import setup_logger
from app.service.admin import AdminService
from app.service.chat import ChatService
from app.service.transfer_manager import TransferManager

# 模板引擎（独立初始化，避免 Starlette Jinja2Templates 兼容问题）
BASE_DIR = Path(__file__).resolve().parent.parent
_jinja_env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    cache_size=0,
    autoescape=select_autoescape(["html"]),
)

logger = setup_logger()
ADMIN_CHAT_TEST_TIMEOUT_SECONDS = 35.0

# ── API 路由 ──
api_router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def is_valid_admin_token(token: str | None) -> bool:
    return bool(token and settings.ADMIN_API_TOKEN and token == settings.ADMIN_API_TOKEN)


def verify_token(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    token = authorization.removeprefix("Bearer ")
    if not is_valid_admin_token(token):
        raise HTTPException(status_code=403, detail="Token 无效")


# ── 页面鉴权 ──
def check_login(request: Request) -> bool:
    token = request.cookies.get("admin_token")
    return is_valid_admin_token(token)


def has_admin_api_access(request: Request, authorization: str | None) -> bool:
    """新后台初始化阶段同时兼容 Cookie 与 Bearer，避免登录态判断口径不一致。"""
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
    """工厂函数：注入依赖后返回路由实例。"""
    router = APIRouter(tags=["admin"])

    # ────────────────────────────── 页面路由 ──────────────────────────────

    @router.get("/admin", response_class=HTMLResponse)
    async def admin_index(request: Request):
        return RedirectResponse(url="/admin/chat-test")

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
        resp.set_cookie(key="admin_token", value=settings.ADMIN_API_TOKEN, max_age=86400, httponly=False, samesite="strict")
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

    # ── 对话测试页 ──
    @router.get("/admin/chat-test", response_class=HTMLResponse)
    async def chat_test_page(request: Request):
        if not check_login(request):
            return RedirectResponse(url="/admin/login", status_code=302)
        html = _jinja_env.get_template("admin/chat_test.html").render(
            request=request, active="chat_test",
        )
        return HTMLResponse(html)

    # ── 对话管理 API ──
    @api_router.get("/auth/me")
    async def auth_me(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict:
        if not has_admin_api_access(request, authorization):
            raise HTTPException(status_code=401, detail="未登录或登录已过期")
        return {
            "ok": True,
            "data": {
                "name": "管理员",
                "role": "admin",
            },
        }

    @api_router.post("/auth/login")
    async def auth_login(request: Request) -> JSONResponse:
        body = await request.json()
        token = str(body.get("token", "")).strip()
        if not is_valid_admin_token(token):
            raise HTTPException(status_code=401, detail="Token 无效")

        response = JSONResponse(
            {
                "ok": True,
                "message": "登录成功",
                "data": {
                    "name": "管理员",
                    "role": "admin",
                },
            },
        )
        response.set_cookie(
            key="admin_token",
            value=settings.ADMIN_API_TOKEN,
            max_age=86400,
            httponly=False,
            samesite="strict",
        )
        return response

    @api_router.post("/auth/logout")
    async def auth_logout() -> JSONResponse:
        response = JSONResponse({"ok": True, "message": "已退出登录"})
        response.delete_cookie("admin_token")
        return response

    @api_router.get("/chat-test/sessions", dependencies=[Depends(verify_token)])
    async def list_saved_sessions() -> dict:
        """获取已保存（有名称）的对话列表。"""
        sessions = await admin_service.get_named(channel="admin_test")
        return {"code": 0, "data": [
            {
                "id": s.id,
                "name": json.loads(s.extra_info).get("name", "未命名"),
                "user_id": s.user_id,
                "msg_count": 0,
                "created_at": s.created_at,
            }
            for s in sessions
        ]}

    @api_router.post("/chat-test/save", dependencies=[Depends(verify_token)])
    async def save_session(request: Request) -> dict:
        """保存/命名一个对话。"""
        import json
        raw = await request.body()
        body = json.loads(raw.decode("utf-8"))
        session_id = body.get("session_id", "")
        name = body.get("name", "").strip()
        if not session_id or not name:
            return {"code": 422, "message": "参数不完整"}
        session = await admin_service.get(session_id)
        if not session:
            return {"code": 404, "message": "会话不存在"}
        extra = json.loads(session.extra_info or "{}")
        extra["name"] = name
        await admin_service.update_extra(session_id, json.dumps(extra, ensure_ascii=False))
        return {"code": 0, "message": "已保存"}

    @api_router.delete("/chat-test/session/{session_id}", dependencies=[Depends(verify_token)])
    async def discard_session(session_id: str) -> dict:
        """丢弃一个对话。"""
        session = await admin_service.get(session_id)
        if not session:
            return {"code": 404, "message": "会话不存在"}
        await admin_service.update_status(session_id, "closed")
        return {"code": 0, "message": "已丢弃"}

    # ── 对话测试 API ──
    @api_router.get("/chat-test/messages", dependencies=[Depends(verify_token)])
    async def chat_test_history(user_id: str = "admin_tester") -> dict:
        """获取对话测试的历史消息。"""
        session = await admin_service.get_active(user_id, "admin_test")
        if not session:
            return {"code": 0, "data": []}
        msgs = await admin_service.get_by_session(session.id)
        return {"code": 0, "session_id": session.id, "data": [
            {
                "role": m.role.value if hasattr(m.role, "value") else m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in msgs
        ]}

    @api_router.post("/chat-test", dependencies=[Depends(verify_token)])
    async def chat_test_api(request: Request) -> dict:
        import json
        raw = await request.body()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("gbk")
        body = json.loads(text)
        content = body.get("content", "").strip()
        if not content:
            return {"code": 422, "message": "内容不能为空"}
        from app.service.llm.intent import detect_intent
        intent = await detect_intent(content)
        test_user = body.get("user_id", "admin_tester")
        s = await admin_service.get_active(test_user, "admin_test")
        if s and s.status in ("transfer_pending", "human_service"):
            await admin_service.update_status(s.id, "active")
        try:
            reply = await asyncio.wait_for(
                chat_service.handle_message(
                    channel="admin_test",
                    user_id=test_user,
                    channel_msg_id=str(uuid.uuid4()),
                    content=content,
                ),
                timeout=ADMIN_CHAT_TEST_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            logger.error("后台 AI 测试接口超时: user=%s content=%s", test_user, content[:80])
            return {
                "code": 0,
                "reply": "查询超时了，当前大模型服务响应较慢。请稍后重试，或直接联系人工确认订单配送时间。",
                "intent": intent,
                "session_id": s.id if s else "",
            }
        # 获取当前会话 ID
        session = await admin_service.get_active(test_user, "admin_test")
        session_id = session.id if session else ""
        # 清理 Markdown 星号
        clean = (reply or "(无回复)").replace("**", "").replace("*", "")
        return {"code": 0, "reply": clean, "intent": intent, "session_id": session_id}

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

    @api_router.get("/sessions/{session_id}/messages", dependencies=[Depends(verify_token)])
    async def get_session_messages(session_id: str) -> dict:
        """获取某会话的消息列表。"""
        msgs = await admin_service.get_by_session(session_id)
        return {"code": 0, "data": [
            {
                "role": m.role.value if hasattr(m.role, "value") else m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in msgs
        ]}

    @api_router.get("/sessions", dependencies=[Depends(verify_token)])
    async def list_sessions() -> dict:
        return {"code": 0, "data": [], "message": "功能开发中"}

    # 合并路由
    router.include_router(api_router)
    return router
