"""知识配置后台页面与 API。"""

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.models.knowledge_admin import KnowledgeAdminDraft
from app.service.knowledge_admin import KnowledgeAdminService

_jinja_env = Jinja2Templates(directory="app/templates")
_DEFAULT_OPERATOR = "admin"


def create_admin_knowledge_router(service: KnowledgeAdminService) -> APIRouter:
    """创建知识配置后台路由。"""

    page_router = APIRouter(prefix="/admin/knowledge-config", tags=["admin-knowledge"])
    api_router = APIRouter(prefix="/api/v1/admin/knowledge-config", tags=["admin-knowledge-api"])
    root_router = APIRouter()

    def _check_login(request: Request) -> bool:
        token = request.cookies.get("admin_token")
        return bool(token and token == settings.ADMIN_API_TOKEN)

    def _verify_token(token: str | None) -> None:
        if not token:
            raise HTTPException(status_code=401, detail="Missing Token")
        if token.replace("Bearer ", "") != settings.ADMIN_API_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid Token")

    def _build_draft(body: dict) -> KnowledgeAdminDraft:
        try:
            priority = int(body.get("priority", 50))
        except (TypeError, ValueError) as exc:
            raise ValueError("优先级必须是数字") from exc
        return KnowledgeAdminDraft(
            title=str(body.get("title", "")),
            content=str(body.get("content", "")),
            content_type=str(body.get("content_type", "")),
            keywords=str(body.get("keywords", "")),
            priority=priority,
            is_active=bool(body.get("is_active", True)),
        )

    def _serialize_entry(entry) -> dict:
        return {
            "id": entry.id,
            "category": entry.category,
            "content_type": entry.content_type,
            "title": entry.title,
            "content": entry.content,
            "keywords": entry.keywords,
            "priority": entry.priority,
            "is_active": bool(entry.is_active),
            "content_origin": entry.content_origin,
            "created_by": entry.created_by,
            "updated_by": entry.updated_by,
            "suggested_category": entry.suggested_category,
            "suggest_reason": entry.suggest_reason,
            "last_sync_source": entry.last_sync_source,
            "last_sync_ref": entry.last_sync_ref,
            "vector_sync_status": entry.vector_sync_status,
            "vector_synced_at": entry.vector_synced_at,
            "vector_sync_error": entry.vector_sync_error,
            "vector_sync_retry_count": entry.vector_sync_retry_count,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
        }

    @page_router.get("", response_class=HTMLResponse)
    async def knowledge_page(request: Request):
        if not _check_login(request):
            return RedirectResponse(url="/admin/login", status_code=302)
        html = _jinja_env.get_template("admin/knowledge_config.html").render(
            request=request,
            active="knowledge_config",
        )
        return HTMLResponse(content=html)

    @api_router.get("/entries")
    async def list_entries(
        page: int = 1,
        content_type: str = "",
        is_active: str = "",
        vector_status: str = "",
        keyword: str = "",
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        limit = 20
        safe_page = max(page, 1)
        offset = (safe_page - 1) * limit
        entries = await service.list_entries(
            content_type=content_type,
            is_active=is_active,
            vector_status=vector_status,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )
        total = await service.count_entries(
            content_type=content_type,
            is_active=is_active,
            vector_status=vector_status,
            keyword=keyword,
        )
        return {
            "code": 0,
            "data": [_serialize_entry(entry) for entry in entries],
            "pagination": {
                "page": safe_page,
                "page_size": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit,
            },
        }

    @api_router.get("/entries/{entry_id}")
    async def get_entry_detail(
        entry_id: int,
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        detail = await service.get_entry_detail(entry_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="知识条目不存在")
        return {
            "code": 0,
            "data": {
                "entry": _serialize_entry(detail["entry"]),
                "history": detail["history"],
            },
        }

    @api_router.post("/entries")
    async def create_entry(request: Request, authorization: str | None = Header(default=None)) -> dict:
        _verify_token(authorization)
        body = await request.json()
        try:
            entry = await service.create_entry(_build_draft(body), operator=_DEFAULT_OPERATOR)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"code": 0, "data": _serialize_entry(entry)}

    @api_router.put("/entries/{entry_id}")
    async def update_entry(
        entry_id: int,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        body = await request.json()
        try:
            entry = await service.update_entry(entry_id, _build_draft(body), operator=_DEFAULT_OPERATOR)
        except ValueError as exc:
            message = str(exc)
            if "不存在" in message:
                raise HTTPException(status_code=404, detail=message) from exc
            raise HTTPException(status_code=422, detail=message) from exc
        return {"code": 0, "data": _serialize_entry(entry)}

    @api_router.post("/entries/{entry_id}/toggle-active")
    async def toggle_active(
        entry_id: int,
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        try:
            entry = await service.toggle_active(entry_id, operator=_DEFAULT_OPERATOR)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"code": 0, "data": _serialize_entry(entry)}

    @api_router.post("/entries/{entry_id}/retry-sync")
    async def retry_sync(
        entry_id: int,
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        try:
            entry = await service.retry_sync(entry_id, operator=_DEFAULT_OPERATOR)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"code": 0, "data": _serialize_entry(entry)}

    @api_router.post("/suggest-category")
    async def suggest_category(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        body = await request.json()
        suggestion = service.suggest_category(
            title=str(body.get("title", "")),
            content=str(body.get("content", "")),
        )
        return {
            "code": 0,
            "data": {
                "content_type": suggestion.content_type,
                "label": suggestion.label,
                "reason": suggestion.reason,
            },
        }

    root_router.include_router(page_router)
    root_router.include_router(api_router)
    return root_router
