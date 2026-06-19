"""lifespan 阶段 API 路由注册逻辑。"""

from typing import Any

from fastapi import FastAPI


def register_routes(app: FastAPI, services: dict[str, Any]) -> None:
    """注册所有 API 路由，并启动消息队列 Worker。"""
    from app.api.admin import create_admin_router
    from app.api.admin_config import create_shop_config_router
    from app.api.admin_frontend import create_admin_frontend_router
    from app.api.admin_knowledge import create_admin_knowledge_router
    from app.api.admin_observability import create_observability_router
    from app.api.miniapp_catalog import create_miniapp_catalog_router
    from app.api.admin_products import create_admin_products_router
    from app.api.webhook import create_webhook_router
    from app.api.wecom import router as wecom_router
    from app.service.wecom.kf_message_queue import kf_queue
    from app.service.wecom.message_queue import wecom_queue

    wecom_queue.start_worker(services["chat_service"])
    kf_queue.start_worker(services["chat_service"])

    app.include_router(create_webhook_router(services["chat_service"]))
    app.include_router(
        create_admin_router(
            chat_service=services["chat_service"],
            admin_service=services["admin_service"],
            transfer_mgr=services["transfer_mgr"],
        )
    )
    app.include_router(create_admin_frontend_router())
    app.include_router(create_shop_config_router(services["admin_service"]))
    app.include_router(
        create_miniapp_catalog_router(services["miniapp_catalog_service"])
    )
    app.include_router(
        create_admin_knowledge_router(services["knowledge_admin_service"])
    )
    app.include_router(create_observability_router(services["observability_service"]))
    app.include_router(
        create_admin_products_router(
            services["reconcile_service"],
            services["knowledge_sync_service"],
        )
    )
    app.include_router(wecom_router)
