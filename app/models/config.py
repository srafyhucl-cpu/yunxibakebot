"""
店铺运营配置数据模型。

管理可由后台动态调整的运营参数（如主推款列表等）。
"""

from dataclasses import dataclass

FEATURED_PRODUCTS_KEY = "featured_products"


@dataclass
class ShopConfig:
    """一条店铺配置记录。"""
    key: str
    value: str
    updated_at: str = ""
