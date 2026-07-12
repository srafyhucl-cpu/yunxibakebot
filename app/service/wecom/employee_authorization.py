"""企微员工机器人 actor、会话和角色授权策略。"""

from dataclasses import dataclass
from typing import Any

from app.config import settings


class EmployeeAuthorizationError(ValueError):
    """员工消息未通过授权。"""


@dataclass(frozen=True)
class EmployeeActor:
    user_id: str
    chat_id: str
    corp_id: str
    role: str


class EmployeeActorAuthorizer:
    """按配置白名单验证真实员工 actor。"""

    def authorize(self, message: dict[str, Any]) -> EmployeeActor:
        actor = _extract_actor(message)
        allowed_users = _split_allowlist(settings.WECOM_EMPLOYEE_ALLOWED_USERS)
        allowed_chats = _split_allowlist(settings.WECOM_EMPLOYEE_ALLOWED_CHATS)
        if settings.WECOM_EMPLOYEE_AUTH_REQUIRED and not allowed_users:
            raise EmployeeAuthorizationError("员工用户白名单未配置")
        if allowed_users and actor.user_id not in allowed_users:
            raise EmployeeAuthorizationError("员工用户不在白名单")
        if allowed_chats and actor.chat_id not in allowed_chats:
            raise EmployeeAuthorizationError("员工会话不在白名单")
        expected_corp = settings.WECOM_EMPLOYEE_CORP_ID.strip()
        if expected_corp and actor.corp_id != expected_corp:
            raise EmployeeAuthorizationError("员工企业身份不匹配")
        return actor

    def authorize_tool(self, actor: EmployeeActor, route_name: str) -> None:
        """限制运营类工具只能由配置的角色调用。"""
        ops_roles = _split_allowlist(settings.WECOM_EMPLOYEE_OPS_ROLES)
        if route_name in _OPS_ROUTES and ops_roles and actor.role not in ops_roles:
            raise EmployeeAuthorizationError("员工角色无权调用运营工具")


def _extract_actor(message: dict[str, Any]) -> EmployeeActor:
    sender = message.get("from")
    sender_map = sender if isinstance(sender, dict) else {}
    return EmployeeActor(
        user_id=str(sender_map.get("userid") or message.get("userid") or "").strip(),
        chat_id=str(
            message.get("chatid") or message.get("conversation_id") or ""
        ).strip(),
        corp_id=str(message.get("corpid") or message.get("corp_id") or "").strip(),
        role=str(message.get("role") or message.get("agent_role") or "").strip(),
    )


def _split_allowlist(raw_value: str) -> set[str]:
    return {item.strip() for item in raw_value.split(",") if item.strip()}


_OPS_ROUTES = frozenset(
    {
        "handoff_pending",
        "integration_status",
        "offline_review_summary",
        "ops_summary",
        "group_campaign_summary",
        "customer_lookup",
    }
)
