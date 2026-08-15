# ADR 0008：账务核心一致性（Unit of Work / 券事件-投影 / 持久退款聚合）

- status: proposed
- date: 2026-08-14
- trace_id: `20260814-member-loyalty-accounting-contract`
- decision_owner: project owner（决策主体 / 唯一批准人）
- technical_advisor: AI (Codex)（仅技术建议，不构成批准）
- revised_at: 2026-08-15（B1.6 合同完成包：补齐真实 UoW 清单与 outbox schema、定稿券事件合同、明确退款 Saga 语义并记录项目负责人三项裁决；B1.7 合同收口：券命令模型 / RESERVED 预占 / 投影 CAS、净额退款与退款预占、outbox fencing、新账务仓储入零 commit 契约；B1.8 合同修正：transition_key 含类型与支付尝试（修复 RESERVE/CONSUME 键冲突）、order_refund_quota 单条条件更新预占、上游版本合同与重建 UoW 原子性、持久 payment_attempt 表；B1.9 合同收口：事件版本合同与 cycle_no CAS、微信退款分派状态机与预占释放、refund_aggregate 绑定 payment_attempt_id、不可变 payment_snapshot_json；B2.0 合同收口：资金腿 ledger_operation 原子合同、退款主体与额度表泛化（payment_refund_quota）、充值退款政策（manual_review+冻结）、退款查询独立于 outbox、券事件三类分离与 legacy 统一公式）
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
| `RefundRepo`（新建） | `create_refund` / `quota_reserve`（单条条件更新）/ `quota_release` / `operation_update` | B1.7 + B1.8 + B2.0 新增，写 `refund_aggregate` + `refund_operation` + `payment_refund_quota`（B2.0 泛化主体） |
| `PaymentAttemptRepo`（新建） | `create` / `settle_if_valid` / `invalidate` | B1.8 + B1.9 新增，写 `payment_attempt`（`subject_type + subject_id`，`provider=wechat` 时 `merchant_order_no` 唯一不可复用，`payment_snapshot_json` 不可变） |
| `LedgerOperationRepo`（新建） | `reserve` / `complete` | B2.0 新增，写 `ledger_operation`（`operation_key UNIQUE` 幂等占位，资金腿原子合同） |

**`InboxRepo` 不纳入零 commit 契约**：`InboxRepo` 是 ADR 0006 定义的入站持久队列，其 `enqueue` / `claim` / `mark_processed` / `mark_failed` 的自提交是**队列自身持久化语义**，不属于账务 UoW 写入；账务 UoW 只把「外部动作投递」写入独立 `accounting_outbox`。禁止把通用入站队列方法笼统纳入"零 commit"规则——账务 UoW 写入与队列自身持久化必须区分。

- 事务边界唯一属主为**应用服务（UoW 属主）**：`OrderApplicationService`、`StoredValueOrderPaymentService` 等通过统一事务上下文声明边界，退出时统一提交，异常时整体回滚。
- 跨仓储复合操作（订单置 paid + 扣余额 + 核销券 + 发分 + 写流水 + 写 `accounting_outbox`）必须处于同一事务；任一后续步骤失败，整体回滚（无 paid、无扣款、无核销、无发分、无外发）。
- **资金腿原子合同（B2.0）**：新增 `ledger_operation` 表（`operation_key UNIQUE` 幂等占位、`subject_type / subject_id`、`operation_type`、`status`、时间戳）。同一 UoW 内顺序：`ledger_operation` 幂等占位（`INSERT OR IGNORE`，重复 `operation_key` 直接短路）→ 余额 / 积分变更（条件更新）→ 流水写入 → `accounting_outbox` 投递占位 → 提交。**禁止"先改余额后写流水"或"先查后改"的非原子模式**；`operation_key` 覆盖重复通知 / 重试 / 并发结算。
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

