# ADR 0008：账务核心一致性（Unit of Work / 券事件-投影 / 持久退款聚合）

- status: proposed
- date: 2026-08-14
- trace_id: `20260814-member-loyalty-accounting-contract`
- decision_owner: project owner（决策主体 / 唯一批准人）
- technical_advisor: AI (Codex)（仅技术建议，不构成批准）
- revised_at: 2026-08-15（B1.6 合同完成包：补齐真实 UoW 清单与 outbox schema、定稿券事件合同、明确退款 Saga 语义并记录项目负责人三项裁决；B1.7 合同收口：券命令模型 / RESERVED 预占 / 投影 CAS、净额退款与退款预占、outbox fencing、新账务仓储入零 commit 契约；B1.8 合同修正：transition_key 含类型与支付尝试（修复 RESERVE/CONSUME 键冲突）、order_refund_quota 单条条件更新预占、上游版本合同与重建 UoW 原子性、持久 payment_attempt 表；B1.9 合同收口：事件版本合同与 cycle_no CAS、微信退款分派状态机与预占释放、refund_aggregate 绑定 payment_attempt_id、不可变 payment_snapshot_json；B2.0 合同收口：资金腿 ledger_operation 原子合同、退款主体与额度表泛化（payment_refund_quota）、充值退款政策（manual_review+冻结）、退款查询独立于 outbox、券事件三类分离与 legacy 统一公式；B3 合同收口（B2.0 评审 9 项一次性收口，评审结论暂不通过、方案 B）：资金腿与预占持久化（payment_attempt_leg + account_hold + 可用余额公式 + order.payment 降级为引用/展示缓存 + 统一支付应用服务）、支付提供方事件 inbox 与先持久化再 ACK 协议（回调固定校验验签/mchid/appid/trade_state/金额/币种/商户单号/交易号）、outbox 补 wechat_order_query 与预下单状态 CAS、逐腿 payment_refund_leg_quota 与充值余额不足 manual_review 优先（禁止先自动外部退款）、退款三状态拆分（dispatch_status/provider_refund_status/outbox status）与 confirmed_refunded/confirmed_not_refunded 枚举统一、authority_epoch 不可变资产矩阵与队列围栏（queue_control/claim_token/同事务入队）、coupon_observation 与 reconcile_hold、券观察与本地当前态冲突裁决、删除 legacy 旧键公式残留、证据检查器 git cat-file --batch 批处理；B3.1 合同收口（B3 最终评审 9 项一次性收口，评审结论暂不通过、方案 B）：双远端审阅基线固定（origin/server 的 codex/r4c-ci-evidence 均推送 8ec3b64、master 保持 344b66a 不动）、account_hold 绑定不可变账户主键 member_balance_id 与支付状态机补全（cancelled / manual_review，manual_review 未解除前禁止同主体新支付尝试）、payment_provider_event 租约 CAS 协议（received/processing/processed/failed/dead_letter，仅 processed 后同键重复通知才 200，落库后崩溃可重领）、prepay_unknown 固定映射（已支付→settling / 未支付先关单再终态释放 / 未知保持占用退避查询或转 manual_review，仅已持久化可用会话进 prepay_ready，禁止支付会话写回不可变快照）、逐腿退款确定性差分分摊（allocation(累计后)−allocation(累计前) + 固定腿排序）与 accepted 后 next_query_at/query_generation 持续查询、积分幂等键按动作拆分（points_used / points_awarded 分别维护额度）与持久短缺债务表 refund_shortfall_debt（入账同 UoW 原子优先扣回）、券对账案件 coupon_reconcile_case（未决案件使券不可用）与显式本地裁决命令 CAS 改当前态 + 受控外部 TAKE 摄取命令、authority_epoch_current 单指针与原子发布 + quarantine + readiness 一致性检查（删除环境变量作为切换动作的表述）、唯一事实统一（payment_attempt.payment_snapshot_json）+ D1-0 逐端点迁移表与历史未完成回填 / manual_review、"历史待处理为 0" 作为切换证据、FP 唯一 DAG 定稿（FP-1+FP-3a→FP-4A→CT-1→FP-4B1→FP-3b→FP-4B2→FP-2）与 CT-1 拆受控白名单门 / 开放控制面、(provider, unique_id) 事件身份与账户级余额投影版本）
- related_docs:
  - `docs/specs/2026-08-12-member-loyalty-storedvalue-plan.md`
  - `docs/specs/2026-08-12-member-loyalty-followup-wechat-pay.md`
  - `docs/specs/2026-08-12-member-loyalty-followup-local-authority.md`
  - `docs/harness-engineering/adr/0006-sqlite-inbox-outbox-exception.md`
  - `docs/harness-engineering/adr/0007-local-authority-cutover.md`
  - `app/service/order/application.py`、`app/service/order/payment_runtime.py`、`app/service/order/payment_notification.py`
  - `app/service/stored_value/payment.py`、`app/service/points/payment.py`、`app/service/coupon/payment.py`
  - `app/repository/coupon_inventory_repo.py`、`app/repository/inbox_repo.py`、`app/repository/base.py`

## Context

2026-08-14 完整复核确认三项结构性风险（均基于代码实测）：

1. **Unit of Work 名存实亡**：`CouponInventoryRepo.insert`（`app/repository/coupon_inventory_repo.py:70`）与 `PointsLedgerRepo.insert`（`app/repository/points_ledger_repo.py:44`）在流程中途自行 `commit()`，把外层复合事务连根提交。`payment_runtime.py` / `payment_notification.py` / `stored_value/payment.py` 的"扣余额 → 置 paid → 核销券 → 发分"复合事务，其真实提交点内嵌于声明边界（`order/application.py:141/166` 的 `transaction()`）。后果：**券已核销、订单已置 paid 之后，若发分失败，无法整体回滚**——订单/余额/券固化、分未发。base.py 的 SAVEPOINT 机制退化，`coupon/payment.py:143/169` 用字符串匹配捕获 savepoint 释放异常后吞错。
2. **券唯一索引同时承担生命周期去重与当前态约束**：`idx_coupon_inventory_dedup (coupon_id, status, mobile)`（v024:66）不含 source。`TAKE → CONSUME → BACK → CONSUME` 的第二次核销在结构上被禁止（当前靠"仅 TAKE 可消费"状态检查使 BACK 成为终态）；同时 local 权威下 webhook/import 券行占用键位导致本地状态无法写入——这是 FP-2 切换唯一键冲突的根因。
3. **退款聚合缺失**：无 `refund` 服务、无退款持久表；微信适配器无关单/退款/退款查询；券 BACK 写入链路（`CouponService.refund_coupon`）无任何订单流程调用；跨"微信款 → 积分 → 余额 → 券"的补偿顺序未实现。现有补偿仅覆盖未支付关单（余额 → 积分 → 清券快照）。
4. **文档与代码金额公式不一致**：代码 `compute_remain_fen(total, coupon, balance, points)`（`payment_state.py:118`）已含券；主计划与 FP-3 文档公式漏 `coupon_fen`。

本 ADR 处于 **proposed**：B1.6 已修正 5 项高风险合同缺口并记录项目负责人裁决；作为设计裁决，代码实施（D1 实施阶段）须在项目负责人批准后单独落地。

## Decision

### D1-A：单一 Unit of Work 与账务 Outbox

**第一批账务仓储清单（零 commit/rollback 契约）**：以下仓储的**写路径**只执行 SQL，**不自行 commit / rollback**（移除内部 `commit()`），并纳入"零 `commit/rollback` 检查"与故障注入回滚测试。清单以**真实类名 + 方法级范围**表述（B1.6 复核修正：删除不存在的 `StoredValueRepo`，补齐真实储值链路的 `RechargeRepo` / `BalanceLedgerRepo` / `OrderEventRepo`）：

