"""ChatService 的知识上下文与 LLM 消息构造边界。"""

import time
from dataclasses import dataclass

from app.logger import setup_logger
from app.models.knowledge import KnowledgeEntry
from app.models.session import Session
from app.service.chat_intent import build_history_text
from app.service.chat_multimodal import apply_multimodal_image_message
from app.service.knowledge_retriever import KnowledgeRetriever
from app.service.llm.intent import IntentType
from app.service.llm.prompt import build_system_prompt
from app.service.llm.query_rewriter import rewrite_query
from app.service.session_manager import SessionManager

logger = setup_logger()

DEFAULT_SEARCH_QUERY = "芸熙烘焙 产品 价格"
KNOWLEDGE_SEARCH_LIMIT = 8


@dataclass(frozen=True)
class ChatContext:
    messages: list[dict]
    rag_ms: int


async def prepare_ai_conversation_messages(
    session_mgr: SessionManager,
    knowledge: KnowledgeRetriever,
    session: Session,
    user_query: str,
    intent: IntentType,
    timing: dict | None,
    history: list[dict] | None,
    history_text: str,
    image_base64: str | None,
) -> tuple[list[dict], str]:
    if history is None:
        history = await session_mgr.build_context(session.id)
        history_text = build_history_text(history)
    chat_context = await prepare_chat_context(
        knowledge=knowledge,
        user_query=user_query,
        history_text=history_text,
        intent=intent,
        history=history,
    )
    if timing is not None:
        timing["rag_ms"] = chat_context.rag_ms
    messages = chat_context.messages

    if image_base64:
        apply_multimodal_image_message(messages, image_base64, session.id)

    return messages, history_text


async def prepare_chat_context(
    knowledge: KnowledgeRetriever,
    user_query: str,
    history_text: str,
    intent: IntentType,
    history: list[dict],
) -> ChatContext:
    started_at = time.monotonic()
    knowledge_entries = await load_knowledge_entries(
        knowledge=knowledge,
        user_query=user_query,
        history_text=history_text,
        intent=intent,
    )
    messages: list[dict] = [
        {"role": "system", "content": build_system_prompt(knowledge_entries)},
    ]
    messages.extend(history)
    return ChatContext(
        messages=messages,
        rag_ms=round((time.monotonic() - started_at) * 1000),
    )


async def load_knowledge_entries(
    knowledge: KnowledgeRetriever,
    user_query: str,
    history_text: str,
    intent: IntentType,
) -> list[KnowledgeEntry]:
    if intent == IntentType.SMALL_TALK:
        return await knowledge.search_keyword_only(
            user_query, limit=KNOWLEDGE_SEARCH_LIMIT
        )

    search_query = user_query or DEFAULT_SEARCH_QUERY
    rewritten = await rewrite_query(search_query, history=history_text)
    try:
        return await knowledge.search(rewritten, limit=KNOWLEDGE_SEARCH_LIMIT)
    except Exception as exc:
        logger.error("知识库检索失败，使用空上下文继续: %s", exc)
        return []
