"""
配置管理。

使用 pydantic-settings 从 .env 文件和环境变量加载配置。
所有敏感信息（API Key、Secret）不进代码仓库。
"""

from pathlib import Path

from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


def _read_version() -> str:
    """从项目根目录 VERSION 文件读取版本号，作为版本号的唯一来源。"""
    version_file = PROJECT_ROOT / "VERSION"
    return version_file.read_text(encoding="utf-8").strip()


APP_VERSION: str = _read_version()


class Settings(BaseSettings):
    """应用配置，字段默认值可被 .env 和环境变量覆盖。"""

    model_config = {
        "env_file": ENV_FILE,
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
    ENABLE_HYBRID_RETRIEVAL: bool = False
    RRF_K: int = 60
    ENABLE_CUSTOMER_MEMORY: bool = False
    ENABLE_REPLY_GUARD: bool = False
    ENABLE_OFFLINE_REVIEW: bool = False
    OFFLINE_REVIEW_INTERVAL_HOURS: float = 6.0
    OFFLINE_REVIEW_MAX_SESSIONS: int = 200

    # ── DeepSeek 大模型（已废弃，保留字段兼容） ──
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    # 视觉识别模型（已废弃，保留字段兼容）
    DEEPSEEK_VISION_MODEL: str = ""
    DEEPSEEK_TIMEOUT_SECONDS: float = 15.0

    # ── 小米 MiMo 大模型（主力 LLM） ──
    MIMO_API_KEY: str = ""
    MIMO_BASE_URL: str = "https://api.xiaomimimo.com/v1"
    # 文本对话模型
    MIMO_CHAT_MODEL: str = "mimo-v2.5"
    # 视觉/多模态模型（支持图片输入）
    MIMO_VISION_MODEL: str = "mimo-v2.5"
    # 语音转文字模型（ASR）
    MIMO_ASR_MODEL: str = "mimo-v2.5-asr"
    MIMO_TIMEOUT_SECONDS: float = 120.0

    # ── 有赞云 ──
    YOUZAN_CLIENT_ID: str = ""
    YOUZAN_CLIENT_SECRET: str = ""
    YOUZAN_KDT_ID: str = ""
    YOUZAN_MOCK_MODE: bool = True
    YOUZAN_AUTH_URL: str = "https://open.youzanyun.com/auth/token"
    YOUZAN_API_BASE: str = "https://open.youzanyun.com/api"
    YOUZAN_GOODS_H5_BASE_URL: str = "https://h5.youzan.com/v2/showcase/goods"
    YOUZAN_HTTP_TIMEOUT_SECONDS: float = 10.0

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
    WECOM_API_BASE: str = "https://qyapi.weixin.qq.com/cgi-bin"
    WECOM_HTTP_TIMEOUT_SECONDS: float = 10.0
    # ── 企业微信（微信客服） ──
    # 微信客服与自建应用共用同一个回调URL / Token / EncodingAESKey
    # 只需额外配置客服账号 ID，用于发送消息时指定 open_kfid
    WECOM_KF_ID: str = ""  # 微信客服账号 ID (open_kfid)，格式如 wkxxxxxxxx
    WECOM_KF_SESSION_IDLE_CLOSE_SECONDS: int = 7200
    WECOM_KF_WELCOME_TEXT: str = "您好，我是芸熙烘焙智能助手，已接入为您继续服务。"
    WECOM_KF_SERVICER_USERID: str = (
        ""  # 转人工时的默认接待人员 userid（企微内部userid）
    )


settings = Settings()
