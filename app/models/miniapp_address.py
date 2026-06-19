"""小程序收货地址模型。"""

from dataclasses import dataclass


@dataclass
class MiniappAddress:
    """小程序用户收货地址。"""

    id: str
    user_id: str
    receiver_name: str
    receiver_phone: str
    address: str
    is_default: int = 0
    created_at: str = ""
    updated_at: str = ""


@dataclass
class MiniappAddressAuditEntry:
    """小程序地址后台操作审计记录。"""

    id: int = 0
    address_id: str = ""
    user_id: str = ""
    operator: str = ""
    action: str = ""
    before_json: str = "{}"
    after_json: str = "{}"
    note: str = ""
    created_at: str = ""
