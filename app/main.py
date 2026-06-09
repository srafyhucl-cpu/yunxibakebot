"""
FastAPI 应用入口。
职责：
- 启动时初始化数据库连接
- 组装依赖树（Repository 层 / Service 层 / API Router）
- 注册路由和异常处理器
- 管理服务生命周期（lifespan）
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import APP_VERSION, settings
from app.database import init_db, db_session_scope
from app.exceptions import AppError
from app.logger import setup_logger
from app.service.alerting import AlertLevel, alert_service
from app.repository.analytics_repo import AnalyticsRepo
from app.repository.config_repo import ConfigRepo
from app.repository.conversation_review_repo import ConversationReviewRepo
from app.repository.content_change_history_repo import ContentChangeHistoryRepo
from app.repository.customer_profile_repo import CustomerProfileRepo
from app.repository.knowledge_gap_repo import KnowledgeGapRepo
from app.repository.knowledge_admin_repo import KnowledgeAdminRepo
from app.repository.knowledge_product_repo import KnowledgeProductRepo
from app.repository.knowledge_repo import KnowledgeRepo
from app.repository.message_repo import MessageRepo
from app.repository.session_repo import SessionRepo
from app.repository.transfer_repo import TransferRepo
from app.repository.youzan_repo import YouzanProductRepo
from app.repository.youzan_webhook_event_repo import YouzanWebhookEventRepo
# 以下5个服务类由lifespan_services模块内部按需导入，避免顶层循环依赖
# （顶层仅做类型标注用）：ChatService、KnowledgeRetriever、YouzanClient、YouzanEventHandler、ProductReconcileService

logger = setup_logger()


def _check_startup_safety() -> None:
    """
    启动时检查敏感配置，检测到问题则记录警告或阻止启动。
    """
    # 检查 ADMIN_API_TOKEN 是否为默认值
    if settings.ADMIN_API_TOKEN == "CHANGE_ME_IN_PRODUCTION_ENV":
        logger.critical(
            "启动安全检查失败：ADMIN_API_TOKEN 仍为默认值，请在 .env 中设置强密码"
        )
        raise SystemExit(1)

    # 检查其他敏感配置是否为空（仅记录警告，不阻止启动）
    sensitive_configs = [
        ("MIMO_API_KEY", settings.MIMO_API_KEY),
        ("YOUZAN_CLIENT_ID", settings.YOUZAN_CLIENT_ID),
        ("YOUZAN_CLIENT_SECRET", settings.YOUZAN_CLIENT_SECRET),
        ("WECOM_CORP_ID", settings.WECOM_CORP_ID),
        ("WECOM_SECRET", settings.WECOM_SECRET),
    ]

    for name, value in sensitive_configs:
        if not value:
            logger.warning(
                "启动安全检查警告：%s 未设置，相关功能可能无法正常工作", name
            )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期。
    startup：
        1. 初始化 SQLite 数据库
        2. 组装依赖树
        3. 注册路由
    shutdown：
        1. 关闭数据库连接
    """
    # ── startup ──
    # 0. 启动安全检查
    _check_startup_safety()

    bg_tasks = await _init_lifespan_services(app)

    yield

    # ── shutdown ──
    await _shutdown_lifespan_services(app, bg_tasks)


async def _init_lifespan_services(app: FastAPI) -> set[asyncio.Task[None]]:
    """初始化 lifespan 所需的所有服务，返回后台任务集合。"""
    # 1. 初始化数据库
    await _init_database()

    # 2. 初始化 Repository 层
    repos = _init_repositories()

    # 3. 初始化向量搜索
    from app.lifespan_vector import init_vector_search

    vs, bm25, save_task = await init_vector_search(
        app,
        repos["knowledge_repo"],  # type: ignore[arg-type]
    )

    # 4. 初始化 Service 层
    from app.lifespan_services import init_services

    services = init_services(repos, vs, bm25)

    # 5. 注册路由
    from app.lifespan_routes import register_routes

    register_routes(app, services)

    # 6. 启动后台任务
    bg_tasks = _start_background_tasks(app, repos)
    bg_tasks.add(save_task)

    # 7. 启动通知
    await _startup_notify()

    # 8. 启动向量同步任务
    await _startup_sync(services["knowledge_sync_service"], bg_tasks)

    return bg_tasks


async def _init_database() -> None:
    """初始化 SQLite 数据库（含微创迁移）。"""
    init_conn = await init_db(settings.DB_PATH)
    await init_conn.close()


def _init_repositories() -> dict[str, object]:
    """初始化 Repository 层（使用 None 占位，运行时通过 ContextVar 动态路由）。"""
    return {
        "session_repo": SessionRepo(None),
        "message_repo": MessageRepo(None),
        "knowledge_repo": KnowledgeRepo(None),
        "knowledge_admin_repo": KnowledgeAdminRepo(None),
        "knowledge_product_repo": KnowledgeProductRepo(None),
        "transfer_repo": TransferRepo(None),
        "config_repo": ConfigRepo(None),
        "history_repo": ContentChangeHistoryRepo(None),
        "youzan_product_repo": YouzanProductRepo(None),
        "webhook_event_repo": YouzanWebhookEventRepo(None),
        "analytics_repo": AnalyticsRepo(None),
        "customer_profile_repo": CustomerProfileRepo(None),
        "conversation_review_repo": ConversationReviewRepo(None),
        "knowledge_gap_repo": KnowledgeGapRepo(None),
    }