| 仓储（真实类名） | 纳入零 commit 契约的写方法 | 现状 |
|---|---|---|
| `CouponInventoryRepo` | `insert` / `consume` / `refund` | `insert` 现于 `coupon_inventory_repo.py:70` 自 commit |
| `PointsLedgerRepo` | `insert` | `insert` 现于 `points_ledger_repo.py:44` 自 commit |
| `MemberBalanceRepo` | `upsert_identity` / `credit_points` / `deduct_points_if_sufficient` / `credit_stored_value` / `deduct_stored_value_if_sufficient` | `upsert_identity` 现于 `member_balance_repo.py:119` 自 commit |
| `RechargeRepo` | `create` / `mark_paid_if_unpaid` / `cancel_if_unpaid` / `expire_if_unpaid` | 储值充值单写路径；`create` 现于 `recharge_repo.py:35` 自 commit |
| `BalanceLedgerRepo` | `insert` | 储值流水；当前 `INSERT OR IGNORE` 无自 commit，纳入契约防回归 |
| `OrderRepo` | 订单状态写 / `order.payment` 展示缓存刷新（**B3.1 口径：唯一账务事实在 `payment_attempt.payment_snapshot_json`，payment.json 仅引用 + 展示缓存**） | 订单写路径 |
| `OrderEventRepo` | `add` | 订单状态事件写路径（真实储值链路一环） |
| `AccountingOutboxRepo`（新建） | `enqueue` / `claim` / `complete` / `fail` | B1.7 新增，写 `accounting_outbox`，纳入故障注入矩阵 |
| `CouponEventRepo`（新建） | `append`（含条件投影 CAS 同一 UoW） | B1.7 新增，写 `coupon_events` + `coupon_current_state` |
| `RefundRepo`（新建） | `create_refund` / `quota_reserve`（单条条件更新）/ `leg_quota_reserve`（B3 逐腿条件更新）/ `quota_release` / `operation_update` | B1.7 + B1.8 + B2.0 + B3 新增，写 `refund_aggregate` + `refund_operation` + `payment_refund_quota` + `payment_refund_leg_quota`（B2.0 泛化主体，B3 逐腿额度） |
| `PaymentAttemptRepo`（新建） | `create` / `settle_if_valid` / `invalidate` / `leg_reserve` / `leg_consume` / `leg_release` | B1.8 + B1.9 + B3 新增，写 `payment_attempt`（`subject_type + subject_id`，`provider=wechat` 时 `merchant_order_no` 唯一不可复用，`payment_snapshot_json` 不可变）+ `payment_attempt_leg`（B3 资金腿） |
| `LedgerOperationRepo`（新建） | `reserve` / `complete` | B2.0 新增，写 `ledger_operation`（`operation_key UNIQUE` 幂等占位，资金腿原子合同） |
| `AccountHoldRepo`（新建） | `reserve`（条件预占，校验可用余额）/ `consume` / `release` / `expire` | B3 + B3.1 新增，写 `account_hold`（余额 / 积分持久预占，**绑定不可变账户主键 `member_balance_id`**，微信等待期间防重复使用） |
| `PaymentProviderEventRepo`（新建） | `enqueue`（唯一事件键幂等）/ `claim`（租约条件更新）/ `mark_processed` / `mark_failed` | B3 + B3.1 新增，写 `payment_provider_event`（支付提供方事件 inbox，先持久化再 ACK，**租约 CAS 协议**） |
| `CouponObservationRepo`（新建） | `append`（写观察）/ `append_case`（写对账案件） | B3 + B3.1 新增，写 `coupon_observation`（外部券观察，不改变当前态）+ `coupon_reconcile_case`（对账案件） |
| `CouponVerdictRepo`（新建） | `verdict`（本地裁决命令，投影 CAS 改当前态） | B3.1 新增，写 `coupon_current_state`（`RECONCILE_HOLD / RECONCILE_VERDICT` 与受控外部 TAKE 摄取命令） |
| `RefundShortfallDebtRepo`（新建） | `create`（缺口债务行）/ `repay_if_sufficient`（入账同 UoW 原子优先扣回）/ `close` | B3.1 新增，写 `refund_shortfall_debt`（余额 / 积分短缺持久债务，替代仅冻结标志位） |

**`InboxRepo` 不纳入零 commit 契约**：`InboxRepo` 是 ADR 0006 定义的入站持久队列，其 `enqueue` / `claim` / `mark_processed` / `mark_failed` 的自提交是**队列自身持久化语义**，不属于账务 UoW 写入；账务 UoW 只把「外部动作投递」写入独立 `accounting_outbox`。禁止把通用入站队列方法笼统纳入"零 commit"规则——账务 UoW 写入与队列自身持久化必须区分。

- 事务边界唯一属主为**应用服务（UoW 属主）**：`OrderApplicationService`、`StoredValueOrderPaymentService` 等通过统一事务上下文声明边界，退出时统一提交，异常时整体回滚。
- 跨仓储复合操作（订单置 paid + 扣余额 + 核销券 + 发分 + 写流水 + 写 `accounting_outbox`）必须处于同一事务；任一后续步骤失败，整体回滚（无 paid、无扣款、无核销、无发分、无外发）。
- **资金腿原子合同（B2.0）**：新增 `ledger_operation` 表（`operation_key UNIQUE` 幂等占位、`subject_type / subject_id`、`operation_type`、`status`、时间戳）。同一 UoW 内顺序：`ledger_operation` 幂等占位（`INSERT OR IGNORE`，重复 `operation_key` 直接短路）→ 余额 / 积分变更（条件更新）→ 流水写入 → `accounting_outbox` 投递占位 → 提交。**禁止"先改余额后写流水"或"先查后改"的非原子模式**；`operation_key` 覆盖重复通知 / 重试 / 并发结算。
- **资金腿与预占持久化（B3，评审问题 1）**：`payment_attempt` 仅有快照不足以阻止微信等待期间重复使用余额 / 积分，须补两张持久表——
  - **`payment_attempt_leg`**：每次支付尝试的资金腿构成。字段：`leg_id`、`payment_attempt_id`（FK）、`asset_type`（`wechat / balance / points / coupon`）、`amount_fen`（积分腿换算分存储）、`status`（`reserved / consumed / released`）、`created_at / updated_at`。**每腿金额必须与 `payment_snapshot_json` 对应资产分摊一致（写入时校验）**，是资金腿的持久账务事实；`UNIQUE(payment_attempt_id, asset_type)`。
  - **`account_hold`**：余额 / 积分的持久预占。字段：`hold_key`（幂等键 `UNIQUE`，如 `hold:<payment_attempt_id>:<asset_type>:<member_balance_id>`）、`subject_type / subject_id`、**`member_balance_id`（不可变账户主键，B3.1：绑定具体余额 / 积分账户行——同一会员多账户 / 多卡时 hold 必须锚定到具体账户行，杜绝跨账户串占；`hold_key` 含账户维度）**、`payment_attempt_id`、`asset_type`（`balance / points`）、`amount_fen`、`status`（`active / consumed / released / expired`）、`expires_at`、`created_at / updated_at`。
  - **预占时序（B3 定稿 + B3.1 账户维度）**：首次不可逆承诺点（创建微信预下单 / 余额支付结算开始）**必须**先持久化预占——余额 / 积分插入 `account_hold`（`active`，绑定 `member_balance_id`），券沿用 `coupon_current_state RESERVED`（不重复建 hold），微信腿无本地预占；随后才允许进入微信等待（`prepay_requested / prepay_unknown / prepay_ready`）或结算。**可用余额公式（唯一口径，按账户行计算）**：`available_balance_fen = member_balance.stored_value_fen - SUM(account_hold.amount_fen WHERE account_hold.member_balance_id = member_balance.id AND asset_type='balance' AND status='active')`；积分同构 `available_points = member_balance.points - SUM(account_hold.amount_fen WHERE account_hold.member_balance_id = member_balance.id AND asset_type='points' AND status='active')`。**新预占以条件更新校验（扣除该账户行全部 active holds 后仍充足才允许）**，微信等待期间余额 / 积分不得被其他尝试重复预占。
  - **消费与释放**：结算成功 → `account_hold` 置 `consumed` + 余额 / 积分 ledger 扣减 + 券 `CONSUME` 同一 UoW（`ledger_operation` 幂等覆盖）；取消 / 超时 / 关单成功 → 置 `released`；**仅 `failed / expired / cancelled` 终态允许释放，`settling` 与微信等待期禁止释放**（防止微信已扣款而本地已释放的双花）；**`cancelled`（B3.1：关单成功终态，见支付尝试状态机）允许释放；`manual_review`（B3.1：查询至上限转人工处置态）期间保持占用，人工裁决（确认已支付 → 消费 / 确认未支付 → 释放）后才动作，禁止自动释放**。
- **`order.payment` 降级为引用 / 展示缓存（B3，评审问题 1）**：`order.payment`（payment.json）**不再承载账务裁决事实**，仅保留 `payment_attempt_id` 引用与展示快照；结算、分摊、预占、退款额度初始化、回调校验一律以 `payment_attempt.payment_snapshot_json` 为**唯一账务事实**；二者不一致时以不可变快照为准并提示对账。D1 实施时订单结算写入 `payment_attempt` 后同步刷新 `order.payment` 缓存，禁止反向以缓存驱动账务（**逐端点迁移与历史未完成处置合同见 D1-0**）。
- **统一支付应用服务（B3，评审问题 1）**：订单（微信差额 / 余额 / mock）、充值（微信 / mock 确认）、余额支付、mock 结算**必须经统一支付应用服务入口**进入 `payment_attempt → payment_attempt_leg + account_hold → ledger_operation → accounting_outbox` 模型，禁止各路径自行拼接状态与账务写入；入口按 `subject_type + subject_id` 分派，回调 / 查询统一按 `payment_attempt` 状态机推进（订单 / 充值 / 余额 / mock 同契约）。
- 迁移顺序：先为清单内仓储的写方法加"零 commit/rollback"静态检查 + 故障注入测试（红），再逐仓储移除自提交（绿），最后删除 `coupon/payment.py` 与 `points/payment.py` 中对 "savepoint" 错误字符串匹配的吞错逻辑。
- 外部调用使用**独立 `accounting_outbox` 表**（非 `inbox_events`）：`inbox_events` 按 ADR 0006 只承载入站事件，且其 `enqueue` 自提交、不能与账务 UoW 原子写入。微信关单/退款等外部动作统一写 `accounting_outbox`，与订单/余额/券/积分**同事务写入**，由独立投递 worker 消费并重试。**删除"outbox 或 Saga"的未决表述**——本决策即定稿为 `accounting_outbox` + 幂等投递。

