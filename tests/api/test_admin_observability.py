import pytest
from fastapi import Request

from app.api.admin_observability import create_observability_router
from app.config import settings
from app.database import close_db, init_db
from app.models.content_change_history import SyncSource
from app.repository.content_change_history_repo import ContentChangeHistoryRepo
from app.repository.knowledge_repo import KnowledgeRepo
from app.repository.youzan_repo import YouzanProductRepo
from app.repository.youzan_webhook_event_repo import YouzanWebhookEventRepo
from app.service.observability import ObservabilityService


def _get_route_endpoint(router, path: str, method: str):
    for route in router.routes:
        if getattr(route, "path", "") == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"Route not found: {method} {path}")


def _build_request(path: str, cookies: dict | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "scheme": "http",
    }
    request = Request(scope)
    request._cookies = cookies or {}
    return request


@pytest.mark.asyncio
async def test_admin_observability_page_redirects_without_login() -> None:
    db = await init_db(":memory:")
    await KnowledgeRepo(db).insert_entry(
        category="faq",
        title="配送说明",
        content="当天配送",
        keywords="配送",
        priority=5,
        sync_source=SyncSource.SEED_KNOWLEDGE,
    )
    router = create_observability_router(
        ObservabilityService(
            knowledge_repo=KnowledgeRepo(db),
            product_repo=YouzanProductRepo(db),
            history_repo=ContentChangeHistoryRepo(db),
            webhook_repo=YouzanWebhookEventRepo(db),
        )
    )
    endpoint = _get_route_endpoint(router, "/admin/observability/current", "GET")

    response = await endpoint(request=_build_request("/admin/observability/current"))

    assert response.status_code == 302
    assert response.headers["location"] == "/admin/login"
    await close_db(db)


@pytest.mark.asyncio
async def test_admin_observability_api_returns_data_with_token() -> None:
    db = await init_db(":memory:")
    await KnowledgeRepo(db).insert_entry(
        category="faq",
        title="配送说明",
        content="当天配送",
        keywords="配送",
        priority=5,
        sync_source=SyncSource.SEED_KNOWLEDGE,
    )
    router = create_observability_router(
        ObservabilityService(
            knowledge_repo=KnowledgeRepo(db),
            product_repo=YouzanProductRepo(db),
            history_repo=ContentChangeHistoryRepo(db),
            webhook_repo=YouzanWebhookEventRepo(db),
        )
    )
    endpoint = _get_route_endpoint(router, "/api/v1/admin/observability/current", "GET")

    payload = await endpoint(authorization=f"Bearer {settings.ADMIN_API_TOKEN}")

    assert payload["code"] == 0
    assert payload["total"] == 1
    assert payload["data"][0]["title"] == "配送说明"
    await close_db(db)
