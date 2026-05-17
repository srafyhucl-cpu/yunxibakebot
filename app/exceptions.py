"""
应用异常层级。

所有业务异常继承自 AppError，方便 FastAPI 全局捕获后统一返回。
"""


class AppError(Exception):
    """应用异常基类，所有业务异常继承于此。"""


class AuthError(AppError):
    """认证失败：签名校验、Token 过期等。"""


class NotFoundError(AppError):
    """资源不存在：会话、消息、用户等查找不到。"""


class LLMError(AppError):
    """DeepSeek API 调用失败：网络超时、频率限制等。"""


class APIError(AppError):
    """外部 API 调用失败：有赞、企微接口异常。"""


class ConfigError(AppError):
    """配置错误：环境变量缺失、格式不正确等。"""
