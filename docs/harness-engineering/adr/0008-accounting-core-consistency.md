# ADR 0008：账务核心一致性（Unit of Work / 券事件-投影 / 持久退款聚合）

- status: proposed
- date: 2026-08-14
- trace_id: `20260814-member-loyalty-accounting-contract`
- decision_owner: project owner（决策主体 / 唯一批准人）
- technical_advisor: AI (Codex)（仅技术建议，不构成批准）
- revised_at: 2026-08-14（B1.6 合同完成包：补齐真实 UoW 清单与 outbox schema、定稿券事件合同、明确退款 Saga 语义并记录项目负责人三项裁决；B1.7 合同收口：券命令模型 / RESERVED 预占 / 投影 CAS、净额退款与退款预占、outbox fencing、新账务仓储入零 commit 契约）
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
| `OrderRepo` | 订单状态写 / `payment.json` 快照写 | 订单写路径 |
| `OrderEventRepo` | `add` | 订单状态事件写路径（真实储值链路一环） |
| `AccountingOutboxRepo`（新建） | `enqueue` / `claim` / `complete` / `fail` | B1.7 新增，写 `accounting_outbox`，纳入故障注入矩阵 |
| `CouponEventRepo`（新建） | `append`（含条件投影 CAS 同一 UoW） | B1.7 新增，写 `coupon_events` + `coupon_current_state` |
| `RefundRepo`（新建） | `create_refund` / `update_quota` / `operation_update` | B1.7 新增，写 `refund_aggregate` + `refund_operation` |

**`InboxRepo` 不纳入零 commit 契约**：`InboxRepo` 是 ADR 0006 定义的入站持久队列，其 `enqueue` / `claim` / `mark_processed` / `mark_failed` 的自提交是**队列自身持久化语义**，不属于账务 UoW 写入；账务 UoW 只把「外部动作投递」写入独立 `accounting_outbox`。禁止把通用入站队列方法笼统纳入"零 commit"规则——账务 UoW 写入与队列自身持久化必须区分。

- 事务边界唯一属主为**应用服务（UoW 属主）**：`OrderApplicationService`、`StoredValueOrderPaymentService` 等通过统一事务上下文声明边界，退出时统一提交，异常时整体回滚。
- 跨仓储复合操作（订单置 paid + 扣余额 + 核销券 + 发分 + 写流水 + 写 `accounting_outbox`）必须处于同一事务；任一后续步骤失败，整体回滚（无 paid、无扣款、无核销、无发分、无外发）。
- 迁移顺序：先为清单内仓储的写方法加"零 commit/rollback"静态检查 + 故障注入测试（红），再逐仓储移除自提交（绿），最后删除 `coupon/payment.py` 与 `points/payment.py` 中对 "savepoint" 错误字符串匹配的吞错逻辑。
- 外部调用使用**独立 `accounting_outbox` 表**（非 `inbox_events`）：`inbox_events` 按 ADR 0006 只承载入站事件，且其 `enqueue` 自提交、不能与账务 UoW 原子写入。微信关单/退款等外部动作统一写 `accounting_outbox`，与订单/余额/券/积分**同事务写入**，由独立投递 worker 消费并重试。**删除"outbox 或 Saga"的未决表述**——本决策即定稿为 `accounting_outbox` + 幂等投递。

**`accounting_outbox` 最小 schema（B1.6 + B1.7 定稿）**：

| 字段 | 说明 |
|---|---|
| `id` | 主键 AUTOINCREMENT |
| `operation_key` | **幂等键**，`UNIQUE NOT NULL`（如 `wechat:refund:<refund_no>` / `wechat:close:<order_no>`） |
| `operation_type` | 操作类型枚举（B1.7）：`wechat_close_order` / `wechat_refund` / `wechat_refund_query` / 预留扩展 |
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
| `depends_on_operation_key` | 顺序 / 依赖字段（B1.7）：依赖前置投递成功后才可 claim（如退款查询依赖退款投递） |
| `dead_lettered_at` / `dead_letter_reason` | 死信时间与原因 |
| `reconcile_status` | 对账状态（`pending / matched / mismatch / manual_review`） |
| `created_at` / `updated_at` | 时间戳 |

