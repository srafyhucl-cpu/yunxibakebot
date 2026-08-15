# 跨入口资产策略矩阵（X1 设计）

- status: proposed
- parent_trace_id: `20260812-member-loyalty-storedvalue`
- 拆分来源：2026-08-14 完整复核（评审问题 3、4）
- 关联 ADR：[0008](../harness-engineering/adr/0008-accounting-core-consistency.md)

## 背景

当前小程序与有赞并存。小程序 storefront API 中充值、余额支付、积分抵扣、券抵扣均**无服务端资产开关**（仅 `ALLOW_MOCK_PAYMENT`、`POINTS_AUTHORITY`、`COUPON_AUTHORITY` 三个开关）；仅隐藏前端入口可被直接 API 调用绕过。旧入口能力**待外部核验**：本仓代码仅能证明 Platform 未封装有赞储值/积分写 API（`member_api.py` 仅查询、`event_member.py` 仅事件镜像），**不能证明旧有赞小程序或后台具备 / 不具备写能力**；以有赞配置、旧小程序能力清单与证据确认后入证据索引。

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
- **策略固化时点（B1.7 修正：在首次不可逆承诺前固化，而非支付成功时）**：在**首次不可逆承诺**（余额预占、券 `RESERVE` 预占、创建微信支付会话——三者任一先发生）时，随 `payment.json` 固化 `payment_attempt_id + policy_version + asset_policy_snapshot`。支付会话已创建或余额 / 券已预占后、开关再关闭，该 `payment_attempt_id` 属于在途业务，**必须按快照完成结算**；不因开关关闭中断已收款订单。
- **授权三分类（B1.7）**：
  - **新业务**：新下单 / 新抵扣 / **新支付尝试**（新的 `payment_attempt_id`，含重试、超时后重新发起）必须按**实时策略**重新授权——任一是 `disabled` 即拒绝，不产生资产副作用。
  - **在途结算**：已固化的 `payment_attempt_id`（余额 / 券预占或微信支付会话已创建）按 `asset_policy_snapshot` 完成，不因实时开关关闭而中断。
  - **系统补偿**：退款 / 对账补偿按 `asset_policy_snapshot` 原路补偿，不禁用。
- **重试 / 超时 / 重新发起归属（B1.7）**：同一 `payment_attempt_id` 的重试沿用原快照；超时作废或重新发起生成**新 `payment_attempt_id`**，按新业务实时策略重新授权。
- **三类操作状态转换（明确）**：

  | 操作 | 读取 | 行为 |
  |---|---|---|
  | 新下单 / 新抵扣 / 新支付尝试（apply-points / apply-coupon / 充值 / 下单 / 重试重新发起） | 实时策略 | `disabled` 即拒绝（无副作用） |
  | 支付通知 / 在途结算（mock / 微信通知 / 储值全额，同一 `payment_attempt_id`） | `asset_policy_snapshot` | 按快照完成，不因实时开关关闭而中断 |
  | 退款 / 对账补偿 | `asset_policy_snapshot` | 不禁用，按快照原路补偿 |

- 资产策略**写入订单支付快照**（`payment.json` 内 `payment_attempt_id + policy_version + asset_policy_snapshot`），区分三态：`拒绝新业务` / `完成在途结算` / `退款对账补偿`。**不能用单一布尔开关阻断退款与对账补偿**。
- **持久 `payment_attempt` 表（B1.8 + B1.9）**：`payment.json` 可被覆盖，不能承载不可变支付尝试事实。新增 `payment_attempt` 表（v025+ 迁移），每行一次支付尝试，字段：`payment_attempt_id`（主键）、**`subject_type + subject_id`（B1.9：`order` / `recharge` 等聚合类型与实例 ID，替代单一 `order_id`）**、`provider`（`wechat` / `balance` / `mock`）、**`merchant_order_no`（微信 `out_trade_no`；仅 `provider=wechat` 强制 `UNIQUE NOT NULL` 且不可复用；`balance` / `mock` 无商户单号，置空）**、`amount_fen`、**`payment_snapshot_json`（B1.9：完整不可变支付快照——各资产分摊 / 券周期 / 币种 / 策略版本与快照 / 金额，替代 `snapshot_hash`）**、`status`（`created / processing / succeeded / failed / expired`）、`provider_transaction_id`（微信 transaction_id，异步回填）、`policy_version`、`asset_policy_snapshot`（JSON）、`created_at / updated_at`。
- **结算分派（B1.9）**：订单（微信差额 / 余额 / mock）、充值（微信 / mock 确认）按 `subject_type` 分派到对应结算路径，均以 `payment_attempt` 状态机推进并**与账务写入同一 UoW** 结算；充值真实回调按 `subject_type=recharge + merchant_order_no` 归属，避免真实回调无归属。
- **唯一活跃尝试（B1.9）**：每个 `(subject_type, subject_id)` 至多一个活跃尝试——新尝试以条件更新创建（`WHERE 不存在 status ∈ {created, processing} 的同主体尝试`），冲突即拒绝；**重复通知仅幂等 ACK**（同单号已 `succeeded` / `processing` 直接 ACK，不重复结算）；**冲突或过期尝试进入对账**，不静默覆盖。
- **回调结算校验（B1.8 + B1.9）**：微信支付通知回调**先按 `out_trade_no`（= `merchant_order_no`）查 `payment_attempt`**，再校验该尝试仍可结算（`status ∈ {created, processing}` 且金额一致、`payment_snapshot_json` 一致），通过后才按该尝试的 `asset_policy_snapshot` 结算；尝试不存在、状态已终态或金额 / 快照不匹配 → 拒绝结算并进入对账。
- **尝试失效（B1.8）**：超时或替代尝试发起后，原尝试置 `expired / failed` 终态**永久失效**；**禁止复用 `merchant_order_no`（`out_trade_no`）**——新尝试必须生成新的商户单号，杜绝迟到支付通知按新快照结算旧尝试。
- 开发 / 测试 / mock 阶段保持 `enabled`；进入受控真实测试或正式上线前，由项目负责人裁决逐项切换并留证。

