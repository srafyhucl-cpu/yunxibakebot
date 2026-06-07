"""
配置管理。

使用 pydantic-settings 从 .env 文件和环境变量加载配置。
所有敏感信息（API Key、Secret）不进代码仓库。
"""

from pathlib import Path

from pydantic_settings import BaseSettings


def _read_version() -> str:
    """从项目根目录 VERSION 文件读取版本号，作为版本号的唯一来源。"""
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    return version_file.read_text(encoding="utf-8").strip()


APP_VERSION: str = _read_version()


class Settings(BaseSettings):
    """应用配置，字段默认值可被 .env 和环境变量覆盖。"""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # .env 中未定义的额外字段忽略，不报错
    }

    # ── 服务配置 ──
    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = 7001
    LOG_LEVEL: str = "info"

    # ── 数据库 ──
    DB_PATH: str = "data/bot.db"
    EMBEDDING_INDEX_DIR: str = "data/embeddings"

    # ── DeepSeek 大模型 ──
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    # 视觉识别模型（支持图片输入的多模态模型），默认同上
    DEEPSEEK_VISION_MODEL: str = ""
    DEEPSEEK_TIMEOUT_SECONDS: float = 15.0

    # ── 有赞云 ──
    YOUZAN_CLIENT_ID: str = ""
    YOUZAN_CLIENT_SECRET: str = ""
    YOUZAN_KDT_ID: str = ""
    YOUZAN_MOCK_MODE: bool = True

    # ── 管理后台 ──
    # 注意：生产环境必须在 .env 中设置强密码，不能使用默认值
    ADMIN_API_TOKEN: str = "CHANGE_ME_IN_PRODUCTION_ENV"

    # ── 企业微信（客户联系） ──
    WECOM_CORP_ID: str = ""
    WECOM_AGENT_ID: str = ""
    WECOM_SECRET: str = ""
    WECOM_TOKEN: str = ""
    WECOM_ENCODING_AES_KEY: str = ""
    WECOM_STAFF_ID: str = ""  # 客服小李的企微 USER_ID
    WECOM_ROBOT_WEBHOOK: str = ""  # 企微值班群机器人 WEBHOOK 地址 (选填，支持群机器人)

    # ── 企业微信（微信客服） ──
    # 微信客服与自建应用共用同一个回调URL / Token / EncodingAESKey
    # 只需额外配置客服账号 ID，用于发送消息时指定 open_kfid
    WECOM_KF_ID: str = ""  # 微信客服账号 ID (open_kfid)，格式如 wkxxxxxxxx
    WECOM_KF_SERVICER_USERID: str = (
        ""  # 转人工时的默认接待人员 userid（企微内部userid）
    )


settings = Settings()
