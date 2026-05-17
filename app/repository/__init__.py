"""
数据访问层统一导出。

各模块通过 Repo 实例操作数据库，不直接拼接 SQL。
"""

from app.repository.session_repo import SessionRepo
from app.repository.message_repo import MessageRepo
from app.repository.knowledge_repo import KnowledgeRepo
from app.repository.transfer_repo import TransferRepo

__all__ = [
    "SessionRepo",
    "MessageRepo",
    "KnowledgeRepo",
    "TransferRepo",
]
