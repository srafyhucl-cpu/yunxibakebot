"""
管理后台。

包含：
- 页面路由（登录 / 概览 / 转人工队列）
- API 路由（转人工 CRUD、会话查询、人工回复）
页面使用 Session Cookie 鉴权，API 使用 Bearer Token 鉴权。
"""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader

from app.config import settings
from app.logger import setup_logger
from app.repository.knowledge_repo import KnowledgeRepo
from app.repository.message_repo import MessageRepo
from app.repository.session_repo import SessionRepo
from app.repository.transfer_repo import TransferRepo
from app.service.chat import ChatService
from app.service.transfer_manager import TransferManager

# 模板引擎（独立初始化，避免 Starlette Jinja2Templates 兼容问题）
BASE_DIR = Path(__file__).resolve().parent.parent
_jinja_env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")), cache_size=0)

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
    message_repo: MessageRepo,
    transfer_repo: TransferRepo,
    knowledge_repo: KnowledgeRepo | None = None,
) -> APIRouter:
    """工厂函数：注入依赖后返回路由实例。"""
    transfer_mgr = TransferManager(transfer_repo)
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
    @api_router.get("/chat-test/sessions", dependencies=[Depends(verify_token)])
    async def list_saved_sessions() -> dict:
        """获取已保存（有名称）的对话列表。"""
        sessions = await session_repo.get_named(channel="admin_test")
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
        session = await session_repo.get(session_id)
        if not session:
            return {"code": 404, "message": "会话不存在"}
        extra = json.loads(session.extra_info or "{}")
        extra["name"] = name
        await session_repo.update_extra(session_id, json.dumps(extra, ensure_ascii=False))
        return {"code": 0, "message": "已保存"}

    @api_router.delete("/chat-test/session/{session_id}", dependencies=[Depends(verify_token)])
    async def discard_session(session_id: str) -> dict:
        """丢弃一个对话。"""
        session = await session_repo.get(session_id)
        if not session:
            return {"code": 404, "message": "会话不存在"}
        await session_repo.update_status(session_id, "closed")
        return {"code": 0, "message": "已丢弃"}

    # ── 对话测试 API ──
    @api_router.get("/chat-test/messages", dependencies=[Depends(verify_token)])
    async def chat_test_history(user_id: str = "admin_tester") -> dict:
        """获取对话测试的历史消息。"""
        session = await session_repo.get_active(user_id, "admin_test")
        if not session:
            return {"code": 0, "data": []}
        from app.models.message import MessageRole
        msgs = await message_repo.get_by_session(session.id)
        return {"code": 0, "data": [
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
        # 运费关键词直接返回固定话术，不走 LLM
        SHIPPING_KEYWORDS = ["运费", "邮费", "配送费"]
        if any(kw in content for kw in SHIPPING_KEYWORDS):
            return {"code": 0, "reply": "运费的话统一回复您：运费由顾客按实际路程支付，下单时确认就好~😊", "intent": 2}

        from app.service.llm.intent import detect_intent
        intent = await detect_intent(content)
        test_user = body.get("user_id", "admin_tester")
        if test_user == "admin_tester":
            s = await session_repo.get_active("admin_tester", "admin_test")
            if s and s.status in ("transfer_pending", "human_service"):
                await session_repo.update_status(s.id, "active")
        if intent == 2:
            return {"code": 0, "reply": "运费的话统一回复您：运费由顾客按实际路程支付，下单时确认就好~😊", "intent": 2}
        if intent == 4:
            return {"code": 0, "reply": "非常抱歉给您带来不好的体验，已为您转接人工客服，请稍候~", "intent": 4}
        reply = await chat_service.handle_message(
            channel="admin_test",
            user_id=test_user,
            channel_msg_id=str(uuid.uuid4()),
            content=content,
        )
        # 获取当前会话 ID
        session = await session_repo.get_active(test_user, "admin_test")
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
        msgs = await message_repo.get_by_session(session_id)
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
