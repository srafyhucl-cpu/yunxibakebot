"""lifespan 阶段 Service 层初始化逻辑（从 main.py 拆出）。

第一阶段平台化重组后，这里优先装配 Platform 的 canonical 领域服务名，
同时保留旧 miniapp_* key 作为兼容别名，避免现有路由和测试立即失效。
"""

from typing import Any

from app.service.chat import ChatService
from app.service.knowledge_retriever import KnowledgeRetriever
from app.service.youzan.client import YouzanClient
from app.service.youzan.event_handler import YouzanEventHandler
from app.service.youzan.product_reconciler import ProductReconcileService


def init_services(repos: dict[str, Any], vs: Any, bm25: Any = None) -> dict[str, Any]:
    """初始化 Service 层，返回服务字典。"""
    knowledge_retriever = KnowledgeRetriever(
        repos["knowledge_repo"],
        vs,
        config_repo=repos["config_repo"],
        bm25=bm25,
    )

    from app.service.admin import AdminService
    from app.service.catalog import CatalogApplicationService
    from app.service.channels.storefront import StorefrontAuthService
    from app.service.conversation import StorefrontConversationService
    from app.service.customer import CustomerAddressService
    from app.service.knowledge_admin import KnowledgeAdminService
    from app.service.knowledge_sync import KnowledgeSyncService
    from app.service.observability import ObservabilityService
    from app.service.ops import (
        ShopConfigurationService,
        ShopPageConfigurationService,
    )
    from app.service.order import OrderApplicationService
    from app.service.transfer_manager import TransferManager

    admin_service = AdminService(
        session_repo=repos["session_repo"],
        message_repo=repos["message_repo"],
        transfer_repo=repos["transfer_repo"],
        knowledge_repo=repos["knowledge_repo"],
        config_repo=repos["config_repo"],
        youzan_product_repo=repos["youzan_product_repo"],
    )
    observability_service = ObservabilityService(
        knowledge_repo=repos["knowledge_repo"],
        product_repo=repos["youzan_product_repo"],
        history_repo=repos["history_repo"],
        webhook_repo=repos["webhook_event_repo"],
    )
    knowledge_sync_service = KnowledgeSyncService(
        knowledge_repo=repos["knowledge_repo"],
        history_repo=repos["history_repo"],
        embedding_searcher=vs,
    )
    knowledge_admin_service = KnowledgeAdminService(
        knowledge_repo=repos["knowledge_repo"],
        admin_repo=repos["knowledge_admin_repo"],
        history_repo=repos["history_repo"],
        sync_service=knowledge_sync_service,
    )
    catalog_service = CatalogApplicationService(
        product_repo=repos["knowledge_product_repo"],
        knowledge_repo=repos["knowledge_repo"],
        config_repo=repos["config_repo"],
        youzan_product_repo=repos["youzan_product_repo"],
    )
    order_service = OrderApplicationService(
        order_repo=repos["order_repo"],
        event_repo=repos["order_event_repo"],
        session_repo=repos["session_repo"],
        product_repo=repos["youzan_product_repo"],
        inventory_repo=repos["youzan_inventory_repo"],
        config_repo=repos["config_repo"],
    )
    customer_address_service = CustomerAddressService(
        address_repo=repos["miniapp_address_repo"],
        audit_repo=repos["miniapp_address_audit_repo"],
    )
    storefront_auth_service = StorefrontAuthService()
    transfer_mgr = TransferManager(repos["transfer_repo"])
    shop_page_configuration_service = ShopPageConfigurationService(repos["config_repo"])
    shop_configuration_service = ShopConfigurationService(repos["config_repo"])

    youzan_client = YouzanClient(config_repo=repos["config_repo"])
    youzan_event_handler = YouzanEventHandler(
        db=None,
        knowledge_retriever=knowledge_retriever,
        youzan_client=youzan_client,
        audit_repo=repos["webhook_event_repo"],
    )
    reconcile_service = ProductReconcileService(
        youzan_client=youzan_client,
        product_repo=repos["youzan_product_repo"],
        history_repo=repos["history_repo"],
        knowledge_product_repo=repos["knowledge_product_repo"],
    )

    chat_service = ChatService(
        session_repo=repos["session_repo"],
        message_repo=repos["message_repo"],
        transfer_repo=repos["transfer_repo"],
        knowledge_retriever=knowledge_retriever,
        youzan_client=youzan_client,
        youzan_webhook_events_repo=repos["webhook_event_repo"],
        youzan_event_handler=youzan_event_handler,
        analytics_repo=repos["analytics_repo"],
        customer_profile_repo=repos.get("customer_profile_repo"),
    )
    storefront_conversation_service = StorefrontConversationService(
        chat_service=chat_service,
        session_repo=repos["session_repo"],
        message_repo=repos["message_repo"],
        transfer_mgr=transfer_mgr,
    )

    return {
        "admin_service": admin_service,
        "observability_service": observability_service,
        "knowledge_sync_service": knowledge_sync_service,
        "knowledge_admin_service": knowledge_admin_service,
        "storefront_auth_service": storefront_auth_service,
        "catalog_service": catalog_service,
        "order_service": order_service,
        "customer_address_service": customer_address_service,
        "transfer_mgr": transfer_mgr,
        "shop_page_configuration_service": shop_page_configuration_service,
        "shop_configuration_service": shop_configuration_service,
        "youzan_client": youzan_client,
        "youzan_event_handler": youzan_event_handler,
        "reconcile_service": reconcile_service,
        "chat_service": chat_service,
        "storefront_conversation_service": storefront_conversation_service,
        # 兼容旧命名，后续逐步缩减
        "miniapp_auth_service": storefront_auth_service,
        "miniapp_catalog_service": catalog_service,
        "miniapp_order_service": order_service,
        "miniapp_address_service": customer_address_service,
        "miniapp_chat_service": storefront_conversation_service,
        "shop_page_config_service": shop_page_configuration_service,
    }