- 事件表 `coupon_events`（v025+ 迁移）：每行一条券生命周期事件。**事件标识拆分（B1.7 + B1.8）**：
  - `transition_key`：**不含来源**的逻辑转换幂等键，`UNIQUE`，用于业务转换去重。**必须包含事件类型与支付尝试（B1.8 修正，否则 `RESERVE` 与同订单 `CONSUME` 生成同一键被自身幂等拒绝）**：
    `transition_key = sha256(coupon_id + ":" + mobile + ":" + transition_type + ":" + business_ref + ":" + cycle_no + ":" + payment_attempt_id)`
    其中 `transition_type ∈ {TAKE, RESERVE, RELEASE, CONSUME, BACK, EXPIRE}`；`business_ref` 为 `order:<order_no>`（预占 / 核销）、`refund:<refund_no>`（退回）、`take:<外部事件 ID>`（领取）、`import:<导入批次 ID>`（导入）、`legacy:<coupon_inventory.id>`（历史行迁移）；`payment_attempt_id` 仅订单路径事件携带（非订单路径为空串）；**`RESERVE` 成功时分配 `cycle_no`，同 `payment_attempt_id` 的 `CONSUME` 复用该预占周期**（同一转换键语义：预占 + 核销各自独立一行）。
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
  | TAKE / RESERVED / CONSUME | EXPIRE | EXPIRE | 到期投影清理 |

- **券事件三类分离（B2.0）**：`coupon_events` 事件分三类——
  1. **本地订单命令**（`RESERVE / RELEASE / CONSUME / BACK`，`ingest_source=order`）：唯一允许驱动状态迁移的事件，走投影 CAS 与 `cycle_no` 分配；
  2. **外部观察**（`ingest_source=webhook / import` 的 `CONSUME / BACK / TAKE`）：**只能投影或进入对账，不得直接迁移状态**——外部 `CONSUME / BACK` 与本地命令冲突时进入对账队列（含负责人与处置），外部 `TAKE` 仅作领取登记；
  3. **迁移**（`ingest_source=legacy`）：基线迁移事件，`business_ref=legacy:<coupon_inventory.id>`。
  因此**取消 `TAKE → CONSUME` 直核**：订单路径核销必须经 `RESERVE`，不存在"两个订单同时读 TAKE 并各自创建支付会话"的合法路径。
- **`legacy` 统一公式（B2.0 修正）**：legacy 迁移行同样遵循统一 `transition_key` 公式——`business_ref = legacy:<coupon_inventory.id>`、`transition_type=TAKE`、`cycle_no=0`、`payment_attempt_id` 空串，`transition_key = sha256(coupon_id + ":" + mobile + ":" + transition_type + ":legacy:<coupon_inventory.id>:0:")`；不再存在"legacy:<id> 直接作为 transition_key"的例外表述。

- **投影版本 / CAS（B1.7）**：`coupon_current_state` 含单调 `version`、`expected_status`；转换采用**条件更新**——追加事件与更新投影**在同一 UoW 内**执行，投影 `UPDATE ... WHERE coupon_id=? AND mobile=? AND version=expected_version AND status=expected_status`，不满足则事务整体回滚（防两个订单同时读 `TAKE` 并各自建支付会话：第二个 `RESERVE` 条件更新失败）。
- **因果顺序规则（B1.7 + B1.9）**：`CONSUME` 事件必须引用同一 `payment_attempt_id` 的 `RESERVE` 事件；`RELEASE` / `CONSUME` / `BACK` 均以投影 `expected_status` 做 CAS。
- **事件版本合同（B1.9）**：事件携带 `provider / event_id / event_version / ordering_kind / payload_hash`；`ordering_kind=monotonic`（供应商保证 `event_version` 单调递增）时以 `event_version` 判定新旧；`ordering_kind=unordered` 或不可比时**不判定新旧**，冲突进入对账队列（含负责人与处置结果）；**禁止以本地 `(occurred_at, id)` 承担因果语义**（仅作同源展示序）。
- **`cycle_no` CAS 原子分配（B1.9）**：`RESERVE` 通过条件更新原子分配周期（基于投影 `version` CAS，未占用才分配并写回），同 `payment_attempt_id` 的 `CONSUME` 复用该周期；并发 `RESERVE` 只有一个成功。
- **跨来源重复事件规则**：同一 `transition_key`（含 `transition_type` + `payment_attempt_id`）幂等拒绝（`UNIQUE` 兜底）；同一上游事件（同 `origin_event_id`，须可跨通道证实对齐）重复摄取拒绝，跨来源不再互相占用唯一键位。
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

