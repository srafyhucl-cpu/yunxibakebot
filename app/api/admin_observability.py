"""数据观察台后台路由。"""

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.service.observability import ObservabilityService

_jinja_env = Jinja2Templates(directory="app/templates")


def create_observability_router(service: ObservabilityService) -> APIRouter:
    """创建数据观察台路由。"""
    page_router = APIRouter(prefix="/admin/observability", tags=["admin-observability"])
    api_router = APIRouter(prefix="/api/v1/admin/observability", tags=["admin-observability-api"])
    root_router = APIRouter()

    def _check_login(request: Request) -> bool:
        token = request.cookies.get("admin_token")
        return bool(token and token == settings.ADMIN_API_TOKEN)

    def _verify_token(token: str | None) -> None:
        if not token:
            raise HTTPException(status_code=401, detail="Missing Token")
        if token.replace("Bearer ", "") != settings.ADMIN_API_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid Token")

    def _want_partial(request: Request) -> bool:
        return request.headers.get("X-Observability-Partial", "") == "1"

    def _render_observability_page(
        *,
        request: Request,
        template_name: str,
        panel_template: str,
        page_intro: str,
        context: dict,
    ) -> HTMLResponse:
        payload = {
            "request": request,
            "active": "observability",
            "panel_template": panel_template,
            "page_intro": page_intro,
            "current_url": str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
        }
        payload.update(context)
        if _want_partial(request):
            html = _jinja_env.get_template(panel_template).render(**payload)
            return HTMLResponse(content=html)
        html = _jinja_env.get_template(template_name).render(**payload)
        return HTMLResponse(content=html)

    @page_router.get("/current", response_class=HTMLResponse)
    async def current_page(
        request: Request,
        page: int = 1,
        view: str = "all",
        category: str = "",
        keyword: str = "",
        product_status: str = "",
    ):
        if not _check_login(request):
            return RedirectResponse(url="/admin/login", status_code=302)
        limit = 30
        offset = (page - 1) * limit
        items, total = await service.list_current_content(
            view=view,
            category=category,
            keyword=keyword,
            product_status=product_status,
            limit=limit,
            offset=offset,
        )
        return _render_observability_page(
            request=request,
            template_name="admin/observability_current.html",
            panel_template="admin/_observability_current_panel.html",
            page_intro="查看当前库里到底有什么、最后一次是从哪里写进来的。",
            context={
                "items": items,
                "page": page,
                "total": total,
                "total_pages": (total + limit - 1) // limit,
                "view": view,
                "category": category,
                "keyword": keyword,
                "product_status": product_status,
            },
        )

    @page_router.get("/history", response_class=HTMLResponse)
    async def history_page(
        request: Request,
        page: int = 1,
        date_from: str = "",
        date_to: str = "",
        source: str = "",
        status: str = "",
        entity_type: str = "",
        keyword: str = "",
    ):
        if not _check_login(request):
            return RedirectResponse(url="/admin/login", status_code=302)
        limit = 30
        offset = (page - 1) * limit
        items, total = await service.get_history(
            date_from=date_from,
            date_to=date_to,
            source=source,
            status=status,
            entity_type=entity_type,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )
        return _render_observability_page(
            request=request,
            template_name="admin/observability_history.html",
            panel_template="admin/_observability_history_panel.html",
            page_intro="查看真正发生写库的事件时间线，按来源和日期排查。",
            context={
                "items": items,
                "page": page,
                "total": total,
                "total_pages": (total + limit - 1) // limit,
                "date_from": date_from,
                "date_to": date_to,
                "source": source,
                "status": status,
                "entity_type": entity_type,
                "keyword": keyword,
            },
        )

    @page_router.get("/webhooks", response_class=HTMLResponse)
    async def webhooks_page(
        request: Request,
        page: int = 1,
        date_from: str = "",
        date_to: str = "",
        status: str = "",
        event_type: str = "",
        keyword: str = "",
    ):
        if not _check_login(request):
            return RedirectResponse(url="/admin/login", status_code=302)
        limit = 30
        offset = (page - 1) * limit
        items, total = await service.get_webhooks(
            date_from=date_from,
            date_to=date_to,
            status=status,
            event_type=event_type,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )
        return _render_observability_page(
            request=request,
            template_name="admin/observability_webhooks.html",
            panel_template="admin/_observability_webhooks_panel.html",
            page_intro="聚焦有赞 Webhook 处理情况，优先看失败、重复和处理中事件。",
            context={
                "items": items,
                "page": page,
                "total": total,
                "total_pages": (total + limit - 1) // limit,
                "date_from": date_from,
                "date_to": date_to,
                "status": status,
                "event_type": event_type,
                "keyword": keyword,
            },
        )

    @api_router.get("/current")
    async def current_api(
        authorization: str | None = Header(default=None),
        page: int = 1,
        view: str = "all",
        category: str = "",
        keyword: str = "",
        product_status: str = "",
    ) -> dict:
        _verify_token(authorization)
        limit = 30
        offset = (page - 1) * limit
        items, total = await service.list_current_content(
            view=view,
            category=category,
            keyword=keyword,
            product_status=product_status,
            limit=limit,
            offset=offset,
        )
        return {"code": 0, "total": total, "data": items}

    @api_router.get("/history")
    async def history_api(
        authorization: str | None = Header(default=None),
        page: int = 1,
        date_from: str = "",
        date_to: str = "",
        source: str = "",
        status: str = "",
        entity_type: str = "",
        keyword: str = "",
    ) -> dict:
        _verify_token(authorization)
        limit = 30
        offset = (page - 1) * limit
        items, total = await service.get_history(
            date_from=date_from,
            date_to=date_to,
            source=source,
            status=status,
            entity_type=entity_type,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )
        return {"code": 0, "total": total, "data": items}

    @api_router.get("/history/{entry_id}")
    async def history_detail_api(
        entry_id: int,
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        entry = await service.get_history_detail(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Not Found")
        return {"code": 0, "data": entry}

    @api_router.get("/webhooks")
    async def webhooks_api(
        authorization: str | None = Header(default=None),
        page: int = 1,
        date_from: str = "",
        date_to: str = "",
        status: str = "",
        event_type: str = "",
        keyword: str = "",
    ) -> dict:
        _verify_token(authorization)
        limit = 30
        offset = (page - 1) * limit
        items, total = await service.get_webhooks(
            date_from=date_from,
            date_to=date_to,
            status=status,
            event_type=event_type,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )
        return {"code": 0, "total": total, "data": items}

    @api_router.get("/webhooks/{event_id}")
    async def webhook_detail_api(
        event_id: int,
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        entry = await service.get_webhook_detail(event_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Not Found")
        return {"code": 0, "data": entry}

    root_router.include_router(page_router)
    root_router.include_router(api_router)
    return root_router
