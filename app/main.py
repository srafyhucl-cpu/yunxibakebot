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
from app.repository.config_repo import ConfigRepo
from app.repository.knowledge_repo import KnowledgeRepo
from app.repository.message_repo import MessageRepo
from app.repository.session_repo import SessionRepo
from app.repository.transfer_repo import TransferRepo
from app.service.chat import ChatService
from app.service.knowledge_retriever import KnowledgeRetriever

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
    db = await init_db(settings.DB_PATH)

    # Repository 层
    session_repo = SessionRepo(db)
    message_repo = MessageRepo(db)
    knowledge_repo = KnowledgeRepo(db)
    transfer_repo = TransferRepo(db)
    config_repo = ConfigRepo(db)

    # 语义向量搜索服务（启动优化：首选极速缓存载入并进行一致性指纹对比，对齐时 100% 豁免 CPU 全量重算）
    from app.service.embedding_search import EmbeddingSearcher
    vs = EmbeddingSearcher()
    vs_path = settings.EMBEDDING_PATH

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
            logger.info("🎉 完美对齐！向量缓存指纹与文本特征 MD5 100%% 一致，直接载入启动，共有 %d 条向量", vs.doc_count)

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
        while True:
            try:
                await asyncio.sleep(120)
                if vs._dirty:
                    active_docs = await knowledge_repo.get_all_titles_with_keys()
                    import hashlib
                    sorted_active_docs = sorted(active_docs, key=lambda x: x[0])
                    concat_str = "".join(f"{d[1]}{d[2]}" for d in sorted_active_docs)
                    latest_db_md5 = hashlib.md5(concat_str.encode("utf-8")).hexdigest()
                    vs._data_hash = latest_db_md5
                    await vs.save(vs_path)
            except asyncio.CancelledError:
                # 正常退出拦截器，最后一次强制清算持久化
                if vs._dirty:
                    try:
                        active_docs = await knowledge_repo.get_all_titles_with_keys()
                        import hashlib
                        sorted_active_docs = sorted(active_docs, key=lambda x: x[0])
                        concat_str = "".join(f"{d[1]}{d[2]}" for d in sorted_active_docs)
                        latest_db_md5 = hashlib.md5(concat_str.encode("utf-8")).hexdigest()
                        vs._data_hash = latest_db_md5
                        await vs.save(vs_path)
                    except Exception as e:
                        logger.error("守护协程退关刷盘异常: %s", e)
                break
            except Exception as e:
                logger.error("定时节流刷盘守护协程异常: %s", e)

    save_task = asyncio.create_task(periodic_save_task())

    # Service 层
    knowledge_retriever = KnowledgeRetriever(knowledge_repo, vs, config_repo=config_repo)
    from app.service.admin import AdminService
    from app.service.transfer_manager import TransferManager

    admin_service = AdminService(
        session_repo=session_repo,
        message_repo=message_repo,
        transfer_repo=transfer_repo,
        knowledge_repo=knowledge_repo,
        config_repo=config_repo,
    )
    transfer_mgr = TransferManager(transfer_repo)

    chat_service = ChatService(
        session_repo=session_repo,
        message_repo=message_repo,
        transfer_repo=transfer_repo,
        knowledge_retriever=knowledge_retriever,
    )

    # 注册路由（通过工厂函数注入依赖）
    from app.api.admin import create_admin_router
    from app.api.admin_config import create_shop_config_router
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
    app.include_router(create_shop_config_router(admin_service))
    app.include_router(wecom_router)

    logger.info("芸熙烘焙 AI 客服启动完成，监听端口: %d", settings.SERVER_PORT)
    yield
    # ── shutdown ──
    save_task.cancel()
    try:
        await save_task
    except asyncio.CancelledError:
        pass
    from app.service.wecom.client import close_wecom_client
    await close_wecom_client()
    await close_db(db)
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

    file_path = BASE_DIR / "static" / f"{filename}.txt"
    if os.path.exists(file_path):
        return FileResponse(str(file_path))
    raise HTTPException(status_code=404, detail="Not Found")


# ── 全局异常处理器 ──
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """应用级异常统一返回 JSON 格式。"""
    logger.error("应用异常: %s %s", type(exc).__name__, exc)
    status_map: dict[str, int] = {
        "AuthError": 403,
        "NotFoundError": 404,
        "LLMError": 502,
        "APIError": 502,
        "ConfigError": 500,
    }
    status = 400
    for cls_name, code in status_map.items():
        if type(exc).__name__ == cls_name:
            status = code
            break
    return JSONResponse(
        status_code=status,
        content={"code": status * 100, "message": str(exc)},
    )


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """未预期异常返回 500，不暴露堆栈详情。"""
    logger.critical("未预期异常: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": 50000, "message": "服务器内部错误"},
    )


# ── 健康检查 ──
@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
