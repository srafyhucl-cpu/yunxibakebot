# 跨入口资产策略矩阵（X1 设计）

- status: proposed
- parent_trace_id: `20260812-member-loyalty-storedvalue`
- 拆分来源：2026-08-14 完整复核（评审问题 3、4）
- 关联 ADR：[0008](../harness-engineering/adr/0008-accounting-core-consistency.md)

## 背景

当前小程序与有赞并存。小程序 storefront API 中充值、余额支付、积分抵扣、券抵扣均**无服务端资产开关**（仅 `ALLOW_MOCK_PAYMENT`、`POINTS_AUTHORITY`、`COUPON_AUTHORITY` 三个开关）；仅隐藏前端入口可被直接 API 调用绕过。旧有赞小程序侧核验结论：**无储值/积分写 API**（`member_api.py` 仅查询积分/券/卡，无储值写；`event_member.py` 仅四类事件镜像），旧小程序无储值操作入口。

## 服务端资产策略矩阵（目标）

新增服务端资产策略配置（`app/config.py`），对四类资产写操作独立控制，在**应用服务层与支付成功联动点强制执行**（不依赖前端隐藏）：

| 资产写操作 | 配置开关（默认） | 受控入口 |
|---|---|---|
| 储值充值 / 余额入账 | `ASSET_STORED_VALUE_WRITE`（default `enabled`，上线前按裁决改 `disabled`） | `stored_value/recharge.py` 入账；`orders.py pay-with-balance`、`prepare-combined-payment` |
| 储值余额支付 | `ASSET_STORED_VALUE_PAY`（同上） | `stored_value/payment.py:42/:106` |
| 积分抵扣 / 发放 / 退款 | `ASSET_POINTS_WRITE`（同上） | `points/__init__.py apply_points`；`points/payment.py` 发分/退回 |
| 券应用 / 核销 / 退回 | `ASSET_COUPON_WRITE`（同上） | `coupon/__init__.py apply_coupon`；`coupon/payment.py` 核销/BACK |
| 支付成功联动（置 paid + 发分 + 核销） | 由上述开关组合 + `PAYMENT_COMMIT_ASSET_FLUSH` | `payment_runtime.py:156-157`、`payment_notification.py:137-138`、`stored_value/payment.py:100-101` 三处统一切入 |

- 开关在**应用服务层**与**支付成功联动点**强制执行：`disabled` 时对应写操作拒绝并返回受控错误（非 401 伪装），覆盖直接 API 调用绕过。
- 开发 / 测试 / mock 阶段保持 `enabled`；进入受控真实测试或正式上线前，由项目负责人裁决逐项切换并留证。

## 积分门禁（评审问题 3，三选一）

`POINTS_AUTHORITY=youzan` 下，Webhook 用有赞总积分覆盖本地余额，而小程序订单直接在本地扣分/发分/退款，且无有赞积分写接口——新旧入口并存会产生积分双花与延迟事件覆盖。正式开放前必须三选一（并入 FP-4B2 门禁）：

1. **关闭旧入口积分能力**：有赞侧不再产生积分事件 / 不再覆盖（需与有赞运营协调停用）。
2. **关闭 Platform 积分写操作**：小程序侧禁用积分抵扣/发放/退款（`ASSET_POINTS_WRITE=disabled`），只读展示。
3. **实现有赞幂等写入 + outbox/回查补偿**：将本地扣分/发分/退款同步到有赞（幂等写入 + outbox + 回查补偿），保持双端一致。

Webhook 镜像不视为同步方案（有覆盖延迟，不能保证一致）。

## 券双端门禁（并入 FP-4B）

沿用三选一：有赞核销同步 / 关闭旧入口 / 正式版关闭券抵扣 + 真实券测试前跨端双花检查。

## 验收（实施阶段）

- 服务端资产开关生效：每个受控写操作在 `disabled` 时被拒绝（含直接 API 调用绕过测试）。
- 支付成功联动点统一读取开关，任一层禁写则不产生资产副作用。
- 积分门禁三选一落地并有幂等/补偿测试。
- 旧有赞小程序无储值/积分写操作核验结论入证据索引。
