"""
新后台前端入口路由。

职责：
- 提供 `/admin-v2` 的静态资源访问
- 为 SPA 路由刷新提供 fallback
- 在前端尚未构建时返回明确提示
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse


BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIST_DIR = BASE_DIR / "web" / "admin" / "dist"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"
INDEX_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


def create_admin_frontend_router() -> APIRouter:
    router = APIRouter(tags=["admin-frontend"])

    @router.get("/admin", response_class=HTMLResponse)
    @router.get("/admin/{asset_path:path}", response_class=HTMLResponse)
    async def admin_entry(asset_path: str = ""):
        if not FRONTEND_INDEX_FILE.exists():
            return HTMLResponse(
                content=(
                    "<h1>admin 尚未构建</h1>"
                    "<p>请先在 web/admin 下执行 npm install 与 npm run build，"
                    "或直接启动 Vite 开发服务。</p>"
                ),
                status_code=503,
                headers=INDEX_CACHE_HEADERS,
            )

        requested_path = (FRONTEND_DIST_DIR / asset_path).resolve()
        if asset_path:
            try:
                requested_path.relative_to(FRONTEND_DIST_DIR.resolve())
            except ValueError:
                return HTMLResponse(content="非法路径", status_code=400)

            if requested_path.exists() and requested_path.is_file():
                return FileResponse(str(requested_path))

        return FileResponse(str(FRONTEND_INDEX_FILE), headers=INDEX_CACHE_HEADERS)

    return router