**`accounting_outbox` 最小 schema（B1.6 + B1.7 定稿）**：

| 字段 | 说明 |
|---|---|
| `id` | 主键 AUTOINCREMENT |
| `operation_key` | **幂等键**，`UNIQUE NOT NULL`（如 `wechat:refund:<refund_no>` / `wechat:close:<order_no>`） |
| `operation_type` | 操作类型枚举（B1.7 + B3）：`wechat_close_order` / `wechat_refund` / `wechat_refund_query` / **`wechat_order_query`（B3：查询预下单 / 支付状态，`operation_key = wechat:order_query:<merchant_order_no>:<payment_attempt_id>`）** / 预留扩展 |
| `provider` | 外部提供方（`wechat` / 预留 `youzan`） |
| `provider_request_no` / `provider_response_no` | 微信侧请求号 / 响应关联号（B1.7）：映射微信商户幂等字段——下单 `out_trade_no`、退款 `out_refund_no` 与 `refund_no` 一一对应；响应关联用于异步结果回填 |
| `aggregate_type` / `aggregate_id` | 聚合引用（`order` / `refund` / `recharge` 等类型与实例 ID） |
| `payload_json` | 投递负载（外部 API 参数原文） |
| `version` | 负载 schema 版本（int），变更必须升版 |
| `status` | `pending / processing / succeeded / failed / dead_letter` |
| `attempt_count` | 重试计数（int，默认 0） |
| `max_attempts` | 最大重试上限（B1.7，默认 5，超出转 `dead_letter`） |
| `lease_token` | **租约令牌（B1.7 fencing）**：claim 时写入新 token；complete / fail 必须以 token 匹配的条件更新完成，过期 worker 无法覆盖 |
| `lease_until` | 投递 worker 租约（`processing` 时占用，重启可重领） |
| `next_attempt_at` | 下次重试时间（退避调度） |
| `last_error` | 最近失败原因（截断存储） |
| `depends_on_operation_key` | 顺序 / 依赖字段（B1.7）：依赖前置投递成功后才可 claim（按需声明，如关单依赖预下单就绪；**退款查询不得引用退款投递行作依赖，见 B3 独立调度规则**） |
| `dead_lettered_at` / `dead_letter_reason` | 死信时间与原因 |
| `reconcile_status` | 对账状态（`pending / matched / mismatch / manual_review`） |
| `created_at` / `updated_at` | 时间戳 |

**投递 fencing 规则（B1.7）**：`claim` 为条件更新——`UPDATE ... SET status='processing', lease_token=<new_token>, lease_until=now+<lease> WHERE id=? AND operation_key=? AND (status='pending' OR (status='processing' AND lease_until<=now) OR (status='failed' AND next_attempt_at<=now)) AND (depends_on_operation_key IS NULL OR NOT EXISTS(未完成前置))`；`complete` / `fail` 同样以 `WHERE id=? AND lease_token=?` 条件更新并校验 token，行数不为 1 即视为陈旧 worker 写入并拒绝覆盖。

**支付提供方事件 inbox 与回调协议（B3，评审问题 2）**：

- 新增 `payment_provider_event` 表：`event_key UNIQUE`（微信支付通知以 `wechat:notify:<transaction_id>:<merchant_order_no>` 为键；`transaction_id` 缺失时以通知 resource `ciphertext` 的 sha256 前缀为键）、`provider`、`event_type`（`pay_notify / refund_notify / query_result`）、`payload_json`（原始通知与解密结果）、`status`（`received / processing / processed / failed / dead_letter`）、`attempt_count`、`last_error`、**`lease_token` / `lease_until`（B3.1 租约：claim 写入，`mark_processed / mark_failed` 以 token 条件更新）、`next_retry_at`、`max_attempts`（默认 5，超出转 `dead_letter`）、`dead_lettered_at` / `dead_letter_reason`**、`created_at / updated_at`。
- **先持久化再 ACK（B3 定稿 + B3.1 ACK 语义定稿，消除"同键直接 ACK"与"仅成功后 ACK"的冲突）**：收到支付通知 → 校验请求头与签名 → **先按唯一 `event_key` 持久化事件（幂等）** → 处理（按 `payment_attempt` 状态机 CAS）→ **仅处理成功（事件 `processed`）后才返回 HTTP 200 ACK**；处理失败返回 5xx，由微信按通知重试。**ACK 语义分情形固定**：① 首次到达且处理成功（`processed`）→ 200；② 同 `event_key` 重复到达且事件已 `processed` → **直接 200 幂等 ACK**（不重复结算）；③ 重复 / 并发到达而事件处于 `received / processing`（如落库后处理中、并发双投、落库后进程崩溃未处理完）→ **不得 ACK**——等待当前处理完成，或租约过期（`lease_until <= now`）后重领重新处理，或返回 5xx 由微信重试；④ 事件 `failed` 且未达 `max_attempts` → 返回 5xx 重试；⑤ `dead_letter` → 返回 5xx 并升级人工。**绝不在事件未达 `processed` 时返回 200**（防止"已持久化未处理"被 ACK 而永不结算）。**`settling` 期间不得提前 ACK 成功**（见支付尝试状态机）。
- **事件租约 CAS 协议（B3.1）**：`claim` 为条件更新——`received → processing`（写 `lease_token` / `lease_until`），或 `processing` 且 `lease_until <= now` 可重领，或 `failed` 且 `next_retry_at <= now` 可重试；`mark_processed / mark_failed` 以 `WHERE event_key=? AND lease_token=?` 条件更新，**行数不为 1 即视为陈旧 worker 写入并拒绝覆盖**。**落库后崩溃**：事件停留在 `received / processing`，租约过期后由调度重领重新处理，处理幂等由 `payment_attempt` 状态机 CAS 兜底——不丢事件、不重复结算。**同 `event_key` 不同 `payload`（冲突负载）**：拒绝结算，进入对账，不覆盖原事件。
- **回调固定校验清单（B3，在 B1.9"只校验微信实际字段"基础上补全）**：支付 / 退款通知必须固定校验——① **验签上下文**：`Wechatpay-Signature`（RSA-SHA256）、`Wechatpay-Timestamp`、`Wechatpay-Nonce`、`Wechatpay-Serial`（按证书序列号取平台证书 / 公钥验签，验签失败拒绝并记录）；② `mchid` = 商户号；③ `appid` = 小程序 AppID；④ **交易成功状态**：`trade_state = SUCCESS`（退款通知为退款成功状态，非成功状态不进账）；⑤ 金额 `amount.total` 与币种 `fee_type = CNY`；⑥ 商户单号 `out_trade_no`；⑦ 交易号 `transaction_id`。任一不匹配 → 拒绝结算并进入对账，不产生资产副作用。
- **`prepay_unknown` 持久调度与状态 CAS（B3 + B3.1 固定映射）**：`prepay_unknown`（预下单响应未知 / `prepay_id` 丢失）由独立调度任务按退避经 outbox 发起 `wechat_order_query`（与关单互斥：同一尝试至多一个在途动作，均以 `lease_token` 条件更新）。**查询结果固定映射（B3.1 定稿；查询只能得知支付状态，不能恢复丢失的 JSAPI `prepay_id`）**——① `trade_state=SUCCESS`（已支付）→ CAS 转 **`settling`**（按该尝试 `payment_snapshot_json` 结算；回调迟到时以查询确认的支付事实结算，仍以 `UNIQUE(provider, provider_transaction_id)` 防串单）；② `NOTPAY`（未支付）→ **先发起关单确认（`wechat_close_order`）成功后再置 `cancelled / expired` 终态并释放预占**，**不得查询到未支付就直接终态释放**（关单前保持占用）；③ `CLOSED / REVOKED / PAYERROR`（已关闭 / 失败）→ 直接终态并释放预占；④ 查询失败 / 状态未知 → **保持占用**（不释放、不终态），退避继续查询，至上限转 **`manual_review`**（保持占用，人工处置）；⑤ **只有已持久化可用的预支付会话（`prepay_id` 已落库且未过期）才进入 `prepay_ready`**——`prepay_unknown` 不产生 `prepay_ready`（无法向用户提供可调起会话），用户侧重试必须作废原尝试并发起新尝试（新 `merchant_order_no`，原单走查询-关单路径处置）。**支付会话（`prepay_id` / 支付参数）属运行时状态，禁止写回不可变 `payment_snapshot_json`**（可存于 `payment_attempt` 可变列）。查询动作与关单动作全部经 outbox 调度，禁止绕过 outbox 的裸调用。

### D1-0：唯一事实迁移合同（B3.1，评审问题 8）