## 积分门禁（B1.6 已裁决：关闭 Platform 积分写操作）

`POINTS_AUTHORITY=youzan` 下，Webhook 用有赞总积分覆盖本地余额，而小程序订单直接在本地扣分/发分/退款，且无有赞积分写接口——新旧入口并存会产生积分双花与延迟事件覆盖。正式开放前必须定稿防双花方案。

**裁决（项目负责人，B1.6）**：采用**关闭 Platform 积分写操作**——正式开放前 `ASSET_POINTS_WRITE=disabled`，小程序积分抵扣 / 发放 / 退款关闭，仅只读展示。无需有赞侧协调，风险最低；后续如需开放积分写，须重新走 FP-4B2 门禁裁决。

- 否决项：有赞幂等写入 + outbox/回查补偿（依赖真实有赞积分写接口与对账能力，实现最重）；关闭旧入口积分能力（需有赞运营协调停用，外部依赖不确定）。
- Webhook 镜像不视为同步方案（有覆盖延迟，不能保证一致）。

## 券双端门禁（B1.6 已裁决：关闭旧入口券能力 + 正式版关闭券抵扣）

**裁决（项目负责人，B1.6）**：**关闭旧入口券能力**（与有赞运营协调停用有赞券核销 / 发放入口）+ **正式版关闭券抵扣**（`ASSET_COUPON_WRITE=disabled`；真实券测试前做跨端双花检查，通过后再开放）。券数据模型以 ADR 0008 为唯一来源。

## 验收（实施阶段）

- 服务端资产开关生效：每个受控写操作在 `disabled` 时被拒绝（含直接 API 调用绕过测试）；支付快照三态（拒绝新业务 / 完成在途结算 / 退款对账补偿）测试通过，退款与补偿不被开关阻断。
- **承诺点固化测试（B1.7）**：余额预占 / 券 `RESERVE` / 微信支付会话任一创建后开关关闭，`payment_attempt_id` 按快照完成结算；同一 `payment_attempt_id` 重试沿用快照；超时重新发起生成新 `payment_attempt_id` 且按实时策略重新授权。
- **payment_attempt 校验（B1.8 + B1.9）**：`subject_type + subject_id` 主体模型，`provider=wechat` 时 `out_trade_no` 一对一不可复用（复用被唯一键拒绝）；每主体至多一个活跃尝试（条件更新）；重复通知幂等 ACK；回调按 `out_trade_no` 查尝试并校验状态 / 金额 / `payment_snapshot_json`；超时尝试置终态后迟到通知按新快照结算被拒绝（进入对账）；充值 / 订单 / 余额 / mock 结算分派与同一 UoW 行为有测试。
- 支付成功联动点统一读取开关 / 快照：**新业务禁写不产生资产副作用；在途结算与退款补偿按 `asset_policy_snapshot` 完成，不因实时开关关闭而中断**（覆盖"支付通知到达前关闭开关"场景）。
- **FP-4B2 门禁（B1.6 补强，不能以"矩阵文档存在"代替验收）**：正式开放前必须归档——
  1. 已选积分策略证据：`ASSET_POINTS_WRITE=disabled` 的配置与 `disabled` 时写操作拒绝的运行证据；
  2. 已选券策略证据：有赞侧停用旧入口券能力的确认 + `ASSET_COUPON_WRITE=disabled` 的配置与拒绝证据；
  3. 旧有赞小程序无储值 / 积分 / 券写能力的**外部核验证据**（旧小程序能力清单 / 有赞后台配置确认），并登记证据索引；
  4. **FP-2 不可逆边界审批项（B1.7）**：本地首次写入后仅 roll-forward 不回写有赞的风险列为正式放行的显式审批项。