- 新增 `refund_aggregate`：`refund_no`、**`subject_type + subject_id`（B2.0 泛化：`order` / `recharge` 等，替代单一 `order_id`）**、**`payment_attempt_id`（`NOT NULL`，绑定被退款支付尝试，与额度表键一致）**、`policy`（`full` / `partial`）、**不可变支付快照**（`payment_snapshot_json`：total/coupon/balance/points/remain + 行级折扣分摊 + 券周期 + 币种 + 策略版本）、各资产分摊（微信款 / 余额 / 积分）、总状态集 `requested / processing / succeeded / failed / manual_review`、对账状态。
- **退款额度表泛化（B2.0）**：`order_refund_quota` 更名为 **`payment_refund_quota`**，按 `UNIQUE(subject_type, subject_id, payment_attempt_id)` 一行额度（字段：`refundable_fen` / `reserved_fen` / `refunded_fen` / `version`），**在支付成功结算的同一 UoW 内初始化额度行**（`refundable_fen` 取自该尝试的不可变 `payment_snapshot_json` 净额）。任何新 `refund_aggregate` 创建 / 更新先对额度行做**单条条件更新预占**：`UPDATE payment_refund_quota SET reserved_fen = reserved_fen + ? , version = version + 1 WHERE subject_type=? AND subject_id=? AND payment_attempt_id=? AND version=? AND refunded_fen + reserved_fen + ? <= refundable_fen`——不满足即整笔拒绝（并发部分退款不可能超额预占）。
- **充值退款政策（B2.0 裁决，与 B1.7 积分收回不足同构）**：充值真实支付后退款，余额 `stored_value_fen` 已被消费（不足抵扣退款额）时——缺口记录为 **`manual_review` + 冻结额度**（`refund_operation.balance_shortfall_frozen`），不产生负余额；后续余额到账（充值 / 其他入账）按冻结额度优先补扣，补扣成功后冲减冻结；对账任务对超过最大未决时长的缺口升级人工。退款前余额是否可扣由单条条件更新裁决（`stored_value_fen >= 缺口`）。
- **微信退款分派状态机（B1.9）**：`not_dispatched / dispatching / dispatch_unknown / accepted / confirmed`——入队前 `not_dispatched`、投递中 `dispatching`、投递后结果未知 `dispatch_unknown`、微信受理 `accepted`、退款查询确认 `confirmed_refunded / confirmed_not_refunded`。
- **退款状态与 outbox 投递状态分离（B2.0）**：`refund_operation` 的分派状态与 `accounting_outbox` 的投递状态**分开建模**；**`dispatch_unknown` 必须能独立调度退款查询**（查询以独立 `operation_key` 写入 outbox，或由对账任务直接调用查询适配器），**不能等待"退款投递成功"**——投递响应丢失时查询仍可发起，避免"已受理但响应丢失"的退款无法查询。
- **预占释放规则（B1.8 + B1.9 明确）**：**仅 `confirmed_not_refunded`（退款查询确认未退款）才允许释放预占**（`reserved -= x`）；`confirmed_refunded` 转实退（`reserved -= x; refunded += x`）；`dispatch_unknown` / `accepted`（请求超时、微信是否已受理未知）**必须保持占用**并进入退款查询或人工复核，**禁止因请求超时释放预占后再次发起退款**。
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
- 退款具备持久状态、幂等（`refund_no`）、`payment_refund_quota` 单条条件更新预占（并发不可超额）、净额口径、对账与人工复核能力；积分 / 充值余额收回不足为 manual_review + 冻结额度。
- outbox 具备 fencing（lease_token 条件更新）、依赖顺序、最大重试与微信商户幂等映射。
- 支付尝试持久化（`payment_attempt` + `out_trade_no` 不可复用），迟到通知无法按新快照结算旧尝试。
- 涉及核心迁移（券表、退款表、`accounting_outbox`、`payment_attempt`）与全量回归；故障注入测试纳入门禁。
- 实施期间建议配合方案 C（服务端关闭储值/积分/券写操作）作为临时边界，降低风险；积分门禁已裁决为关闭 Platform 积分写操作，券门禁已裁决为关闭旧入口券能力 + 正式版关闭券抵扣。