- **唯一事实唯一口径（B3.1 定稿）**：`payment_attempt.payment_snapshot_json` 是**唯一**账务裁决事实；`order.payment`（payment.json）仅保存引用与展示缓存。资产矩阵「策略固化时点」「资产策略写入快照」与 FP-3「按 `payment.balanceFen` 原路退款」等旧口径一律以 `payment_attempt.payment_snapshot_json` 的资产分摊为准（相应文档已一并修正）。**禁止任何路径以 `payment.json` 驱动账务裁决**（结算 / 分摊 / 预占 / 退款额度初始化 / 回调校验）。
- **逐端点迁移表（D1 实施验收，旧写路径禁用或转发）**：

  | 端点 / 写路径 | 现状 | 迁移动作（D1） | 迁移证据 |
  |---|---|---|---|
  | `payment_runtime.prepare_payment`（同步返回 JSAPI 会话） | 写 `order.payment`，`prepay_id` 不持久化 | 转发统一支付应用服务；`payment_attempt` 持久化预下单状态与会话（可变列），会话不写回快照 | `payment_attempt` 行存在且状态正确 |
  | `payment_runtime.confirm_mock_payment` | mock 置 paid + 核销 / 发分 | 经统一入口走 `payment_attempt → legs/holds → ledger_operation → outbox` | UoW 故障注入测试通过 |
  | `payment_notification.handle_wechat_payment_notify` | 回调处理 | 先持久化 `payment_provider_event` 再处理（租约 CAS，仅 `processed` 后 200） | 先持久化再 ACK 测试 |
  | `stored_value/payment.py` 两条路径 | 余额 / 组合支付 | 统一入口 + `payment_attempt` 主体分派 | 同 UoW 结算测试 |
  | `recharges.py` mock-pay / cancel | 充值写路径 | 充值尝试入 `payment_attempt`（`subject_type=recharge`，`provider=wechat` 时 `merchant_order_no` 唯一） | 回调归属测试 |
  | `_user.py` legacy header 分支 | 兼容头 | 已裁决永久关闭（CT-1，B3） | legacy 任意值 401 测试 |
  | 其他绕过统一入口的写路径 | — | 逐项核对并禁用 / 转发 | 覆盖表核对记录入验收 |

- **历史未完成处置合同（B3.1）**：D1 切换前盘点历史 `order.payment` 与充值单——`status ∈ {unpaid, partial}` 且存在未归属回调 / 未知预下单的单据：能按快照回填 `payment_attempt` 的**回填**（快照重建，`snapshot_hash` 校验一致），无法可靠回填的**标记 `manual_review`**（保持占用，人工处置，禁止自动结算）。
- **切换证据（B3.1，"历史待处理为 0"）**：无未归属回调、无未处置 `prepay_unknown`、无未查询 `dispatch_unknown` / `accepted` 退款、无未决 `manual_review` 缺口——**历史待处理为 0** 作为从旧模型切换到 `payment_attempt` 唯一事实的放行证据之一（进 D1 / FP-4B2 Go/No-Go 清单）。

### D1-B：券生命周期事件与当前态投影分离（唯一模型）

**唯一模型（B1.6 + B1.7 定稿，不再保留多个实施候选）**：

- 事件表 `coupon_events`（v025+ 迁移）：每行一条券生命周期事件。**事件标识拆分（B1.7 + B1.8）**：
  - `transition_key`：**不含来源**的逻辑转换幂等键，`UNIQUE`，用于业务转换去重。**必须包含事件类型与支付尝试（B1.8 修正，否则 `RESERVE` 与同订单 `CONSUME` 生成同一键被自身幂等拒绝）**：
    `transition_key = sha256(coupon_id + ":" + mobile + ":" + transition_type + ":" + business_ref + ":" + cycle_no + ":" + payment_attempt_id)`
    其中 `transition_type ∈ {TAKE, RESERVE, RELEASE, CONSUME, BACK, EXPIRE, RECONCILE_HOLD, RECONCILE_VERDICT}`（**RECONCILE_* 为 B3.1 本地对账裁决命令事件**，见 D1-B 对账案件协议）；`business_ref` 为 `order:<order_no>`（预占 / 核销）、`refund:<refund_no>`（退回）、`take:<外部事件 ID>`（领取）、`import:<导入批次 ID>`（导入）、`legacy:<coupon_inventory.id>`（历史行迁移）；`payment_attempt_id` 仅订单路径事件携带（非订单路径为空串）；**`RESERVE` 成功时分配 `cycle_no`，同 `payment_attempt_id` 的 `CONSUME` 复用该预占周期**（同一转换键语义：预占 + 核销各自独立一行）。
  - `ingest_source`：摄取来源字段（`import` / `webhook` / `order` / `local` / `legacy`），**不参与 `transition_key`**。
  - `origin_event_id`：**上游稳定事件 ID**（B1.8 + B1.9：必须可跨 import / webhook 通道对齐，如由有赞业务事件确定的 `msg_id` / 事件主键；**导入批次行 ID 不能默认等同 webhook `msg_id`**，仅当二者可证实指向同一上游事件时才允许对齐）；同一外部事件双通道到达以 `origin_event_id` 幂等去重，唯一范围为 **`UNIQUE(coupon_id, mobile, origin_event_id)`**（仅可证实对齐的写入该键，无法对齐的置空并隔离待对账）；**无法确认来源的事件隔离待对账，禁止伪造外部事件 ID**。事件新旧判定按 B1.9 事件版本合同（`event_version` / `ordering_kind` / `payload_hash`），禁止以本地到达序承担因果。
- **券生命周期状态迁移表（B1.7 加入 `RESERVED` 预占，唯一允许的迁移，禁止跨状态跳转）**：

  | from | event | to | 前置条件 |
  |---|---|---|---|
  | （初始） | TAKE | TAKE | 领取 / 导入 / legacy 迁移 |
  | TAKE | RESERVE | RESERVED | apply-coupon 预占（**仅本地订单命令**），绑定 `payment_attempt_id`；写事件与投影同一 UoW |
  | RESERVED | RELEASE | TAKE | 未支付取消 / 超时释放预占（**仅本地订单命令**，不写 BACK） |
  | RESERVED | CONSUME | CONSUME | 支付成功（**仅本地订单命令**），校验 `payment_attempt_id` 与预占匹配 |
  | CONSUME | BACK | TAKE | 全单退款（**仅本地订单命令**），券退回可再用 |
  | TAKE / RESERVED / CONSUME | RECONCILE_HOLD | reconcile_hold | 对账未决（**B3.1 仅本地裁决命令**，由 `coupon_reconcile_case` 未决案件触发），不可用、不可核销 |
  | reconcile_hold | RECONCILE_VERDICT | TAKE / RESERVED / CONSUME（按裁决） | 对账裁决（**B3.1 仅本地裁决命令**），携带 `case_id` / 版本校验 / 审计，按裁决 CAS 恢复或改态 |
  | TAKE / RESERVED / CONSUME | EXPIRE | EXPIRE | 到期投影清理 |

- **券事件三类分离（B2.0）**：`coupon_events` 事件分三类——
  1. **本地订单命令**（`RESERVE / RELEASE / CONSUME / BACK`，`ingest_source=order`）：唯一允许驱动状态迁移的事件，走投影 CAS 与 `cycle_no` 分配；
  2. **外部观察**（`ingest_source=webhook / import` 的 `CONSUME / BACK / TAKE`）：**只写 `coupon_observation` 与对账，不改变 `coupon_current_state`**（B3 定稿 + B3.1 案件协议）——外部 `CONSUME / BACK` 与本地命令冲突时进入对账队列（含负责人与处置），外部 `TAKE` 仅作领取登记；**切换窗口内新券经受控外部 TAKE 摄取命令进入本地可用当前态（B3.1，见下对账案件协议）**；
  3. **迁移**（`ingest_source=legacy`）：基线迁移事件，`business_ref=legacy:<coupon_inventory.id>`。
  因此**取消 `TAKE → CONSUME` 直核**：订单路径核销必须经 `RESERVE`，不存在"两个订单同时读 TAKE 并各自创建支付会话"的合法路径。
