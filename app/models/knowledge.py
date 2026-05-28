"""知识库数据模型。"""

from dataclasses import dataclass
from enum import Enum


class KnowledgeCategory(str, Enum):
    STORE_INFO = "store_info"
    PRODUCT = "product"
    POLICY = "policy"
    FAQ = "faq"
    AFTER_SALES = "after_sales"


class KnowledgeContentType(str, Enum):
    PRODUCT = "product"
    FAQ = "faq"
    RULE = "rule"
    SCRIPT = "script"


class VectorSyncStatus(str, Enum):
    PENDING = "pending"
    SYNCING = "syncing"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class KnowledgeEntry:
    id: int = 0
    category: KnowledgeCategory = KnowledgeCategory.FAQ
    content_type: str = KnowledgeContentType.FAQ
    title: str = ""
    content: str = ""
    keywords: str = ""
    priority: int = 0
    is_active: bool = True
    youzan_item_id: str | None = None
    last_sync_source: str = ""
    last_sync_ref: str = ""
    content_origin: str = "admin_manual"
    created_by: str = ""
    updated_by: str = ""
    suggested_category: str = ""
    suggest_reason: str = ""
    vector_sync_status: str = VectorSyncStatus.PENDING
    vector_synced_at: str = ""
    vector_sync_error: str = ""
    vector_sync_retry_count: int = 0
    created_at: str = ""
    updated_at: str = ""
