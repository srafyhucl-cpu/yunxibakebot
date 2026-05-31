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

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db, close_db
from app.exceptions import AppError
from app.logger import setup_logger
from app.repository.analytics_repo import AnalyticsRepo
from app.repository.config_repo import ConfigRepo
from app.repository.content_change_history_repo import ContentChangeHistoryRepo
from app.repository.knowledge_admin_repo import KnowledgeAdminRepo
from app.repository.knowledge_product_repo import KnowledgeProductRepo
from app.repository.knowledge_repo import KnowledgeRepo
from app.repository.message_repo import MessageRepo
from app.repository.session_repo import SessionRepo
from app.repository.transfer_repo import TransferRepo
from app.repository.youzan_repo import YouzanProductRepo
from app.repository.youzan_webhook_event_repo import YouzanWebhookEventRepo
from app.service.chat import ChatService
from app.service.knowledge_retriever import KnowledgeRetriever
from app.service.youzan.client import YouzanClient
from app.service.youzan.event_handler import YouzanEventHandler
from app.service.youzan.product_reconciler import ProductReconcileService

logger = setup_logger()


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
    # 仅执行一次性初始化及微创迁移
    init_conn = await init_db(settings.DB_PATH)
    await init_conn.close()

    # 持有后台任务强引用，避免任务被 GC 提前回收导致回复丢失（N-2）。
    _background_tasks: set[asyncio.Task] = set()

    # Repository 层：启用动态 Context-Local 动态路由（传入 None）
    session_repo = SessionRepo(None)
    message_repo = MessageRepo(None)
    knowledge_repo = KnowledgeRepo(None)
    knowledge_admin_repo = KnowledgeAdminRepo(None)
    knowledge_product_repo = KnowledgeProductRepo(None)
    transfer_repo = TransferRepo(None)
    config_repo = ConfigRepo(None)
    history_repo = ContentChangeHistoryRepo(None)
    youzan_product_repo = YouzanProductRepo(None)
    webhook_event_repo = YouzanWebhookEventRepo(None)

    # 语义向量搜索服务（启动优化：首选极速缓存载入并进行一致性指纹对比，对齐时 100% 豁免 CPU 全量重算）
    from app.service.embedding_search import EmbeddingSearcher
    vs = EmbeddingSearcher()
    vs_path = settings.EMBEDDING_INDEX_DIR

    # 包裹在 db_session_scope 内部以提供专属连接
    from app.database import db_session_scope
    async with db_session_scope():
        logger.info("正在初始化向量搜索：首选尝试极速载入本地预解算缓存...")
        await vs.load(vs_path)

        docs = await knowledge_repo.get_all_titles_with_keys()
        need_rebuild = True

        import hashlib
        sorted_docs = sorted(docs, key=lambda x: x[0])
        concat_text = "".join(f"{d[1]}{d[2]}" for d in sorted_docs)
        current_db_md5 = hashlib.md5(concat_text.encode("utf-8")).hexdigest()

        if vs._ready and docs:
            # 对齐校验防漂移：引入 O(N) 集合哈希对比，检查缓存主键数量与值是否与数据库完全一致，同时校验数据文本全量 MD5 锁
            cached_keys = set(vs._doc_keys)
            db_keys = {str(d[0]) for d in docs}
            if cached_keys == db_keys and vs._data_hash == current_db_md5:
                need_rebuild = False
                logger.info("向量缓存指纹与文本特征 MD5 已完全对齐，直接载入启动，共有 %d 条向量", vs.doc_count)

        if need_rebuild:
            if docs:
                logger.info("向量缓存缺失或数据指纹不对齐（数据发生漂移），正在执行冷启动全量向量构建...")
                await asyncio.to_thread(vs.build, docs, current_db_md5)
                await vs.save(vs_path)
                logger.info("全量向量自愈构建并落盘完成，对齐并持久化 %d 条活跃向量", vs.doc_count)
            else:
                logger.warning("知识库中尚无活跃条目，跳过启动向量构建")

    # 异步定时节流刷盘后台守护任务
    async def periodic_save_task() -> None:
        try:
            while True:
                try:
                    await asyncio.wait_for(vs._save_event.wait(), timeout=120.0)
                    vs._save_event.clear()
                except asyncio.TimeoutError:
                    pass
                if vs and vs._dirty:
                    async with db_session_scope():
                        active_docs = await knowledge_repo.get_all_titles_with_keys()
                        import hashlib
                        sorted_active_docs = sorted(active_docs, key=lambda x: x[0])
                        concat_str = "".join(f"{d[1]}{d[2]}" for d in sorted_active_docs)
                        latest_db_md5 = hashlib.md5(concat_str.encode("utf-8")).hexdigest()
                        vs._data_hash = latest_db_md5
                        await vs.save(vs_path)
        except asyncio.CancelledError:
            # 正常退出拦截器，最后一次强制清算持久化
            if vs and vs._dirty:
                try:
                    async with db_session_scope():
                        active_docs = await knowledge_repo.get_all_titles_with_keys()
                        import hashlib
                        sorted_active_docs = sorted(active_docs, key=lambda x: x[0])
                        concat_str = "".join(f"{d[1]}{d[2]}" for d in sorted_active_docs)
                        latest_db_md5 = hashlib.md5(concat_str.encode("utf-8")).hexdigest()
                        vs._data_hash = latest_db_md5
                        await vs.save(vs_path)
                except Exception as e:
                    logger.error("守护协程退关刷盘异常: %s", e)
        except Exception as e:
            logger.error("定时节流刷盘守护协程异常: %s", e)

    save_task = asyncio.create_task(periodic_save_task())

    # Service 层
    knowledge_retriever = KnowledgeRetriever(knowledge_repo, vs, config_repo=config_repo)
    from app.service.admin import AdminService
    from app.service.knowledge_admin import KnowledgeAdminService
    from app.service.knowledge_sync import KnowledgeSyncService
    from app.service.observability import ObservabilityService
    from app.service.transfer_manager import TransferManager

    admin_service = AdminService(
        session_repo=session_repo,
        message_repo=message_repo,
        transfer_repo=transfer_repo,
        knowledge_repo=knowledge_repo,
        config_repo=config_repo,
        youzan_product_repo=youzan_product_repo,
    )
    observability_service = ObservabilityService(
        knowledge_repo=knowledge_repo,
        product_repo=youzan_product_repo,
        history_repo=history_repo,
        webhook_repo=webhook_event_repo,
    )
    knowledge_sync_service = KnowledgeSyncService(
        knowledge_repo=knowledge_repo,
        history_repo=history_repo,
        embedding_searcher=vs,
    )
    knowledge_admin_service = KnowledgeAdminService(
        knowledge_repo=knowledge_repo,
        admin_repo=knowledge_admin_repo,
        history_repo=history_repo,
        sync_service=knowledge_sync_service,
    )
    transfer_mgr = TransferManager(transfer_repo)

    youzan_client = YouzanClient(config_repo=config_repo)
    analytics_repo = AnalyticsRepo(None)
    youzan_event_handler = YouzanEventHandler(
        db=None,
        knowledge_retriever=knowledge_retriever,
        youzan_client=youzan_client,
        audit_repo=webhook_event_repo,
    )
    reconcile_service = ProductReconcileService(
        youzan_client=youzan_client,
        product_repo=youzan_product_repo,
        history_repo=history_repo,
        knowledge_product_repo=knowledge_product_repo,
    )

    chat_service = ChatService(
        session_repo=session_repo,
        message_repo=message_repo,
        transfer_repo=transfer_repo,
        knowledge_retriever=knowledge_retriever,
        youzan_client=youzan_client,
        youzan_webhook_events_repo=webhook_event_repo,
        youzan_event_handler=youzan_event_handler,
        analytics_repo=analytics_repo,
    )

    # 注册路由（通过工厂函数注入依赖）
    from app.api.admin import create_admin_router
    from app.api.admin_config import create_shop_config_router
    from app.api.admin_frontend import create_admin_frontend_router
    from app.api.admin_knowledge import create_admin_knowledge_router
    from app.api.admin_observability import create_observability_router
    from app.api.admin_products import create_admin_products_router
    from app.api.webhook import create_webhook_router
    from app.api.wecom import router as wecom_router, register_handler

    # 注册企微消息回调处理器
    async def wecom_handler(channel: str, user_id: str, content: str, channel_msg_id: str) -> None:
        await chat_service.handle_message(
            channel=channel,
            user_id=user_id,
            content=content,
            channel_msg_id=channel_msg_id,
        )
    register_handler(wecom_handler)

    app.include_router(create_webhook_router(chat_service))
    app.include_router(create_admin_router(
        chat_service=chat_service,
        admin_service=admin_service,
        transfer_mgr=transfer_mgr,
    ))
    app.include_router(create_admin_frontend_router())
    app.include_router(create_shop_config_router(admin_service))
    app.include_router(create_admin_knowledge_router(knowledge_admin_service))
    app.include_router(create_observability_router(observability_service))
    app.include_router(create_admin_products_router(reconcile_service, knowledge_sync_service))
    app.include_router(wecom_router)

    logger.info("芸熙烘焙 AI 客服启动完成，监听端口: %d", settings.SERVER_PORT)

    async def _startup_sync_task() -> None:
        """服务启动完成后批量同步所有 pending 向量条目。"""
        try:
            async with db_session_scope():
                result = await knowledge_sync_service.sync_all_pending()
                logger.info("启动向量自愈同步完成: %s", result)
        except Exception as exc:
            logger.error("启动向量自愈同步失败: %s", exc)

    startup_sync = asyncio.create_task(_startup_sync_task())
    _background_tasks.add(startup_sync)
    startup_sync.add_done_callback(_background_tasks.discard)
    yield
    # ── shutdown ──
    save_task.cancel()
    try:
        await save_task
    except asyncio.CancelledError:
        pass
    from app.service.wecom.client import close_wecom_client
    await close_wecom_client()
    logger.info("服务已关闭")


app = FastAPI(
    title="芸熙烘焙 AI 客服",
    description="Yunxi BakeBot - 多渠道 AI 智能客服系统",
    version="0.1.0",
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


# ── 数据库连接生命周期与事务隔离中间件 ──
@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    from app.database import db_session_scope
    async with db_session_scope():
        return await call_next(request)


# ── 全局异常处理器 ──
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.error("应用异常: %s %s", type(exc).__name__, exc)
    status = exc.status_code
    return JSONResponse(status_code=status, content={"code": status * 100, "message": str(exc)})


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.critical("未预期异常: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"code": 50000, "message": "服务器内部错误"})


# ── 健康检查 ──
@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
