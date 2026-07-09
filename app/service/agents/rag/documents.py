"""知识条目与 LangChain Document 转换。"""

from typing import Any

from app.models.knowledge import KnowledgeEntry


def knowledge_entry_to_document(
    entry: KnowledgeEntry,
    extra_metadata: dict[str, Any] | None = None,
) -> Any:
    """把知识条目转换为 LangChain Document。"""
    from langchain_core.documents import Document

    metadata = {
        "knowledge_id": entry.id,
        "title": entry.title,
        "category": str(entry.category),
        "content_type": str(entry.content_type),
        "audience": entry.audience,
        "review_status": entry.review_status,
        "youzan_item_id": entry.youzan_item_id or "",
        "priority": entry.priority,
        "valid_from": entry.valid_from,
        "valid_until": entry.valid_until,
        "last_sync_source": entry.last_sync_source,
        "last_sync_ref": entry.last_sync_ref,
    }
    metadata.update(extra_metadata or {})
    return Document(
        page_content=entry.content,
        metadata=metadata,
    )


def knowledge_entries_to_documents(
    entries: list[KnowledgeEntry],
    extra_metadata: dict[str, Any] | None = None,
) -> list[Any]:
    """批量转换知识条目。"""
    return [
        knowledge_entry_to_document(entry, extra_metadata=extra_metadata)
        for entry in entries
    ]
