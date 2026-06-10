"""微信客服人工接管状态检查器。"""

from datetime import datetime

from app.config import settings
from app.logger import setup_logger
from app.models.session import SessionStatus

logger = setup_logger()

WECOM_KF_CHANNEL = "wecom_kf"


class DbHandoffSessionChecker:
    """从数据库判断用户是否处于人工接管状态。"""

    async def is_handoff_user(self, external_userid: str) -> bool:
        if not external_userid:
            return False
        from app.database import db_session_scope
        from app.repository.session_repo import SessionRepo

        async with db_session_scope():
            session_repo = SessionRepo()
            session = await session_repo.get_active(external_userid, WECOM_KF_CHANNEL)
            if session is None:
                return False
            if session.status not in (
                SessionStatus.TRANSFER_PENDING,
                SessionStatus.HUMAN_SERVICE,
            ):
                return False
            if _is_idle_handoff_session(session.updated_at):
                await session_repo.update_status(session.id, SessionStatus.CLOSED)
                logger.info(
                    "微信客服人工会话空闲超时，已关闭本地旧会话 user=%s session=%s",
                    external_userid,
                    session.id,
                )
                return False
            return True


def _is_idle_handoff_session(updated_at: str) -> bool:
    if not updated_at:
        return False
    try:
        updated = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        logger.warning("无法解析会话 updated_at=%s，跳过空闲关闭判断", updated_at)
        return False
    idle_seconds = (datetime.now() - updated).total_seconds()
    return idle_seconds > settings.WECOM_KF_SESSION_IDLE_CLOSE_SECONDS
