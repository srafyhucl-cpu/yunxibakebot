from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app import main
from app.exceptions import AppError


class FakeAlertService:
    def __init__(self) -> None:
        self.alerts: list[tuple[object, str, str]] = []

    async def alert(self, level: object, title: str, message: str) -> None:
        self.alerts.append((level, title, message))


class FakeLogger:
    def __init__(self) -> None:
        self.records: list[tuple[str, tuple[object, ...]]] = []

    def critical(self, message: str, *args: object, **kwargs: object) -> None:
        self.records.append(("critical", (message, *args)))

    def error(self, message: str, *args: object, **kwargs: object) -> None:
        self.records.append(("error", (message, *args)))

    def warning(self, message: str, *args: object, **kwargs: object) -> None:
        self.records.append(("warning", (message, *args)))

    def info(self, message: str, *args: object, **kwargs: object) -> None:
        self.records.append(("info", (message, *args)))


async def _call_next(_request: object) -> str:
    return "ok"


def test_startup_safety_blocks_default_admin_token(monkeypatch) -> None:
    fake_logger = FakeLogger()
    monkeypatch.setattr(main.settings, "ADMIN_API_TOKEN", main.DEFAULT_ADMIN_TOKEN)
    monkeypatch.setattr(main, "logger", fake_logger)

    with pytest.raises(SystemExit):
        main._check_startup_safety()  # noqa: SLF001

    assert fake_logger.records[0][0] == "critical"


def test_startup_safety_warns_for_missing_optional_secrets(monkeypatch) -> None:
    fake_logger = FakeLogger()
    monkeypatch.setattr(main.settings, "ADMIN_API_TOKEN", "strong-token")
    monkeypatch.setattr(main.settings, "MIMO_API_KEY", "")
    monkeypatch.setattr(main.settings, "YOUZAN_CLIENT_ID", "")
    monkeypatch.setattr(main.settings, "YOUZAN_CLIENT_SECRET", "secret")
    monkeypatch.setattr(main.settings, "WECOM_CORP_ID", "corp")
    monkeypatch.setattr(main.settings, "WECOM_SECRET", "")
    monkeypatch.setattr(main, "logger", fake_logger)

    main._check_startup_safety()  # noqa: SLF001

    warning_names = [record[1][1] for record in fake_logger.records]
    assert warning_names == ["MIMO_API_KEY", "YOUZAN_CLIENT_ID", "WECOM_SECRET"]


async def test_db_session_middleware_wraps_call_next(monkeypatch) -> None:
    events: list[str] = []

    class FakeDbSessionScope:
        async def __aenter__(self) -> None:
            events.append("enter")

        async def __aexit__(self, exc_type, exc, tb) -> None:
            events.append("exit")

    import app.database as database

    monkeypatch.setattr(database, "db_session_scope", FakeDbSessionScope)

    result = await main.db_session_middleware(object(), _call_next)

    assert result == "ok"
    assert events == ["enter", "exit"]


async def test_app_error_handler_returns_structured_json() -> None:
    class ConflictError(AppError):
        status_code = 409

    response = await main.app_error_handler(
        object(),
        ConflictError("业务失败"),
    )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 409
    assert response.body.decode("utf-8") == '{"code":40900,"message":"业务失败"}'


async def test_general_error_handler_schedules_alert(monkeypatch) -> None:
    fake_alert_service = FakeAlertService()
    created_tasks: list[object] = []

    def fake_create_task(coro):
        created_tasks.append(coro)
        return "task"

    monkeypatch.setattr(main, "alert_service", fake_alert_service)
    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    response = await main.general_error_handler(object(), RuntimeError("boom"))
    await created_tasks[0]

    assert response.status_code == 500
    assert fake_alert_service.alerts
    assert "RuntimeError" in fake_alert_service.alerts[0][2]


async def test_health_and_ready_shapes(monkeypatch) -> None:
    monkeypatch.setattr(main, "build_readiness_checks", lambda: {"db": True})
    monkeypatch.setattr(
        main,
        "build_runtime_feature_flags",
        lambda offline_review_running=False: {
            "reply_guard": True,
            "offline_review_running": offline_review_running,
        },
    )

    assert await main.health() == {"status": "ok", "version": main.APP_VERSION}
    assert await main.ready() == {
        "status": "ready",
        "version": main.APP_VERSION,
        "checks": {"db": True},
        "features": {"reply_guard": True, "offline_review_running": False},
    }


def test_build_runtime_feature_flags_includes_offline_runtime_state() -> None:
    flags = main.build_runtime_feature_flags(True)

    assert flags["offline_review_running"] is True


async def test_static_file_helpers_return_or_404(monkeypatch, tmp_path) -> None:
    app_dir = tmp_path / "app"
    static_dir = app_dir / "static"
    admin_dist = tmp_path / "web" / "admin" / "dist"
    static_dir.mkdir(parents=True)
    admin_dist.mkdir(parents=True)
    verify_file = static_dir / "verify.txt"
    favicon = admin_dist / "favicon.ico"
    verify_file.write_text("ok", encoding="utf-8")
    favicon.write_bytes(b"ico")
    monkeypatch.setattr(main, "BASE_DIR", app_dir)

    verify_response = await main.serve_verify_txt("../verify")
    favicon_response = await main.serve_favicon()

    assert isinstance(verify_response, FileResponse)
    assert isinstance(favicon_response, FileResponse)
    with pytest.raises(HTTPException):
        await main.serve_verify_txt("missing")


async def test_shutdown_lifespan_services_stops_runtime_components(
    monkeypatch,
) -> None:
    events: list[str] = []
    fake_alert_service = FakeAlertService()

    class FakeQueue:
        async def stop(self) -> None:
            events.append("queue-stop")

    async def fake_stop_offline_review_scheduler(app) -> None:
        events.append("offline-stop")

    async def fake_close_wecom_client() -> None:
        events.append("wecom-close")

    _install_runtime_module(
        monkeypatch,
        "app.service.wecom.message_queue",
        wecom_queue=FakeQueue(),
    )
    _install_runtime_module(
        monkeypatch,
        "app.service.wecom.kf_message_queue",
        kf_queue=FakeQueue(),
    )
    _install_runtime_module(
        monkeypatch,
        "app.service.offline.bootstrap",
        stop_offline_review_scheduler=fake_stop_offline_review_scheduler,
    )
    _install_runtime_module(
        monkeypatch,
        "app.service.wecom.client",
        close_wecom_client=fake_close_wecom_client,
    )
    monkeypatch.setattr(main, "alert_service", fake_alert_service)
    monkeypatch.setattr(main, "logger", FakeLogger())
    app = SimpleNamespace(state=SimpleNamespace())

    await main._shutdown_lifespan_services(app, set())  # noqa: SLF001

    assert events == ["queue-stop", "queue-stop", "offline-stop", "wecom-close"]
    assert fake_alert_service.alerts


def _install_runtime_module(monkeypatch, name: str, **attrs: object) -> None:
    import sys
    import types

    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