**投递 fencing 规则（B1.7）**：`claim` 为条件更新——`UPDATE ... SET status='processing', lease_token=<new_token>, lease_until=now+<lease> WHERE id=? AND operation_key=? AND (status='pending' OR (status='processing' AND lease_until<=now) OR (status='failed' AND next_attempt_at<=now)) AND (depends_on_operation_key IS NULL OR NOT EXISTS(未完成前置))`；`complete` / `fail` 同样以 `WHERE id=? AND lease_token=?` 条件更新并校验 token，行数不为 1 即视为陈旧 worker 写入并拒绝覆盖。

### D1-B：券生命周期事件与当前态投影分离（唯一模型）

**唯一模型（B1.6 + B1.7 定稿，不再保留多个实施候选）**：

- 事件表 `coupon_events`（v025+ 迁移）：每行一条券生命周期事件。**事件标识拆分（B1.7）**：
  - `transition_key`：**不含来源**的逻辑转换幂等键，`UNIQUE`，用于业务转换去重：`transition_key = sha256(coupon_id + ":" + mobile + ":" + business_ref + ":" + cycle_no)`；`business_ref` 为 `order:<order_no>`（核销 / 预占）、`refund:<refund_no>`（退回）、`take:<外部事件 ID>`（领取）、`import:<导入批次 ID>`（导入）、`legacy:<coupon_inventory.id>`（历史行迁移）；`cycle_no` 为同券同业务引用周期序号（int，从 0 起）。
  - `ingest_source`：摄取来源字段（`import` / `webhook` / `order` / `local` / `legacy`），**不参与 `transition_key`**。
  - `origin_event_id`：外部原始事件 ID（如有赞 `msg_id` / 导入批次行 ID）。**同一外部事件经 import 与 webhook 两条通道到达时，以 `origin_event_id` 幂等去重**，不产生两条业务事件；无法确认来源事件的记录隔离待对账，**禁止伪造外部事件 ID**。
- **券生命周期状态迁移表（B1.7 加入 `RESERVED` 预占，唯一允许的迁移，禁止跨状态跳转）**：

  | from | event | to | 前置条件 |
  |---|---|---|---|
  | （初始） | TAKE | TAKE | 领取 / 导入 / legacy 迁移 |
  | TAKE | RESERVE | RESERVED | apply-coupon 预占，绑定 `payment_attempt_id`；写事件与投影同一 UoW |
  | RESERVED | RELEASE | TAKE | 未支付取消 / 超时释放预占（不写 BACK） |
  | RESERVED | CONSUME | CONSUME | 支付成功，校验 `payment_attempt_id` 与预占匹配 |
  | TAKE | CONSUME | CONSUME | 兼容非订单直核场景（可配置关闭） |
  | CONSUME | BACK | TAKE | 全单退款，券退回可再用 |
  | TAKE / RESERVED / CONSUME | EXPIRE | EXPIRE | 到期投影清理 |

- **投影版本 / CAS（B1.7）**：`coupon_current_state` 含单调 `version`、`expected_status`；转换采用**条件更新**——追加事件与更新投影**在同一 UoW 内**执行，投影 `UPDATE ... WHERE coupon_id=? AND mobile=? AND version=expected_version AND status=expected_status`，不满足则事务整体回滚（防两个订单同时读 `TAKE` 并各自建支付会话：第二个 `RESERVE` 条件更新失败）。
- **因果顺序规则（B1.7）**：`CONSUME` 事件必须引用同一 `payment_attempt_id` 的 `RESERVE` 事件；`RELEASE` / `CONSUME` / `BACK` 均以投影 `expected_status` 做 CAS，保证因果顺序；来源权重不再参与事件排序（`(occurred_at, id)` 单调，迟到事件追加后重算投影）。
- **跨来源重复事件规则**：同一 `transition_key` 幂等拒绝（`UNIQUE` 兜底）；同一外部事件（同 `origin_event_id`）重复摄取拒绝，跨来源不再互相占用唯一键位。
- 当前态投影 `coupon_current_state`（条件投影）：按 `coupon_id + mobile` 聚合最新事件行，投影出 `status / order_no / refund_no / payment_attempt_id / valid_from / valid_until / value_fen / version` 等当前态字段，供可用券列表、核销判定与 local 权威读取。
- **历史行迁移（B1.7）**：现有 `coupon_inventory` 行迁移为 `transition_key = legacy:<coupon_inventory.id>`（无法确认外部来源事件 ID，不作伪造）；迁移完成后旧 `idx_coupon_inventory_dedup (coupon_id, status, mobile)`（v024:66）标为**"第一阶段现状，禁止用于新实现"**并最终删除。
- local 权威下 webhook/import 券以事件形式入 `coupon_events`，不再被 `source IN ('order','local')` 过滤丢券；FP-2 切换唯一键冲突与 FP-3 券 BACK 二次核销限制一并解除。
- 该设计**必须前置于 FP-3 退款与 FP-2 权威切换**（二者执行前设计门禁）。