- **券观察与本地当前态拆分（B3 + B3.1 对账案件协议）**：新增 `coupon_observation` 表（外部观察事实）：`observation_id`、`coupon_id / mobile / origin_event_id`、`observed_status`、`provider / event_version / ordering_kind / payload_hash`、`observed_at`、`reconcile_status`（`pending / matched / mismatch / manual_review`）。**B3.1 引入 `coupon_reconcile_case`（对账案件表，可用性覆盖）**：`case_id`、`coupon_id / mobile / origin_event_id`、`case_type`（`unmatched_observation / version_conflict / status_conflict / external_take`）、`status`（`open / verdict_applied / closed`）、`trace_id`（裁决记录关联）、`created_at / updated_at`。规则定稿——① **外部 `CONSUME / BACK / TAKE` 观察只追加 `coupon_observation` 事实与 `coupon_reconcile_case` 案件，绝不直接写 `coupon_current_state`**（观察层不改当前态）；② **未决案件（`open`）使券不可用**：可用券列表与核销判定 = 当前态可用 AND 无该券未决案件，案件未决即不可用、不可核销；③ **只有显式本地对账裁决命令（`RECONCILE_HOLD / RECONCILE_VERDICT`，`ingest_source=local`）才能 CAS 修改 `coupon_current_state`**——案件处置（自动规则或人工）后由裁决命令将投影置 `reconcile_hold`（未决人工处置）或恢复 / 改态（`matched`），命令携带 `case_id`、裁决结果、目标状态、`event_version` 版本校验与审计关联（`trace_id`），投影以 `version + expected_status` 条件更新；④ **受控外部 `TAKE` 摄取命令（B3.1，切换窗口内新券的合法可用路径）**：外部新券 `TAKE` 观察到达（如切换窗口内有赞新发券）→ 追加观察与 `external_take` 案件 → 经受控摄取命令（携带过渡 epoch、`event_version` 版本校验、幂等键 `origin_event_id` / `transition_key`、审计关联）CAS 写入 `coupon_current_state=TAKE`（可用）——避免切换窗口内新券从本地可用列表消失；⑤ 可精确对应本地命令与周期（同 `origin_event_id` 且版本可比）的观察，由确认裁决命令更新投影。**外部观察不改变当前态，本地命令（`RESERVE / CONSUME / BACK` 与 `RECONCILE_*` 裁决 / 摄取）是唯一写入 `coupon_current_state` 的路径**——观察只追加事实与案件、未决案件使券不可用、裁决命令才改当前态，三者由此统一（`reconcile_hold` 由裁决命令写入，不是由观察直接写入，状态迁移表见上）。
- **`legacy` 统一公式（B2.0 修正）**：legacy 迁移行同样遵循统一 `transition_key` 公式——`business_ref = legacy:<coupon_inventory.id>`、`transition_type=TAKE`、`cycle_no=0`、`payment_attempt_id` 空串，`transition_key = sha256(coupon_id + ":" + mobile + ":" + transition_type + ":legacy:<coupon_inventory.id>:0:")`；不再存在"legacy:<id> 直接作为 transition_key"的例外表述。

- **投影版本 / CAS（B1.7）**：`coupon_current_state` 含单调 `version`、`expected_status`；转换采用**条件更新**——追加事件与更新投影**在同一 UoW 内**执行，投影 `UPDATE ... WHERE coupon_id=? AND mobile=? AND version=expected_version AND status=expected_status`，不满足则事务整体回滚（防两个订单同时读 `TAKE` 并各自建支付会话：第二个 `RESERVE` 条件更新失败）。
- **因果顺序规则（B1.7 + B1.9）**：`CONSUME` 事件必须引用同一 `payment_attempt_id` 的 `RESERVE` 事件；`RELEASE` / `CONSUME` / `BACK` 均以投影 `expected_status` 做 CAS。
- **事件版本合同（B1.9）**：事件携带 `provider / event_id / event_version / ordering_kind / payload_hash`；`ordering_kind=monotonic`（供应商保证 `event_version` 单调递增）时以 `event_version` 判定新旧；`ordering_kind=unordered` 或不可比时**不判定新旧**，冲突进入对账队列（含负责人与处置结果）；**禁止以本地 `(occurred_at, id)` 承担因果语义**（仅作同源展示序）。
- **`cycle_no` CAS 原子分配（B1.9）**：`RESERVE` 通过条件更新原子分配周期（基于投影 `version` CAS，未占用才分配并写回），同 `payment_attempt_id` 的 `CONSUME` 复用该周期；并发 `RESERVE` 只有一个成功。
- **跨来源重复事件规则**：同一 `transition_key`（含 `transition_type` + `payment_attempt_id`）幂等拒绝（`UNIQUE` 兜底）；同一上游事件（同 `origin_event_id`，须可跨通道证实对齐）重复摄取拒绝，跨来源不再互相占用唯一键位。
- 当前态投影 `coupon_current_state`（条件投影）：按 `coupon_id + mobile` 聚合最新事件行，投影出 `status / order_no / refund_no / payment_attempt_id / valid_from / valid_until / value_fen / version` 等当前态字段，供可用券列表、核销判定与 local 权威读取。
- **历史行迁移（B1.7 + B3 口径统一）**：现有 `coupon_inventory` 行按**统一 `transition_key` 公式**迁移（`business_ref = legacy:<coupon_inventory.id>`、`transition_type=TAKE`、`cycle_no=0`、`payment_attempt_id` 空串，见上文 `legacy` 统一公式；**不再存在"legacy:<id> 直接作为 transition_key"的旧键表述**；无法确认外部来源事件 ID，不作伪造）；迁移完成后旧 `idx_coupon_inventory_dedup (coupon_id, status, mobile)`（v024:66）标为**"第一阶段现状，禁止用于新实现"**并最终删除。
- local 权威下 webhook/import 券以事件形式入 `coupon_events`，不再被 `source IN ('order','local')` 过滤丢券；FP-2 切换唯一键冲突与 FP-3 券 BACK 二次核销限制一并解除。
- 该设计**必须前置于 FP-3 退款与 FP-2 权威切换**（二者执行前设计门禁）。

### D1-C：持久退款聚合（Saga 最终一致 + 人工复核）

**政策裁决（B1.6 + B1.7，项目负责人书面裁决）**：支持**全额与部分退款**，基准为**净额退款**（B1.7 裁决）：

- **退款基准确认（净额）**：券折扣**只影响可退商品金额，不生成货币型退款操作**。可退货币基准 = `refundable_fen = cash_fen + balance_fen + points_fen = total_fen - coupon_fen`（客户实付净额）。`refund_fen` 在（微信款 / 余额 / 积分）三者间按实付占比分摊（最大余数法保证分摊之和等于 `refund_fen`）；**券仅在全额退款时 BACK 退回，部分退款不退回券**——部分退款金额不包含券面额，客户不获得超出实付的补偿。**（B3.1 差分分摊定稿）**多笔部分退款**禁止各笔独立按最大余数法分摊并各自预占**（每笔余数可能都落到同一腿，导致逐腿额度被错误拒绝）；改为**确定性差分分摊**——先按固定规则（**腿排序固定为 `wechat → balance → points`**）计算**含本笔在内的累计退款总额**的分摊 `allocation(累计后)`，本笔各腿分摊 = `allocation(累计后) − allocation(累计前)`（差分），保证逐腿预占单调确定，且任一笔跨腿超额整笔拒绝。
- **商品行级折扣分摊**：`discounted_line_fen = line_fen - coupon_line_share`，其中 `coupon_line_share` 按商品行金额占可退商品总额的比例分摊券面额（整数分钱最大余数法）；行级退款金额以 `discounted_line_fen` 为上限，券份额不随行级退款退回。
- **毛额 / 净额口径**：毛额 `gross_fen = total_fen`（含券），净额 `net_fen = total_fen - coupon_fen`。退款一律按净额口径结算；毛额仅用于对账展示与商品行级核对。

**事务语义（B1.6 复核修正，消除"支付/退款失败可整体回滚"的歧义）**：

- **本地账务 UoW 原子**：订单状态、余额、积分流水、券事件、`accounting_outbox` 投递在同一本地事务内，任一步失败整体回滚（无 paid、无扣款、无核销、无发分、无外发）。
- **跨微信退款采用 Saga 最终一致**：微信退款成功是外部不可逆动作。**微信已退款成功、本地补偿失败时不能整体回滚**，只能进入 `manual_review` 并等待对账 / 人工补录。

