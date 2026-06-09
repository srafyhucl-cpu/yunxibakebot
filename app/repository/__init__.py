"""
数据访问层统一导出。

各模块通过 Repo 实例操作数据库，不直接拼接 SQL。
"""

from app.repository.session_repo import SessionRepo
from app.repository.message_repo import MessageRepo
from app.repository.knowledge_repo import KnowledgeRepo
from app.repository.transfer_repo import TransferRepo
from app.repository.customer_profile_repo import CustomerProfileRepo
from app.repository.conversation_review_repo import ConversationReviewRepo
from app.repository.knowledge_gap_repo import KnowledgeGapRepo

__all__ = [
    "SessionRepo",
    "MessageRepo",
    "KnowledgeRepo",
    "TransferRepo",
    "CustomerProfileRepo",
    "ConversationReviewRepo",
    "KnowledgeGapRepo",
]