### D1-C：持久退款聚合（Saga 最终一致 + 人工复核）

**政策裁决（B1.6 + B1.7，项目负责人书面裁决）**：支持**全额与部分退款**，基准为**净额退款**（B1.7 裁决）：

- **退款基准确认（净额）**：券折扣**只影响可退商品金额，不生成货币型退款操作**。可退货币基准 = `refundable_fen = cash_fen + balance_fen + points_fen = total_fen - coupon_fen`（客户实付净额）。`refund_fen` 在（微信款 / 余额 / 积分）三者间按实付占比分摊（最大余数法保证分摊之和等于 `refund_fen`）；**券仅在全额退款时 BACK 退回，部分退款不退回券**——部分退款金额不包含券面额，客户不获得超出实付的补偿。
- **商品行级折扣分摊**：`discounted_line_fen = line_fen - coupon_line_share`，其中 `coupon_line_share` 按商品行金额占可退商品总额的比例分摊券面额（整数分钱最大余数法）；行级退款金额以 `discounted_line_fen` 为上限，券份额不随行级退款退回。
- **毛额 / 净额口径**：毛额 `gross_fen = total_fen`（含券），净额 `net_fen = total_fen - coupon_fen`。退款一律按净额口径结算；毛额仅用于对账展示与商品行级核对。

**事务语义（B1.6 复核修正，消除"支付/退款失败可整体回滚"的歧义）**：

- **本地账务 UoW 原子**：订单状态、余额、积分流水、券事件、`accounting_outbox` 投递在同一本地事务内，任一步失败整体回滚（无 paid、无扣款、无核销、无发分、无外发）。
- **跨微信退款采用 Saga 最终一致**：微信退款成功是外部不可逆动作。**微信已退款成功、本地补偿失败时不能整体回滚**，只能进入 `manual_review` 并等待对账 / 人工补录。

- 新增 `refund_aggregate`：`refund_no`、`order_id`、`policy`（`full` / `partial`）、**原支付快照**（`payment.json` 原文：total/coupon/balance/points/remain + 行级折扣分摊）、各资产分摊（微信款 / 余额 / 积分）、总状态集 `requested / processing / succeeded / failed / manual_review`、对账状态。
- **订单级退款汇总 / 预占（B1.7）**：`refund_aggregate` 维护 `refunded_fen` 与 `reserved_fen`，任何新 `refund_aggregate` 创建 / 更新必须满足条件约束 **`requested + processing + succeeded <= refundable_fen`**（`refundable_fen` 取自支付快照净额），并随申请即时预占 `reserved_fen`，防止并发部分退款超退。
- 新增 `refund_operation`（子操作）：每步补偿一个资产——`operation_key` 幂等键（B1.7：**所有账本操作一律按 `refund_no` 幂等**，即 `refund_operation.operation_key = "refund:<refund_no>:<asset>"`，不再以 `order_id` 为键，支持同一订单多笔部分退款）、资产类型、金额 / 积分单位、状态 `pending / success / failed / manual_review`、重试计数、人工复核条件、微信退款号 / 异步结果关联。
- **积分收回不足（B1.7 裁决）**：按 `refund_no` 收回 `pointsAwarded` 时积分余额不足，缺口记录为 **`manual_review` + 冻结额度**（`refund_operation.points_shortfall_frozen`），不产生负余额；后续积分到账按冻结额度优先补扣，补扣成功后冲减冻结，全部补齐后方可关闭该 `refund_operation`。对账任务须对 `manual_review` 超过最大未决时长的缺口升级人工。
- **人工复核进入条件（明确）**：任一 `refund_operation` 重试达上限仍失败，或「微信退款步骤已 `success`、后续本地补偿步骤 `failed`」（即微信已退、本地未补偿，必须可观测、可人工补录），或积分收回不足触发冻结。
- **补录幂等键**：人工补录以 `refund_operation.operation_key` 为幂等键，重复补录不产生双倍补偿。
- **最大未决时长**：`refund_aggregate` 处于 `processing` / `manual_review` 超过上限时长（实施前由项目负责人在裁决记录中固定数值，默认 72 小时）后，对账任务必须上报 `mismatch` 并升级人工。
- **对账关闭条件**：`refund_aggregate.status = succeeded` 且全部 `refund_operation` 为 `success`，且微信对账查询累计退款金额与本地 `refund_aggregate` 分摊金额一致（净额口径），方可关闭对账。
- 微信适配器补齐：关单、退款、退款查询、异步退款结果通知。
- 券 `BACK` 作为全单退款 `refund_operation` 的一步接入；`compute_remain_fen(total, coupon, balance, points)` 为唯一金额公式。
- 补偿顺序：微信款 → 积分（退回 pointsUsed / 收回 pointsAwarded）→ 余额 → 券（核销回退）；任一步失败，微信退款成功后本地补偿失败时进入 `manual_review` 并由对账任务发现。