async def _startup_notify() -> None:
    """发送启动通知。"""
    logger.info("芸熙烘焙 AI 客服启动完成，监听端口: %d", settings.SERVER_PORT)
    asyncio.create_task(
        alert_service.alert(
            AlertLevel.INFO,
            "服务已启动",
            f"芸熙烘焙 AI 客服 v{APP_VERSION} 已启动，监听端口 {settings.SERVER_PORT}",
        )
    )


def _start_background_tasks(
    app: FastAPI, repos: dict[str, object]
) -> set[asyncio.Task[None]]:
    """创建后台任务集合（持有强引用，避免任务被 GC 提前回收）。"""
    bg_tasks: set[asyncio.Task[None]] = set()

    from app.service.offline.bootstrap import register_offline_review_scheduler

    register_offline_review_scheduler(app, repos, bg_tasks, db_session_scope)
    return bg_tasks


async def _startup_sync(
    knowledge_sync_service: Any, bg_tasks: set[asyncio.Task[None]]
) -> None:
    """服务启动完成后批量同步所有 pending 向量条目。"""

    async def _startup_sync_task() -> None:
        try:
            async with db_session_scope():
                result = await knowledge_sync_service.sync_all_pending()
                logger.info("启动向量自愈同步完成: %s", result)
        except Exception as exc:
            logger.error("启动向量自愈同步失败: %s", exc)

    startup_sync = asyncio.create_task(_startup_sync_task())
    bg_tasks.add(startup_sync)
    startup_sync.add_done_callback(lambda t: bg_tasks.discard(t))


async def _shutdown_lifespan_services(
    app: FastAPI, _bg_tasks: set[asyncio.Task[None]]
) -> None:
    """关闭 lifespan 所有服务。"""
    # 取消定时刷盘任务
    if hasattr(app.state, "save_task"):
        save_task = app.state.save_task
        save_task.cancel()
        try:
            await save_task
        except asyncio.CancelledError:
            pass

    # 停止企微消息队列 Worker
    from app.service.wecom.message_queue import wecom_queue

    await wecom_queue.stop()

    # 停止微信客服消息队列 Worker
    from app.service.wecom.kf_message_queue import kf_queue

    await kf_queue.stop()

    from app.service.offline.bootstrap import stop_offline_review_scheduler

    await stop_offline_review_scheduler(app)

    # 关闭企微客户端
    from app.service.wecom.client import close_wecom_client

    await close_wecom_client()

    # 发送关闭通知
    await alert_service.alert(
        AlertLevel.INFO, "服务已关闭", f"芸熙烘焙 AI 客服 v{APP_VERSION} 已正常关闭"
    )
    logger.info("服务已关闭")


app = FastAPI(
    title="芸熙烘焙 AI 客服",
    description="Yunxi BakeBot - 多渠道 AI 智能客服系统",
    version=APP_VERSION,
    lifespan=lifespan,
)

# ── 静态文件 ──
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/{filename}.txt")
async def serve_verify_txt(filename: str):
    """微信/有赞等平台域名所有权 TXT 文件根目录穿透自动响应路由。"""
    import os
    from fastapi.responses import FileResponse
    from fastapi.exceptions import HTTPException

    filename = os.path.basename(filename)
    file_path = BASE_DIR / "static" / f"{filename}.txt"
    if os.path.exists(file_path):
        return FileResponse(str(file_path))
    raise HTTPException(status_code=404, detail="Not Found")


@app.get("/favicon.ico", include_in_schema=False)
async def serve_favicon():
    """网站根目录 favicon.ico 图标响应。"""
    from fastapi.responses import FileResponse

    ico_path = BASE_DIR.parent / "web" / "admin" / "dist" / "favicon.ico"
    if not ico_path.exists():
        ico_path = BASE_DIR / "static" / "favicon.ico"
    if ico_path.exists():
        return FileResponse(str(ico_path))
    from fastapi.exceptions import HTTPException

    raise HTTPException(status_code=404, detail="Not Found")


# ── 数据库连接生命周期与事务隔离中间件 ──
@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    from app.database import db_session_scope

    async with db_session_scope():
        return await call_next(request)


# ── 全局异常处理器 ──
@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    logger.error("应用异常: %s %s", type(exc).__name__, exc)
    status = exc.status_code
    return JSONResponse(
        status_code=status, content={"code": status * 100, "message": str(exc)}
    )


@app.exception_handler(Exception)
async def general_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.critical("未预期异常: %s", exc, exc_info=True)
    # 异步发送企微告警（不阻塞 HTTP 响应）
    asyncio.create_task(
        alert_service.alert(
            AlertLevel.CRITICAL, "未预期异常", f"{type(exc).__name__}: {exc}"
        )
    )
    return JSONResponse(
        status_code=500, content={"code": 50000, "message": "服务器内部错误"}
    )


# ── 健康检查 ──
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": APP_VERSION}