## Verification（实施阶段验收）

- 账务仓储清单（含 B1.7/B1.8/B2.0 新增 `AccountingOutboxRepo` / `CouponEventRepo` / `RefundRepo` / `PaymentAttemptRepo` / `LedgerOperationRepo`）"零 commit/rollback"静态检查通过（红绿迁移）。
- 故障注入集成测试：订单 / 余额 / 券 / 积分 / outbox 任一步注入失败，断言全部状态回滚（无 paid、无扣款、无核销、无发分、无外发）。
- 券命令模型测试：`TAKE → RESERVE → CONSUME → BACK`（含 `RESERVED → RELEASE`）全周期；**`RESERVE` 与同订单 `CONSUME` 的 `transition_key` 不相同（含 `transition_type` + `payment_attempt_id`，无键冲突回归测试）**；两个订单并发 `RESERVE` 同一 TAKE 券只有一个成功（投影 CAS + `cycle_no` CAS 原子分配）；同一外部事件 import/webhook 双通道仅一条 `transition_key`；`origin_event_id` 唯一范围 `UNIQUE(coupon_id, mobile, origin_event_id)` 且可跨通道对齐，导入批次行 ID 不等同 webhook `msg_id`，无法对齐的隔离对账；事件新旧判定按 `event_version / ordering_kind / payload_hash` 合同（monotonic 才判新旧，unordered 冲突进对账队列）；legacy 行迁移不伪造外部事件 ID。
- 投影重建测试：新事件处理后旧快照覆盖，投影重建恢复（关联 FP-1 I1 重建器）；按事件版本合同胜出、`UNIQUE(batch_id, asset, inbox_event_id)` 物化幂等、投影 / 物化 / checkpoint 同 UoW。
- 退款聚合测试：`refund_aggregate + refund_operation` 幂等（`refund_no` 键）、**`refund_aggregate.payment_attempt_id NOT NULL` 且与额度行键一致**、**`payment_refund_quota` 单条条件更新并发预占（两笔并发部分退款不可能超额；充值主体与订单主体同契约）**、**微信退款分派状态机（仅 `confirmed_not_refunded` 释放预占；`dispatch_unknown` / `accepted` 保持占用进入查询或人工复核，禁止超时释放后重发退款；退款查询独立于 outbox 投递调度）**、额度行在结算同一 UoW 初始化、净额口径分摊、积分收回不足的 manual_review + 冻结额度、充值余额不足的 manual_review + 冻结额度、微信已退本地未补偿的人工复核路径、进程重启恢复、对账一致。
- outbox fencing 测试：claim 租约 token 条件更新、陈旧 worker token 不匹配完成被拒绝、依赖顺序、`max_attempts` 转 dead_letter、微信 `out_trade_no` / `out_refund_no` 幂等映射。
- payment_attempt 测试：`subject_type + subject_id` 主体模型（订单 / 充值 / 余额 / mock 结算分派同 UoW）；完整状态机 `draft → prepay_requested → prepay_unknown/prepay_ready → settling → succeeded/failed/expired`（含 `settling` 重启恢复、仅 `succeeded` 同交易号幂等 ACK）；`UNIQUE(provider, provider_transaction_id)` 防串单；回调只校验微信实际字段（金额 / 币种 / 商户单号 / 交易号），不依赖内部快照比较；快照写入后不可修改；`ledger_operation` 幂等占位 + 余额变更 + 流水 + outbox 同一 UoW（无"先改后写"非原子模式）；超时尝试置终态后迟到通知按新快照结算被拒绝（进入对账）。
- `compute_remain_fen` 四资产组合支付与净额退款金额测试。
- 全量回归 + `ruff` + `check_project --skip-tests` 门禁通过。