- 新增 `refund_aggregate`：`refund_no`、**`subject_type + subject_id`（B2.0 泛化：`order` / `recharge` 等，替代单一 `order_id`）**、**`payment_attempt_id`（`NOT NULL`，绑定被退款支付尝试，与额度表键一致）**、`policy`（`full` / `partial`）、**不可变支付快照**（`payment_snapshot_json`：total/coupon/balance/points/remain + 行级折扣分摊 + 券周期 + 币种 + 策略版本）、各资产分摊（微信款 / 余额 / 积分）、总状态集 `requested / processing / succeeded / failed / manual_review`、对账状态。
- **退款额度表泛化（B2.0）**：`order_refund_quota` 更名为 **`payment_refund_quota`**，按 `UNIQUE(subject_type, subject_id, payment_attempt_id)` 一行额度（字段：`refundable_fen` / `reserved_fen` / `refunded_fen` / `version`），**在支付成功结算的同一 UoW 内初始化额度行**（`refundable_fen` 取自该尝试的不可变 `payment_snapshot_json` 净额）。任何新 `refund_aggregate` 创建 / 更新先对额度行做**单条条件更新预占**：`UPDATE payment_refund_quota SET reserved_fen = reserved_fen + ? , version = version + 1 WHERE subject_type=? AND subject_id=? AND payment_attempt_id=? AND version=? AND refunded_fen + reserved_fen + ? <= refundable_fen`——不满足即整笔拒绝（并发部分退款不可能超额预占）。
- **逐腿退款额度（B3，评审问题 3）**：新增 **`payment_refund_leg_quota`**（`UNIQUE(subject_type, subject_id, payment_attempt_id, asset_type)`，字段：`refundable_fen / reserved_fen / refunded_fen / version`），在结算同一 UoW 内与总额度行一并初始化——每腿 `refundable_fen` 取自 `payment_snapshot_json` 对应资产分摊（微信款 / 余额 / 积分各一腿）。任何 `refund_aggregate` 创建 / 更新**先对逐腿额度行做单条条件更新预占**：`UPDATE payment_refund_leg_quota SET reserved_fen = reserved_fen + ?, version = version + 1 WHERE subject_type=? AND subject_id=? AND payment_attempt_id=? AND asset_type=? AND version=? AND refunded_fen + reserved_fen + ? <= refundable_fen`；总额度行与逐腿行同一 UoW 更新，**任一不满足即整笔拒绝**。**每腿累计退款（`refunded_fen + reserved_fen`）不得超过该腿 `refundable_fen`**——多笔部分退款按最大余数法各自分摊时，不可能累计多退某一资金腿。**（B3.1）**逐腿预占金额一律按**差分分摊**（`allocation(累计后) − allocation(累计前)`，腿排序固定 `wechat → balance → points`）的结果执行——多笔部分退款不会因每笔最大余数落同一腿而误拒；每笔预占仍以 `version + refunded_fen + reserved_fen + ? <= refundable_fen` 单条条件更新原子执行。
- **充值退款政策（B2.0 裁决 + B3 边界定稿）**：充值真实支付后退款，余额 `stored_value_fen` 已被消费（不足抵扣退款额）时——**默认进入 `manual_review`，禁止先向微信发起自动外部退款**（外部退款动作不得早于余额缺口处置）；缺口记录为 **`manual_review` + 持久短缺债务**（**B3.1：新增 `refund_shortfall_debt` 表**：`debt_key`（如 `refund:<refund_no>:balance`）、`asset_type`（`balance / points`）、`amount_fen`、`status`（`pending / repaying / closed`）、`version`、`created_at / updated_at`——替代仅 `refund_operation.balance_shortfall_frozen` 标志位，**债务行随缺口产生在同一 UoW 写入**），不产生负余额；**后续余额入账（充值 / 其他入账）时在同一 UoW 内原子优先扣回债务**（`UPDATE refund_shortfall_debt SET ... WHERE debt_key=? AND status IN ('pending','repaying') AND 入账额 >= 缺口额` 条件扣减，扣完置 `closed`；入账与补扣要么同时成功要么整体回滚）；对账任务对超过最大未决时长的缺口升级人工。余额足够时——**先冻结再分派外部退款**：分派前以 `account_hold` 预占冻结（`hold_key = refund:<refund_no>:balance`，`asset_type=balance`），冻结成功后才允许对应 `wechat_refund` 动作进入 outbox；冻结失败即拒绝分派进入 `manual_review`。退款前余额是否可扣由单条条件更新裁决（`stored_value_fen - SUM(active holds) >= 缺口`）。
- **微信退款分派状态机（B1.9 + B3 三状态拆分）**：`refund_operation` 拆分三个独立状态维度，禁止混为一谈——
  - **`dispatch_status`**（微信侧受理结果）：`not_dispatched / dispatching / dispatch_unknown / accepted`——入队前 `not_dispatched`、投递中 `dispatching`、投递后结果未知 `dispatch_unknown`、微信受理 `accepted`；
  - **`provider_refund_status`**（退款查询确认结果）：`unknown / confirmed_refunded / confirmed_not_refunded`——**确认态枚举统一，删除 `confirmed` 单值表述**（B3 修正：此前状态枚举写作 `confirmed`，实际使用 `confirmed_refunded / confirmed_not_refunded`，此处定稿为后者）；
  - **`accounting_outbox.status`**（outbox 投递状态，`pending / processing / succeeded / failed / dead_letter`，与分派状态分开建模）。
- **退款状态与 outbox 投递状态分离（B2.0 + B3）**：`refund_operation` 的分派状态与 `accounting_outbox` 的投递状态**分开建模**；**`dispatch_unknown` 必须能独立调度退款查询**（查询以独立 `operation_key = wechat:refund_query:<refund_no>:<payment_attempt_id>` 写入 outbox，或由对账任务直接调用查询适配器），**不设置"退款投递成功"依赖**（`depends_on_operation_key` 不得引用退款投递行）——投递响应丢失时查询仍可发起，避免"已受理但响应丢失"的退款无法查询；**全部经 outbox 调度，回写一律以 `version + lease_token` 条件更新，陈旧 worker（token 不匹配）拒绝覆盖**。**`accepted` / `dispatch_unknown` 后通知丢失的持续查询（B3.1）**：`refund_operation` 增 `next_query_at / query_generation` 字段——按退避以 `next_query_at` 调度持续 `wechat_refund_query`，直至 `confirmed_refunded / confirmed_not_refunded` 或升级人工；`query_generation` 单调递增，查询结果回写以 `version + lease_token + query_generation` 条件更新，陈旧查询结果（代数低于当前）拒绝覆盖。
- **预占释放规则（B1.8 + B1.9 + B3 明确）**：**仅 `provider_refund_status = confirmed_not_refunded`（退款查询确认未退款）才允许释放预占**（`reserved -= x`）；`confirmed_refunded` 转实退（`reserved -= x; refunded += x`）；`dispatch_unknown` / `accepted`（请求超时、微信是否已受理未知）**必须保持占用**并进入退款查询或人工复核，**禁止因请求超时释放预占后再次发起退款**。
- 新增 `refund_operation`（子操作）：每步补偿一个资产——`operation_key` 幂等键（B1.7：**所有账本操作一律按 `refund_no` 幂等**，即 `refund_operation.operation_key = "refund:<refund_no>:<asset>"`，不再以 `order_id` 为键，支持同一订单多笔部分退款；**（B3.1 积分键拆分）**退回已用积分与收回奖励积分分别以 `refund:<refund_no>:points_used` / `refund:<refund_no>:points_awarded` 为幂等键，**分别维护累计额度**（各自 ≤ 对应已用 / 已发量），不再共用单一 `refund:<refund_no>:points` 键——否则同 `refund_no` 的第二个积分操作会被幂等键拒绝）、资产类型、金额 / 积分单位、状态 `pending / success / failed / manual_review`、重试计数、人工复核条件、微信退款号 / 异步结果关联。
- **积分收回不足（B1.7 裁决 + B3.1 债务化）**：按 `refund_no` 收回 `pointsAwarded` 时积分余额不足，缺口记录为 **`manual_review` + 持久短缺债务**（`refund_shortfall_debt`，`asset_type=points`，B3.1：与余额缺口同一张债务表、同一原子优先扣回协议，替代 `points_shortfall_frozen` 标志位），不产生负余额；后续积分到账在同一 UoW 内原子优先补扣（条件扣减，扣完 `closed`），全部补齐后方可关闭该 `refund_operation`。对账任务须对 `manual_review` 超过最大未决时长的缺口升级人工。
- **人工复核进入条件（明确）**：任一 `refund_operation` 重试达上限仍失败，或「微信退款步骤已 `success`、后续本地补偿步骤 `failed`」（即微信已退、本地未补偿，必须可观测、可人工补录），或积分收回不足触发冻结。
- **补录幂等键**：人工补录以 `refund_operation.operation_key` 为幂等键，重复补录不产生双倍补偿。
- **最大未决时长**：`refund_aggregate` 处于 `processing` / `manual_review` 超过上限时长（实施前由项目负责人在裁决记录中固定数值，默认 72 小时）后，对账任务必须上报 `mismatch` 并升级人工。
- **对账关闭条件**：`refund_aggregate.status = succeeded` 且全部 `refund_operation` 为 `success`，且微信对账查询累计退款金额与本地 `refund_aggregate` 分摊金额一致（净额口径），方可关闭对账。
- 微信适配器补齐：关单、退款、退款查询、异步退款结果通知。
- 券 `BACK` 作为全单退款 `refund_operation` 的一步接入；`compute_remain_fen(total, coupon, balance, points)` 为唯一金额公式。
- 补偿顺序：微信款 → 积分（退回 pointsUsed / 收回 pointsAwarded）→ 余额 → 券（核销回退）；任一步失败，微信退款成功后本地补偿失败时进入 `manual_review` 并由对账任务发现。

### D1-D：入站围栏与 authority epoch（B3，评审问题 6）

> 背景：`inbox_events.id` 只是到达水位，事件可能在权威切换前入队、切换后才被消费；`InboxRepo`（`app/repository/inbox_repo.py`）当前无 claim token，陈旧 worker / dead-letter / 重启接管均无围栏。本节约束 FP-2 D2 协议并扩展 ADR 0006 队列语义。

