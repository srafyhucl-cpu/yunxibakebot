"""统一支付应用服务结构化错误（D1-A.1 复核 R5）。

- 错误分流不得依赖中文字符串子串匹配：结算/预占失败路径按
  `PaymentAccountError`（isinstance）判定转 `manual_review` 还是
  `settling_retry`——账户状态型错误（账户缺失 / 余额不足 / 历史未绑定）
  一律 manual_review（重试无益，需人工）；其余错误 settling_retry（可重放）。
- `code` 提供机器可读错误码（account_missing / balance_insufficient /
  points_insufficient / account_changed / account_unresolved / legacy_unbound），
  `message` 为面向调用方/日志的中文说明（与既有测试断言兼容）。
"""

from __future__ import annotations

__all__ = ["PaymentAccountError"]


class PaymentAccountError(ValueError):
    """账户状态型错误：结算 / 预占失败应转 manual_review（而非 settling_retry）。

    - account_missing：不可变账户 ID 查无（删除/漂移），禁止按手机号替代；
    - balance_insufficient / points_insufficient：结算时余额/积分不足（含预占），
      需人工复核（不自动重放）；
    - account_changed：快照绑定账户与当前解析账户不一致（漂移阻断）；
    - account_unresolved：会员手机号无法解析；
    - legacy_unbound：历史快照未绑定账户 ID，禁止按手机号补绑结算。
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
