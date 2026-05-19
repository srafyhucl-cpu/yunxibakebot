"""
店铺配置管理路由。

包含：
- 主推款管理页面与 API（Issue 1）
- 商品上下架管理页面与 API（Issue 3）
"""

import json
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader

from app.config import settings
from app.models.config import FEATURED_PRODUCTS_KEY
from app.repository.config_repo import ConfigRepo
from app.repository.knowledge_repo import KnowledgeRepo

BASE_DIR = Path(__file__).resolve().parent.parent
_jinja_env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")), cache_size=0)

_api_router = APIRouter(prefix="/api/v1/admin", tags=["shop-config"])


def _check_login(request: Request) -> bool:
    return bool(request.cookies.get("admin_token"))


def _verify_token(authorization: str | None = Header(default=None)) -> None:
    if not settings.ADMIN_API_TOKEN:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    if authorization.removeprefix("Bearer ") != settings.ADMIN_API_TOKEN:
        raise HTTPException(status_code=403, detail="Token 无效")


def create_shop_config_router(
    config_repo: ConfigRepo,
    knowledge_repo: KnowledgeRepo,
) -> APIRouter:
    """工厂函数：注入依赖后返回路由实例。"""
    router = APIRouter(tags=["shop-config"])

    # ────────────── 主推款页面 ──────────────

    @router.get("/admin/featured-products", response_class=HTMLResponse)
    async def featured_products_page(request: Request):
        if not _check_login(request):
            return RedirectResponse(url="/admin/login", status_code=302)
        products = await config_repo.get_list(FEATURED_PRODUCTS_KEY)
        html = _jinja_env.get_template("admin/featured_products.html").render(
            request=request, active="featured_products", products=products,
        )
        return HTMLResponse(html)

    # ────────────── 商品管理页面 ──────────────

    @router.get("/admin/products", response_class=HTMLResponse)
    async def products_page(request: Request, search: str = "", page: int = 1):
        if not _check_login(request):
            return RedirectResponse(url="/admin/login", status_code=302)
        limit = 30
        offset = (page - 1) * limit
        entries = await knowledge_repo.get_all_products(search=search, limit=limit, offset=offset)
        total = await knowledge_repo.count_products(search=search)
        html = _jinja_env.get_template("admin/products.html").render(
            request=request, active="products",
            entries=entries, search=search,
            page=page, total=total, limit=limit,
            total_pages=(total + limit - 1) // limit,
        )
        return HTMLResponse(html)

    # ────────────── 主推款 API ──────────────

    @_api_router.get("/shop-config/featured-products")
    async def get_featured_products(
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        return {"code": 0, "data": await config_repo.get_list(FEATURED_PRODUCTS_KEY)}

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
        await config_repo.set_list(FEATURED_PRODUCTS_KEY, products)
        return {"code": 0, "message": "已保存", "data": products}

    # ────────────── 商品上下架 API ──────────────

    @_api_router.get("/products")
    async def list_products(
        search: str = "",
        page: int = 1,
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        limit = 30
        offset = (page - 1) * limit
        entries = await knowledge_repo.get_all_products(search=search, limit=limit, offset=offset)
        total = await knowledge_repo.count_products(search=search)
        return {"code": 0, "total": total, "data": [
            {
                "id": e.id,
                "category": e.category,
                "title": e.title,
                "is_active": bool(e.is_active),
                "updated_at": e.updated_at,
            }
            for e in entries
        ]}

    @_api_router.post("/products/{product_id}/toggle")
    async def toggle_product(
        product_id: int,
        authorization: str | None = Header(default=None),
    ) -> dict:
        _verify_token(authorization)
        entry = await knowledge_repo.get_by_id(product_id)
        if not entry:
            raise HTTPException(status_code=404, detail="条目不存在")
        new_status = not bool(entry.is_active)
        await knowledge_repo.update_active(product_id, new_status)
        return {"code": 0, "is_active": new_status, "title": entry.title}

    router.include_router(_api_router)
    return router
