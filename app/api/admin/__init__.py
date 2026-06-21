"""管理后台 API canonical 包入口。

历史代码可继续通过 ``app.api.admin`` 导入鉴权工具和后台根路由。
"""

from app.api.admin.root import (
    ADMIN_SESSION_MAX_AGE_SECONDS,
    check_login,
    create_admin_router,
    has_admin_api_access,
    is_valid_admin_token,
    require_admin_token,
    verify_token,
)

__all__ = [
    "ADMIN_SESSION_MAX_AGE_SECONDS",
    "check_login",
    "create_admin_router",
    "has_admin_api_access",
    "is_valid_admin_token",
    "require_admin_token",
    "verify_token",
]
