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

    # 语义向量搜索服务（加载已有索引或构建新的）
    from app.service.embedding_search import EmbeddingSearcher
    vs = EmbeddingSearcher()
    vs_path = settings.EMBEDDING_PATH
    if Path(vs_path).exists():
        await asyncio.to_thread(vs.load, vs_path)

    if vs.doc_count > 0:
        logger.info("向量索引已就绪: %d 条文档", vs.doc_count)
    else:
        docs = await knowledge_repo.get_all_titles()
        if docs:
            await asyncio.to_thread(vs.build, docs)
            await asyncio.to_thread(vs.save, vs_path)
            logger.info("向量索引已构建: %d 条文档", vs.doc_count)

    # Service 层
    knowledge_retriever = KnowledgeRetriever(knowledge_repo, vs, config_repo=config_repo)
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
        chat_service, session_repo, message_repo, transfer_repo, knowledge_repo=knowledge_repo,
    ))
    app.include_router(create_shop_config_router(config_repo, knowledge_repo))
    app.include_router(wecom_router)

    logger.info("芸熙烘焙 AI 客服启动完成，监听端口: %d", settings.SERVER_PORT)
    yield
    # ── shutdown ──
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
