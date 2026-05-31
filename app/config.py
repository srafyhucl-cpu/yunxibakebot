"""
配置管理。

使用 pydantic-settings 从 .env 文件和环境变量加载配置。
所有敏感信息（API Key、Secret）不进代码仓库。
"""

from pydantic_settings import BaseSettings


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
    DEEPSEEK_TIMEOUT_SECONDS: float = 15.0

    # ── 有赞云 ──
    YOUZAN_CLIENT_ID: str = ""
    YOUZAN_CLIENT_SECRET: str = ""
    YOUZAN_KDT_ID: str = ""
    YOUZAN_MOCK_MODE: bool = True

    # ── 管理后台 ──
    ADMIN_API_TOKEN: str = ""

    # ── 企业微信（客户联系） ──
    WECOM_CORP_ID: str = ""
    WECOM_AGENT_ID: str = ""
    WECOM_SECRET: str = ""
    WECOM_TOKEN: str = ""
    WECOM_ENCODING_AES_KEY: str = ""
    WECOM_STAFF_ID: str = ""  # 客服小李的企微 USER_ID
    WECOM_ROBOT_WEBHOOK: str = ""  # 企微值班群机器人 WEBHOOK 地址 (选填，支持群机器人)


settings = Settings()
