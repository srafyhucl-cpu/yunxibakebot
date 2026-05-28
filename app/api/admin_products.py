"""
商品管理后台 API 路由。

职责：
- 提供商品全量对账触发接口
"""

from fastapi import APIRouter, Header, HTTPException

from app.service.youzan.product_reconciler import ProductReconcileService


def create_admin_products_router(reconcile_service: ProductReconcileService) -> APIRouter:
    """创建商品管理 API 路由。"""
    router = APIRouter(prefix="/api/v1/admin/products", tags=["admin-products"])

    def _verify_token(token: str | None) -> None:
        from app.config import settings
        if not token:
            raise HTTPException(status_code=401, detail="Missing Token")
        if token.replace("Bearer ", "") != settings.ADMIN_API_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid Token")

    @router.post("/reconcile")
    async def trigger_reconcile(
        authorization: str | None = Header(default=None),
    ) -> dict:
        """触发商品全量对账，比对有赞在售集合与本地活跃记录，自动补齐下架状态。"""
        _verify_token(authorization)
        result = await reconcile_service.run()
        return {"code": 0, "data": result}

    return router
