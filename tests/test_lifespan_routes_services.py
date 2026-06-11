from __future__ import annotations

import sys
import types
from typing import Any

from app import lifespan_routes, lifespan_services


class FakeApp:
    def __init__(self) -> None:
        self.included_routers: list[Any] = []

    def include_router(self, router: Any) -> None:
        self.included_routers.append(router)


class FakeQueue:
    def __init__(self) -> None:
        self.started_with: list[Any] = []

    def start_worker(self, chat_service: Any) -> None:
        self.started_with.append(chat_service)


def _install_module(monkeypatch: Any, name: str, **attrs: Any) -> None:
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)


def test_register_routes_starts_workers_and_includes_all_routers(
    monkeypatch,
) -> None:
    wecom_queue = FakeQueue()
    kf_queue = FakeQueue()
    _install_module(
        monkeypatch,
        "app.service.wecom.message_queue",
        wecom_queue=wecom_queue,
    )
    _install_module(
        monkeypatch,
        "app.service.wecom.kf_message_queue",
        kf_queue=kf_queue,
    )
    _install_module(
        monkeypatch,
        "app.api.admin",
        create_admin_router=lambda **kwargs: ("admin", kwargs),
    )
    _install_module(
        monkeypatch,
        "app.api.admin_config",
        create_shop_config_router=lambda admin_service: ("config", admin_service),
    )
    _install_module(
        monkeypatch,
        "app.api.admin_frontend",
        create_admin_frontend_router=lambda: "frontend",
    )
    _install_module(
        monkeypatch,
        "app.api.admin_knowledge",
        create_admin_knowledge_router=lambda service: ("knowledge", service),
    )
    _install_module(
        monkeypatch,
        "app.api.admin_observability",
        create_observability_router=lambda service: ("observability", service),
    )
    _install_module(
        monkeypatch,
        "app.api.admin_products",
        create_admin_products_router=lambda reconcile, sync: (
            "products",
            reconcile,
            sync,
        ),
    )
    _install_module(
        monkeypatch,
        "app.api.webhook",
        create_webhook_router=lambda chat_service: ("webhook", chat_service),
    )
    _install_module(monkeypatch, "app.api.wecom", router="wecom-router")
    app = FakeApp()
    services = {
        "chat_service": "chat",
        "admin_service": "admin-service",
        "transfer_mgr": "transfer",
        "knowledge_admin_service": "knowledge-admin",
        "observability_service": "observability",
        "reconcile_service": "reconcile",
        "knowledge_sync_service": "knowledge-sync",
    }

    lifespan_routes.register_routes(app, services)

    assert wecom_queue.started_with == ["chat"]
    assert kf_queue.started_with == ["chat"]
    assert len(app.included_routers) == 8
    assert app.included_routers[0] == ("webhook", "chat")
    assert app.included_routers[-1] == "wecom-router"


def test_init_services_wires_core_services(monkeypatch) -> None:
    created: dict[str, Any] = {}

    class FakeKnowledgeRetriever:
        def __init__(self, knowledge_repo, vs, *, config_repo, bm25) -> None:
            created["knowledge_retriever"] = (knowledge_repo, vs, config_repo, bm25)

    class FakeYouzanClient:
        def __init__(self, *, config_repo) -> None:
            created["youzan_client"] = config_repo

    class FakeYouzanEventHandler:
        def __init__(self, **kwargs: Any) -> None:
            created["youzan_event_handler"] = kwargs

    class FakeProductReconcileService:
        def __init__(self, **kwargs: Any) -> None:
            created["reconcile_service"] = kwargs

    class FakeAdminService:
        def __init__(self, **kwargs: Any) -> None:
            created["admin_service"] = kwargs

    class FakeObservabilityService:
        def __init__(self, **kwargs: Any) -> None:
            created["observability_service"] = kwargs

    class FakeKnowledgeSyncService:
        def __init__(self, **kwargs: Any) -> None:
            created["knowledge_sync_service"] = kwargs

    class FakeKnowledgeAdminService:
        def __init__(self, **kwargs: Any) -> None:
            created["knowledge_admin_service"] = kwargs

    class FakeTransferManager:
        def __init__(self, repo: Any) -> None:
            created["transfer_mgr"] = repo

    class FakeChatService:
        def __init__(self, **kwargs: Any) -> None:
            created["chat_service"] = kwargs

    monkeypatch.setattr(lifespan_services, "KnowledgeRetriever", FakeKnowledgeRetriever)
    monkeypatch.setattr(lifespan_services, "YouzanClient", FakeYouzanClient)
    monkeypatch.setattr(lifespan_services, "YouzanEventHandler", FakeYouzanEventHandler)
    monkeypatch.setattr(
        lifespan_services,
        "ProductReconcileService",
        FakeProductReconcileService,
    )
    monkeypatch.setattr(lifespan_services, "ChatService", FakeChatService)
    _install_module(monkeypatch, "app.service.admin", AdminService=FakeAdminService)
    _install_module(
        monkeypatch,
        "app.service.knowledge_admin",
        KnowledgeAdminService=FakeKnowledgeAdminService,
    )
    _install_module(
        monkeypatch,
        "app.service.knowledge_sync",
        KnowledgeSyncService=FakeKnowledgeSyncService,
    )
    _install_module(
        monkeypatch,
        "app.service.observability",
        ObservabilityService=FakeObservabilityService,
    )
    _install_module(
        monkeypatch,
        "app.service.transfer_manager",
        TransferManager=FakeTransferManager,
    )
    repos = {
        "session_repo": "session-repo",
        "message_repo": "message-repo",
        "knowledge_repo": "knowledge-repo",
        "knowledge_admin_repo": "knowledge-admin-repo",
        "knowledge_product_repo": "knowledge-product-repo",
        "transfer_repo": "transfer-repo",
        "config_repo": "config-repo",
        "history_repo": "history-repo",
        "youzan_product_repo": "youzan-product-repo",
        "webhook_event_repo": "webhook-event-repo",
        "analytics_repo": "analytics-repo",
        "customer_profile_repo": "customer-profile-repo",
    }

    services = lifespan_services.init_services(repos, vs="vector", bm25="bm25")

    assert set(services) == {
        "admin_service",
        "observability_service",
        "knowledge_sync_service",
        "knowledge_admin_service",
        "transfer_mgr",
        "youzan_client",
        "youzan_event_handler",
        "reconcile_service",
        "chat_service",
    }
    assert created["knowledge_retriever"] == (
        "knowledge-repo",
        "vector",
        "config-repo",
        "bm25",
    )
    assert created["transfer_mgr"] == "transfer-repo"
    assert created["chat_service"]["youzan_client"] is services["youzan_client"]
    assert created["chat_service"]["customer_profile_repo"] == "customer-profile-repo"
    assert (
        created["reconcile_service"]["knowledge_product_repo"]
        == "knowledge-product-repo"
    )
