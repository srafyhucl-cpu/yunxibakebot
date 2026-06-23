"""前台渠道用户标识校验。"""

from fastapi import HTTPException


def require_storefront_user_id(value: str | None) -> str:
    """要求请求显式携带已登录的小程序用户标识。"""
    user_id = (value or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录或会话未就绪，请先重新登录")
    return user_id
