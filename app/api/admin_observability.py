"""数据观察台后台路由。"""

from fastapi import APIRouter, Depends, Header, HTTPException, Request


from app.api.admin import verify_token
from app.service.observability import ObservabilityService




def create_observability_router(service: ObservabilityService) -> APIRouter:
    """创建数据观察台路由。"""
    api_router = APIRouter(prefix="/api/v1/admin/observability", tags=["admin-observability-api"], dependencies=[Depends(verify_token)])
    root_router = APIRouter()


    @api_router.get("/current")
    async def current_api(
        authorization: str | None = Header(default=None),
        page: int = 1,
        view: str = "all",
        category: str = "",
        keyword: str = "",
        product_status: str = "",
    ) -> dict:

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

        entry = await service.get_webhook_detail(event_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Not Found")
        return {"code": 0, "data": entry}


    root_router.include_router(api_router)
    return root_router
