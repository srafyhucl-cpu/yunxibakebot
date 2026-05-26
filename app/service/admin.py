"""管理后台业务服务层。"""

import json

from app.models.content_change_history import (
    ChangeAction,
    ChangeEntityType,
    SyncSource,
)
from app.models.config import FEATURED_PRODUCTS_KEY
from app.models.knowledge import KnowledgeEntry
from app.models.message import Message
from app.models.session import Session, SessionStatus
from app.models.transfer import HumanTransfer
from app.config import settings
from app.repository.config_repo import ConfigRepo
from app.repository.content_change_history_repo import ContentChangeHistoryRepo
from app.repository.knowledge_repo import KnowledgeRepo
from app.repository.message_repo import MessageRepo
from app.repository.session_repo import SessionRepo
from app.repository.transfer_repo import TransferRepo
from app.service.observability import ContentChangeLogger, build_knowledge_change_summary


class AdminService:
    """封装管理后台所需的底层数据操作，防止 api 直接穿透到 repository。"""

    def __init__(
        self,
        session_repo: SessionRepo,
        message_repo: MessageRepo,
        transfer_repo: TransferRepo,
        knowledge_repo: KnowledgeRepo,
        config_repo: ConfigRepo,
    ) -> None:
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._transfer_repo = transfer_repo
        self._knowledge_repo = knowledge_repo
        self._config_repo = config_repo

    # ── 会话与转人工 ──
    async def get_pending_transfers(self) -> list[HumanTransfer]:
        return await self._transfer_repo.get_pending()

    async def get_all_active_sessions(self) -> list[Session]:
        return await self._session_repo.get_all_active()

    async def get_all_active(self) -> list[Session]:
        return await self.get_all_active_sessions()

    async def get_recent_sessions(self, limit: int = 10) -> list[Session]:
        return await self._session_repo.get_recent(limit=limit)

    async def get_recent(self, limit: int = 10) -> list[Session]:
        return await self.get_recent_sessions(limit=limit)

    async def get_session(self, session_id: str) -> Session | None:
        return await self._session_repo.get(session_id)

    async def get(self, session_id: str) -> Session | None:
        return await self.get_session(session_id)

    async def get_active_session(self, user_id: str, channel: str) -> Session | None:
        return await self._session_repo.get_active(user_id, channel)

    async def get_active(self, user_id: str, channel: str) -> Session | None:
        return await self.get_active_session(user_id, channel)

    async def get_named_sessions(self, channel: str) -> list[Session]:
        return await self._session_repo.get_named(channel=channel)

    async def get_named(self, channel: str) -> list[Session]:
        return await self.get_named_sessions(channel)

    async def get_session_messages(self, session_id: str) -> list[Message]:
        return await self._message_repo.get_by_session(session_id)

    async def get_by_session(self, session_id: str) -> list[Message]:
        return await self.get_session_messages(session_id)

    async def update_status(self, session_id: str, status: str) -> None:
        await self._session_repo.update_status(session_id, SessionStatus(status))

    async def update_extra(self, session_id: str, extra_info: str) -> None:
        await self._session_repo.update_extra(session_id, extra_info)

    async def name_session(self, session_id: str, name: str) -> bool:
        session = await self._session_repo.get(session_id)
        if not session:
            return False
        extra = json.loads(session.extra_info or "{}")
        extra["name"] = name
        await self._session_repo.update_extra(session_id, json.dumps(extra, ensure_ascii=False))
        return True

    async def discard_session(self, session_id: str) -> bool:
        session = await self._session_repo.get(session_id)
        if not session:
            return False
        await self._session_repo.update_status(session_id, "closed")
        return True

    async def activate_session(self, session_id: str) -> None:
        await self._session_repo.update_status(session_id, "active")

    # ── 知识库与商品管理 ──
    async def count_knowledge(self) -> int:
        return await self._knowledge_repo.count_all()

    async def get_all_products(self, search: str = "", limit: int = 30, offset: int = 0) -> list[KnowledgeEntry]:
        return await self._knowledge_repo.get_all_products(search=search, limit=limit, offset=offset)

    async def count_products(self, search: str = "") -> int:
        return await self._knowledge_repo.count_products(search=search)

    async def get_product(self, product_id: int) -> KnowledgeEntry | None:
        return await self._knowledge_repo.get_by_id(product_id)

    async def toggle_product_active(self, product_id: int) -> bool | None:
        """切换商品上架状态。如果商品不存在返回 None，否则返回新的状态。"""
        entry = await self._knowledge_repo.get_by_id(product_id)
        if not entry:
            return None
        new_status = not bool(entry.is_active)
        await self._knowledge_repo.update_active(
            product_id,
            new_status,
            sync_source=SyncSource.ADMIN_MANUAL,
            sync_ref=str(product_id),
        )
        category = entry.category.value if hasattr(entry.category, "value") else str(entry.category)
        await ContentChangeLogger(ContentChangeHistoryRepo(self._knowledge_repo._db)).log_success(
            entity_type=ChangeEntityType.KNOWLEDGE,
            entity_key=str(product_id),
            category=category,
            title=entry.title,
            source=SyncSource.ADMIN_MANUAL,
            source_ref=str(product_id),
            action=ChangeAction.ACTIVATE if new_status else ChangeAction.DEACTIVATE,
            change_summary=build_knowledge_change_summary(
                title=entry.title,
                category=category,
                priority=entry.priority,
                is_active=new_status,
            ),
        )
        return new_status

    # ── 店铺配置（主推款等） ──
    async def get_featured_products(self) -> list[str]:
        return await self._config_repo.get_list(FEATURED_PRODUCTS_KEY)

    async def set_featured_products(self, products: list[str]) -> None:
        await self._config_repo.set_list(FEATURED_PRODUCTS_KEY, products)

    async def get_settings_summary(self) -> dict:
        featured_products = await self.get_featured_products()
        product_total = await self.count_products()
        return {
            "shop": {
                "server_host": settings.SERVER_HOST,
                "server_port": settings.SERVER_PORT,
                "database_path": settings.DB_PATH,
                "embedding_path": settings.EMBEDDING_PATH,
                "featured_product_count": len(featured_products),
                "product_total": product_total,
            },
            "channels": {
                "youzan": {
                    "client_id_configured": _is_configured(settings.YOUZAN_CLIENT_ID),
                    "client_secret_configured": _is_configured(settings.YOUZAN_CLIENT_SECRET),
                    "kdt_id_configured": _is_configured(settings.YOUZAN_KDT_ID),
                    "webhook_token_configured": _is_configured(settings.YOUZAN_WEBHOOK_TOKEN),
                    "mock_mode": settings.YOUZAN_MOCK_MODE,
                },
                "wecom": {
                    "corp_id_configured": _is_configured(settings.WECOM_CORP_ID),
                    "agent_id_configured": _is_configured(settings.WECOM_AGENT_ID),
                    "secret_configured": _is_configured(settings.WECOM_SECRET),
                    "token_configured": _is_configured(settings.WECOM_TOKEN),
                    "encoding_aes_key_configured": _is_configured(settings.WECOM_ENCODING_AES_KEY),
                    "staff_id_configured": _is_configured(settings.WECOM_STAFF_ID),
                    "robot_webhook_configured": _is_configured(settings.WECOM_ROBOT_WEBHOOK),
                },
            },
            "api": {
                "admin_token_configured": _is_configured(settings.ADMIN_API_TOKEN),
                "deepseek_api_key_configured": _is_configured(settings.DEEPSEEK_API_KEY),
                "deepseek_base_url": settings.DEEPSEEK_BASE_URL,
                "deepseek_model": settings.DEEPSEEK_MODEL,
                "deepseek_timeout_seconds": settings.DEEPSEEK_TIMEOUT_SECONDS,
            },
        }


def _is_configured(value: object) -> bool:
    return bool(str(value or "").strip())
