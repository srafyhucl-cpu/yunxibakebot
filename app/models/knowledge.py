"""
知识库数据模型。

存储店铺信息、产品介绍、政策、常见问题等。
LLM 对话时自动检索相关内容注入到 System Prompt 中。
"""

from dataclasses import dataclass
from enum import Enum


class KnowledgeCategory(str, Enum):
    """知识分类：门店信息 / 产品 / 政策 / 常见问题 / 售后"""
    STORE_INFO = "store_info"
    PRODUCT = "product"
    POLICY = "policy"
    FAQ = "faq"
    AFTER_SALES = "after_sales"


@dataclass
class KnowledgeEntry:
    """一条知识记录，含标题、正文、关键词和优先级。"""
    id: int = 0
    category: KnowledgeCategory = KnowledgeCategory.FAQ
    title: str = ""
    content: str = ""      # Markdown 格式
    keywords: str = ""      # 逗号分隔，用于模糊匹配
    priority: int = 0
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""
