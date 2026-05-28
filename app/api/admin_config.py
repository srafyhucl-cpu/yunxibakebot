"""
店铺配置管理路由。

包含：
- 主推款管理页面与 API（Issue 1）
- 商品上下架管理页面与 API（Issue 3）
"""

import json

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.service.admin import AdminService

_jinja_env = Jinja2Templates(directory="app/templates")

router = APIRouter(tags=["admin-config"])
_api_router = APIRouter(prefix="/api/v1/admin")


def create_shop_config_router(admin_service: AdminService) -> APIRouter:
    """创建店铺配置相关路由。"""

    def _check_login(request: Request) -> bool:
        token = request.cookies.get("admin_token")
        return bool(token and token == settings.ADMIN_API_TOKEN)

    def _verify_token(token: str | None) -> None:
        if not token:
            raise HTTPException(status_code=401, detail="Missing Token")
        if token.replace("Bearer ", "") != settings.ADMIN_API_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid Token")

    # ────────────── 页面路由 ──────────────

    @router.get("/admin/featured-products", response_class=HTMLResponse)
    async def featured_products_page(request: Request):
        if not _check_login(request):
            return RedirectResponse(url="/admin/login", status_code=302)
        products = await admin_service.get_featured_products()
        html = _jinja_env.get_template("admin/featured_products.html").render(
            request=request, active="featured_products", products=products,
        )
        return HTMLResponse(content=html)

    @router.get("/admin/products", response_class=HTMLResponse)
    async def products_page(request: Request, page: int = 1, search: str = ""):
        if not _check_login(request):
            return RedirectResponse(url="/admin/login", status_code=302)
        limit = 30
        offset = (page - 1) * limit
        entries = await admin_service.get_all_products(search=search, limit=limit, offset=offset)
        total = await admin_service.count_products(search=search)
        html = _jinja_env.get_template("admin/products.html").render(
            request=request, active="products",
            entries=entries, search=search,
            page=page, total_pages=(total + limit - 1) // limit,
        )
        return HTMLResponse(content=html)

    # ────────────── 主推款配置 API ──────────────

    @_api_router.get("/shop-config/featured-products")
    async def get_featured_products(
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        return {"code": 0, "data": await admin_service.get_featured_products()}

    @_api_router.post("/shop-config/featured-products")
    async def set_featured_products(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        raw = await request.body()
        body = json.loads(raw.decode("utf-8"))
        products: list[str] = body.get("products", [])
        products = [p.strip() for p in products if p.strip()]
        await admin_service.set_featured_products(products)
        return {"code": 0, "message": "已保存", "data": products}

    # ────────────── 商品上下架 API ──────────────

    @_api_router.get("/products")
    async def get_products(
        page: int = 1,
        search: str = "",
        is_active: str = "",
        sync_source: str = "",
        vector_sync_status: str = "",
        featured_only: bool = False,
        youzan_item_id: str = "",
        keyword_filter: str = "",
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        limit = 30
        offset = (page - 1) * limit
        active_filter: int | None = None
        if is_active == "1":
            active_filter = 1
        elif is_active == "0":
            active_filter = 0
        featured_filter: list[str] | None = None
        if featured_only:
            featured_filter = await admin_service.get_featured_products()
        entries = await admin_service.get_all_products(
            search=search, limit=limit, offset=offset,
            is_active=active_filter, sync_source=sync_source,
            vector_sync_status=vector_sync_status,
            featured_titles=featured_filter,
            youzan_item_id_filter=youzan_item_id,
            keyword_filter=keyword_filter,
        )
        total = await admin_service.count_products(
            search=search, is_active=active_filter, sync_source=sync_source,
            vector_sync_status=vector_sync_status,
            featured_titles=featured_filter,
            youzan_item_id_filter=youzan_item_id,
            keyword_filter=keyword_filter,
        )
        total_active = await admin_service.count_products(is_active=1)
        total_inactive = await admin_service.count_products(is_active=0)
        youzan_ids = [e.youzan_item_id for e in entries if e.youzan_item_id]
        price_stock_map = await admin_service.get_prices_and_stocks(youzan_ids)
        return {"code": 0, "total": total, "total_active": total_active, "total_inactive": total_inactive, "data": [
            {
                "id": e.id,
                "category": e.category,
                "content_type": e.content_type,
                "title": e.title,
                "content": e.content,
                "keywords": e.keywords,
                "priority": e.priority,
                "is_active": e.is_active,
                "youzan_item_id": e.youzan_item_id,
                "last_sync_source": e.last_sync_source,
                "last_sync_ref": e.last_sync_ref,
                "vector_sync_status": e.vector_sync_status,
                "updated_at": e.updated_at,
                "price_fen": price_stock_map.get(e.youzan_item_id or "", {}).get("price_fen"),
                "stock": price_stock_map.get(e.youzan_item_id or "", {}).get("stock"),
                "sold_num": price_stock_map.get(e.youzan_item_id or "", {}).get("sold_num", 0),
            }
            for e in entries
        ], "page": page, "page_size": limit}

    @_api_router.post("/products/{product_id}/toggle-active")
    async def toggle_product_active(
        product_id: int,
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        entry = await admin_service.get_product(product_id)
        if not entry:
            raise HTTPException(status_code=404, detail="条目不存在")
        new_status = await admin_service.toggle_product_active(product_id)
        return {"code": 0, "is_active": new_status, "title": entry.title}

    @_api_router.get("/settings/summary")
    async def get_settings_summary(
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        return {"code": 0, "data": await admin_service.get_settings_summary()}

    router.include_router(_api_router)
    return router