## Alternatives

- 维持现状（仓储自 commit + savepoint 吞错）：改动最小，但"券已核销订单已 paid 而积分失败"不可回滚，资金一致性无保证，否决。
- 引入分布式事务框架：当前单机 SQLite、单 worker，无跨服务事务需求；用本地 UoW + outbox/补偿即可满足，避免引入分布式事务基础设施，否决。
- 仅改文案/文档：不解决结构性回滚与券生命周期问题，否决。

## Consequences

- 所有支付 / 退款路径的事务边界收敛到 UoW 属主：**本地账务 UoW 原子回滚；跨微信退款按 Saga 最终一致，微信已退本地未补偿进入人工复核**，不再声称"可整体回滚"。
- 券生命周期支持 `RESERVED` 预占与多周期核销退回（投影 CAS 防双花）；local 切换唯一键冲突消除（需 v025+ 迁移与基线迁移）。
- 退款具备持久状态、幂等（`refund_no`）、预占约束、净额口径、对账与人工复核能力；积分收回不足为 manual_review + 冻结额度。
- outbox 具备 fencing（lease_token 条件更新）、依赖顺序、最大重试与微信商户幂等映射。
- 涉及核心迁移（券表、退款表、`accounting_outbox`）与全量回归；故障注入测试纳入门禁。
- 实施期间建议配合方案 C（服务端关闭储值/积分/券写操作）作为临时边界，降低风险；积分门禁已裁决为关闭 Platform 积分写操作，券门禁已裁决为关闭旧入口券能力 + 正式版关闭券抵扣。

## Verification（实施阶段验收）

- 账务仓储清单（含 B1.7 新增 `AccountingOutboxRepo` / `CouponEventRepo` / `RefundRepo`）"零 commit/rollback"静态检查通过（红绿迁移）。
- 故障注入集成测试：订单 / 余额 / 券 / 积分 / outbox 任一步注入失败，断言全部状态回滚（无 paid、无扣款、无核销、无发分、无外发）。
- 券命令模型测试：`TAKE → RESERVE → CONSUME → BACK`（含 `RESERVED → RELEASE`）全周期；两个订单并发 `RESERVE` 同一 TAKE 券只有一个成功（投影 CAS）；同一外部事件 import/webhook 双通道仅一条 `transition_key`；`origin_event_id` 幂等去重；legacy 行迁移不伪造外部事件 ID。
- 投影重建测试：新事件处理后旧快照覆盖，投影重建恢复（关联 FP-1 I1 重建器）。
- 退款聚合测试：`refund_aggregate + refund_operation` 幂等（`refund_no` 键）、订单级退款预占约束 `requested+processing+succeeded <= refundable_fen`、净额口径分摊、积分收回不足的 manual_review + 冻结额度、微信已退本地未补偿的人工复核路径、进程重启恢复、对账一致。
- outbox fencing 测试：claim 租约 token 条件更新、陈旧 worker token 不匹配完成被拒绝、依赖顺序、`max_attempts` 转 dead_letter、微信 `out_trade_no` / `out_refund_no` 幂等映射。
- `compute_remain_fen` 四资产组合支付与净额退款金额测试。
- 全量回归 + `ruff` + `check_project --skip-tests` 门禁通过。