- **`authority_epoch` 表（不可变资产权威矩阵）**：`epoch_id`（主键）、`points_mode`（`youzan / local`）、`coupon_mode`（`youzan / local`）、`identity_mode`（`youzan / local`）、`activated_at`、`trace_id`（切换裁决记录）、`created_at`。**一条 epoch 记录积分 / 券 / 身份各资产的权威模式矩阵（不可变，禁止更新已激活行）**；切换只新增行，可表达"积分已切、券未切"的混合权威态；`activated_at` 与裁决记录 `trace_id` 一一对应。**（B3.1 单指针）**：新增单行指针表 **`authority_epoch_current`**（`epoch_id` / `activated_at` / `updated_at` / `trace_id`，单行，或等价单调 epoch 编号）——入队端与消费端只读当前指针判定当前权威；**入队与读取当前 epoch 必须在同一写事务**（`enqueue` 同事务读指针并写事件，与 B3 入队同事务围栏一致）。
- **入队同事务围栏（B3）**：`InboxRepo.enqueue` 在**同一事务内读取 active `authority_epoch` 并写入事件**——`inbox_events` 增列 `authority_epoch_id`（入队时写入当时的 active epoch）与 `claim_token`（claim 时写入）；禁止"入队后再补读 epoch"或"先读后插非同一事务"。
- **`queue_control` 表（切换围栏控制）**：`queue_name`（`UNIQUE`）、`paused`、`paused_at`、`paused_by`、`resume_at`、`reason`、`trace_id`。切换流程：① 置 `paused`（暂停 claim）；② 排空 / 接管水位前 `received / processing / failed` 事件（处理完或标记接管）；③ 插入新 `authority_epoch` 并**同一事务**更新 `authority_epoch_current` 指针（**B3.1 原子发布**：发布即单事务，禁止先插行后指针漂移的中间态）；④ 解除 `paused` 恢复消费。水位前事件按旧 epoch 语义处理，水位后事件按新 epoch 处理。**（B3.1 quarantine）**：切换前水位前事件必须**全部完成**，或进入 **quarantine 隔离区**——被接管 / 放弃执行的事件标记 `quarantined`（`inbox_events.quarantine_status`），**不可执行业务写入**，仅记录 / 审计并由人工或对账处置；旧 epoch 事件未完成且未 quarantine 时禁止切换。
- **`claim_token` 条件完成（B3）**：`claim` 写入 `claim_token` 并随结果返回；`mark_processed / mark_failed` 以 `WHERE id=? AND claim_token=?` 条件更新，**行数不为 1 即视为陈旧 worker 写入并拒绝覆盖**；dead-letter 与重启接管（lease 过期重领）同样以 token 校验，防止旧 worker 回写新接管后的事件。
- **消费按事件 epoch 路由（B2.0 + B3）**：消费者**不得读取进程级环境变量**判定权威，一律按事件 `authority_epoch_id` 路由到对应处理语义；进程级开关仅作部署默认值。**（B3.1 readiness 一致性检查）**：进程启动时校验——部署配置默认值（如 `POINTS_AUTHORITY` 配置项）与持久化当前 epoch 指针不一致即 `/ready` 返回 `false`（fail-closed），**禁止以配置覆盖持久 epoch 作为切换动作**；配置仅作部署默认值，不承担切换语义。
- **演练矩阵（B3 验收 + B3.1 增补，隔离环境）**：切换中入队（水位前 / 后事件分别携带旧 / 新 epoch）；陈旧 worker 完成被拒（token 不匹配）；dead-letter 后接管；进程重启恢复（lease 过期重领后 token 校验通过）；混合 epoch（积分已切、券未切）路由正确；企微队列混入被过滤。**（B3.1）**：切换指针原子发布（发布前后无中间态）；旧 epoch 事件 quarantine 后切换；配置默认值与持久 epoch 不一致 → readiness 失败；`query_generation` 陈旧查询回写拒绝。

## Alternatives

- 维持现状（仓储自 commit + savepoint 吞错）：改动最小，但"券已核销订单已 paid 而积分失败"不可回滚，资金一致性无保证，否决。
- 引入分布式事务框架：当前单机 SQLite、单 worker，无跨服务事务需求；用本地 UoW + outbox/补偿即可满足，避免引入分布式事务基础设施，否决。
- 仅改文案/文档：不解决结构性回滚与券生命周期问题，否决。

## Consequences

- 所有支付 / 退款路径的事务边界收敛到 UoW 属主：**本地账务 UoW 原子回滚；跨微信退款按 Saga 最终一致，微信已退本地未补偿进入人工复核**，不再声称"可整体回滚"。
- 券生命周期支持 `RESERVED` 预占与多周期核销退回（投影 CAS 防双花）；local 切换唯一键冲突消除（需 v025+ 迁移与基线迁移）。
- 退款具备持久状态、幂等（`refund_no`）、`payment_refund_quota` 单条条件更新预占（并发不可超额）、净额口径、对账与人工复核能力；积分 / 充值余额收回不足为 manual_review + 持久短缺债务（**B3.1：`refund_shortfall_debt`，替代冻结标志位**）。
- outbox 具备 fencing（lease_token 条件更新）、依赖顺序、最大重试与微信商户幂等映射。
- 支付尝试持久化（`payment_attempt` + `out_trade_no` 不可复用），迟到通知无法按新快照结算旧尝试。
- **（B3）资金腿持久化**：`payment_attempt_leg` + `account_hold` 提供余额 / 积分持久预占与可用余额公式，微信等待期间不可重复预占；`order.payment` 降级为引用 / 展示缓存，`payment_attempt.payment_snapshot_json` 为唯一账务事实；统一支付应用服务收敛订单 / 充值 / 余额 / mock 结算入口。
- **（B3）回调与查询**：支付提供方事件 inbox 先持久化再 ACK；回调固定校验验签 / mchid / appid / 成功状态 / 金额 / 币种 / 商户单号 / 交易号；`prepay_unknown` 经 outbox 持久调度 `wechat_order_query` 并 CAS 推进。
- **（B3）退款**：`payment_refund_leg_quota` 逐腿条件更新预占，每腿累计退款不可超额；充值余额不足默认 `manual_review` 且禁止先自动外部退款，余额足够先冻结再分派；退款三状态（`dispatch_status` / `provider_refund_status` / outbox status）拆分，确认态统一为 `confirmed_refunded / confirmed_not_refunded`。
- **（B3）入站围栏**：`authority_epoch` 不可变资产矩阵 + 入队同事务 + `queue_control` + `claim_token` 条件完成，陈旧 worker / dead-letter / 重启接管有围栏。
- **（B3）券观察**：`coupon_observation` 与 `coupon_current_state` 拆分，外部观察不改变当前态，无法精确匹配时置 `reconcile_hold`。
- **（B3.1）账户与租约**：`account_hold` 绑定不可变账户主键 `member_balance_id`（可用额按账户行计算）；支付状态机补 `cancelled / manual_review`——`manual_review` 未解除前禁止同主体新支付尝试；`payment_provider_event` 租约 CAS（`received/processing/processed/failed/dead_letter`），**仅 `processed` 后同键重复通知才 200**，落库后崩溃可重领不丢不重。
- **（B3.1）查询与分摊**：`prepay_unknown` 固定映射（已支付→`settling` / 未支付先关单再终态释放 / 未知保持占用退避查询或转 `manual_review`；仅已持久化可用会话进 `prepay_ready`，禁止支付会话写回不可变快照）；逐腿退款确定性差分分摊（`allocation(累计后) − allocation(累计前)`，固定腿排序）；`next_query_at / query_generation` 持续查询；积分幂等键按动作拆分（`points_used` / `points_awarded`）；余额 / 积分短缺以持久 `refund_shortfall_debt` 债务表同 UoW 原子优先扣回。
- **（B3.1）券对账与 epoch**：`coupon_reconcile_case` 对账案件（未决案件使券不可用），仅显式本地裁决命令（`RECONCILE_HOLD / RECONCILE_VERDICT`）CAS 改当前态，受控外部 TAKE 摄取命令；`authority_epoch_current` 单指针与原子发布、quarantine、readiness 一致性检查（删除环境变量作为切换动作的表述）。
- **（B3.1）唯一事实与迁移**：`payment_attempt.payment_snapshot_json` 唯一事实；D1-0 逐端点迁移表与历史未完成回填 / `manual_review`；"历史待处理为 0" 作为切换证据；FP 唯一 DAG 定稿与 CT-1 拆门（受控白名单门 / 开放控制面）、`(provider, unique_id)` 事件身份与账户级投影版本。
- 涉及核心迁移（券表、退款表、`accounting_outbox`、`payment_attempt`、`payment_attempt_leg`、`account_hold`、`payment_provider_event`、`coupon_observation`、`authority_epoch`、`queue_control`、`inbox_events` 增列）与全量回归；故障注入测试纳入门禁。
- 实施期间建议配合方案 C（服务端关闭储值/积分/券写操作）作为临时边界，降低风险；积分门禁已裁决为关闭 Platform 积分写操作，券门禁已裁决为关闭旧入口券能力 + 正式版关闭券抵扣。

## Verification（实施阶段验收）

- 账务仓储清单（含 B1.7/B1.8/B2.0/B3/B3.1 新增 `AccountingOutboxRepo` / `CouponEventRepo` / `RefundRepo` / `PaymentAttemptRepo` / `LedgerOperationRepo` / `AccountHoldRepo` / `PaymentProviderEventRepo` / `CouponObservationRepo` / `CouponVerdictRepo` / `RefundShortfallDebtRepo`）"零 commit/rollback"静态检查通过（红绿迁移）。
- 故障注入集成测试：订单 / 余额 / 券 / 积分 / outbox 任一步注入失败，断言全部状态回滚（无 paid、无扣款、无核销、无发分、无外发）。
- 券命令模型测试：`TAKE → RESERVE → CONSUME → BACK`（含 `RESERVED → RELEASE`）全周期；**`RESERVE` 与同订单 `CONSUME` 的 `transition_key` 不相同（含 `transition_type` + `payment_attempt_id`，无键冲突回归测试）**；两个订单并发 `RESERVE` 同一 TAKE 券只有一个成功（投影 CAS + `cycle_no` CAS 原子分配）；同一外部事件 import/webhook 双通道仅一条 `transition_key`；`origin_event_id` 唯一范围 `UNIQUE(coupon_id, mobile, origin_event_id)` 且可跨通道对齐，导入批次行 ID 不等同 webhook `msg_id`，无法对齐的隔离对账；事件新旧判定按 `event_version / ordering_kind / payload_hash` 合同（monotonic 才判新旧，unordered 冲突进对账队列）；legacy 行迁移不伪造外部事件 ID。
- 投影重建测试：新事件处理后旧快照覆盖，投影重建恢复（关联 FP-1 I1 重建器）；按事件版本合同胜出、`UNIQUE(batch_id, asset, inbox_event_id)` 物化幂等、投影 / 物化 / checkpoint 同 UoW。
- 退款聚合测试：`refund_aggregate + refund_operation` 幂等（`refund_no` 键）、**`refund_aggregate.payment_attempt_id NOT NULL` 且与额度行键一致**、**`payment_refund_quota` 单条条件更新并发预占（两笔并发部分退款不可能超额；充值主体与订单主体同契约）**、**`payment_refund_leg_quota` 逐腿条件更新（多笔部分退款逐腿累计不超 `refundable_fen`，任一笔预占跨腿超额整笔拒绝）**、**微信退款分派状态机（仅 `provider_refund_status = confirmed_not_refunded` 释放预占；`dispatch_unknown` / `accepted` 保持占用进入查询或人工复核，禁止超时释放后重发退款；退款查询独立于 outbox 投递调度且以 version + lease_token 回写，陈旧 worker 拒绝覆盖）**、额度行在结算同一 UoW 初始化、净额口径分摊、积分收回不足的 manual_review + 持久短缺债务、充值余额不足的 manual_review + 持久短缺债务（**禁止先自动外部退款**；余额足够先 `account_hold` 冻结再分派）、微信已退本地未补偿的人工复核路径、进程重启恢复、对账一致。
- outbox fencing 测试：claim 租约 token 条件更新、陈旧 worker token 不匹配完成被拒绝、依赖顺序、`max_attempts` 转 dead_letter、微信 `out_trade_no` / `out_refund_no` 幂等映射。
- payment_attempt 测试：`subject_type + subject_id` 主体模型（订单 / 充值 / 余额 / mock 结算分派同 UoW）；完整状态机 `draft → prepay_requested → prepay_unknown/prepay_ready → settling → succeeded/failed/expired/cancelled`（**B3.1：`cancelled` 为关单成功终态；`prepay_unknown` 退避查询至上限转 `manual_review` 处置态，`manual_review` 未解除前禁止同主体新尝试**；含 `settling` 重启恢复、仅 `succeeded` 同交易号幂等 ACK）；`UNIQUE(provider, provider_transaction_id)` 防串单；回调只校验微信实际字段（金额 / 币种 / 商户单号 / 交易号），不依赖内部快照比较；快照写入后不可修改；`ledger_operation` 幂等占位 + 余额变更 + 流水 + outbox 同一 UoW（无"先改后写"非原子模式）；超时尝试置终态后迟到通知按新快照结算被拒绝（进入对账）。
- **（B3）资金腿与预占测试**：`payment_attempt_leg` 每腿金额与 `payment_snapshot_json` 分摊一致（写入校验）；`account_hold` 条件预占（可用余额 = 账本 - active holds，微信等待期间并发新尝试预占被拒）；结算成功 hold 消费与 ledger 扣减同一 UoW、取消 / 超时释放、`settling` 与等待期禁止释放；`order.payment` 与不可变快照不一致时以快照为准并提示对账；订单 / 充值 / 余额 / mock 均经统一支付应用服务入口（绕过即测试失败）。
- **（B3）回调与查询测试**：`payment_provider_event` 唯一 `event_key` 幂等（重复通知不重复结算）；**先持久化再 ACK**（持久化失败不返回 200、处理失败返回 5xx 由微信重试）；回调固定校验验签上下文 / mchid / appid / `trade_state=SUCCESS` / 金额 / 币种 / 商户单号 / 交易号（逐项负向用例）；`prepay_unknown` 经 outbox 发起 `wechat_order_query` 并 CAS 推进（与关单互斥，lease_token 防陈旧回写）。
- **（B3）入站围栏测试**：`authority_epoch` 不可变矩阵（新 epoch 表达"积分已切、券未切"）；enqueue 同事务写 active epoch；`queue_control` 暂停 → 排空 / 接管 → 切纪元 → 恢复演练；`claim_token` 条件完成（陈旧 worker 拒绝、dead-letter 接管、重启恢复）；混合 epoch 路由正确。
- **（B3）券观察测试**：外部 `CONSUME / BACK / TAKE` 只写 `coupon_observation` 不改变当前态；无法精确匹配时 `coupon_current_state` 置 `reconcile_hold`（不可用、不可核销）；可精确匹配（同 `origin_event_id` 且版本可比）才更新投影。
- **（B3.1）账户绑定与状态机测试**：`account_hold` 绑定 `member_balance_id`（跨账户不串占、可用额按账户行计算）；支付状态机含 `cancelled / manual_review`——`manual_review` 未解除前同主体新支付尝试被拒（唯一活跃尝试集合含 `manual_review`）；`manual_review` 期间 holds 保持占用，裁决后才释放 / 消费；`cancelled` 终态允许释放。
- **（B3.1）事件租约测试**：`payment_provider_event` 租约 CAS（`received → processing` 写 token、`lease_until` 过期重领、`failed` 按 `next_retry_at` 重试、达 `max_attempts` 转 `dead_letter`）；**落库后崩溃**（事件停留 `received / processing`，租约重领重处理，不丢不重）；**重复通知**（`processed` 后重复 → 200 幂等；`received / processing` 重复 / 并发 → 不 ACK，重领或 5xx）；**冲突 payload**（同 `event_key` 不同 payload → 拒绝结算进对账，不覆盖原事件）。
- **（B3.1）prepay_unknown 映射测试**：查询 `SUCCESS` → `settling`（按快照结算）；`NOTPAY` → 先关单确认再终态释放（关单前保持占用）；`CLOSED / REVOKED / PAYERROR` → 终态释放；未知 → 保持占用退避查询至上限转 `manual_review`；`prepay_unknown` 不产生 `prepay_ready`；支付会话（`prepay_id`）不写回不可变快照（`snapshot_hash` 不变断言）。
- **（B3.1）退款分摊与债务测试**：多笔部分退款按差分分摊（`allocation(after) − allocation(before)`，固定腿排序）逐腿预占不误拒、不超退；`accepted` 后通知丢失按 `next_query_at` 持续查询、`query_generation` 陈旧结果拒绝回写；积分退回 `points_used` 与收回 `points_awarded` 幂等键独立（同 `refund_no` 两操作均成功）；余额 / 积分短缺产生 `refund_shortfall_debt` 债务行（同一 UoW 写入），后续入账同一 UoW 原子优先扣回（入账成功债务未扣 = 整体回滚）。
- **（B3.1）券对账案件测试**：外部观察只追加事实与 `coupon_reconcile_case` 案件；未决案件使券不可用 / 不可核销；仅本地裁决命令（`RECONCILE_HOLD / RECONCILE_VERDICT`，含 `case_id` / `event_version` 校验 / `trace_id` 审计）CAS 改当前态；受控外部 TAKE 摄取命令在切换窗口内使新券可用（含过渡 epoch、幂等键 `origin_event_id` / `transition_key`）。
- **（B3.1）epoch 单指针测试**：`authority_epoch_current` 单行指针；入队同事务读指针写事件；插入 `authority_epoch` 行与更新指针同一事务原子发布（无中间态）；旧 epoch 事件完成或 quarantine 后才可切换，quarantine 事件不可执行业务写入；配置默认值与持久 epoch 不一致 → `/ready=false`。
- **（B3.1）唯一事实与迁移测试**：逐端点迁移表核对（旧写路径禁用 / 转发）；历史未完成订单 / 充值单回填（`snapshot_hash` 校验）或 `manual_review`；"历史待处理为 0" 断言（无未归属回调 / 未处置 `prepay_unknown` / 未查询退款 / 未决 `manual_review`）。
- `compute_remain_fen` 四资产组合支付与净额退款金额测试。
- 全量回归 + `ruff` + `check_project --skip-tests` 门禁通过。
