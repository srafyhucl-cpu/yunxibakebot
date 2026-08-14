# ADR 0008：账务核心一致性（Unit of Work / 券事件-投影 / 持久退款聚合）

- status: proposed
- date: 2026-08-14
- trace_id: `20260814-member-loyalty-accounting-contract`
- decision_owner: project owner（决策主体 / 唯一批准人）
- technical_advisor: AI (Codex)（仅技术建议，不构成批准）
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

本 ADR 处于 **proposed**：作为设计裁决，代码实施（D1 实施阶段）须在批准后单独落地。

## Decision

### D1-A：单一 Unit of Work 与账务 Outbox

**第一批账务仓储清单（零 commit/rollback 契约）**：以下仓储只执行 SQL，**不自行 commit / rollback**（移除内部 `commit()`），并纳入"零 `commit/rollback` 检查"与故障注入回滚测试：

- `CouponInventoryRepo`（含 `insert`/`consume`/`refund`）
- `PointsLedgerRepo`（含 `insert`）
- `MemberBalanceRepo`
- `StoredValueRepo`（`stored_value_recharge` / `balance_ledger`）
- `OrderRepo`（订单 / `payment.json` 快照）
- `InboxRepo`（`enqueue` 当前自行 commit，见 `app/repository/inbox_repo.py:27`，改入 UoW 契约）

- 事务边界唯一属主为**应用服务（UoW 属主）**：`OrderApplicationService`、`StoredValueOrderPaymentService` 等通过统一事务上下文声明边界，退出时统一提交，异常时整体回滚。
- 跨仓储复合操作（订单置 paid + 扣余额 + 核销券 + 发分 + 写流水 + 写 outbox）必须处于同一事务；任一后续步骤失败，整体回滚（无 paid、无扣款、无核销、无发分、无外发）。
- 迁移顺序：先为清单内仓储加"零 commit/rollback"静态检查 + 故障注入测试（红），再逐仓储移除自提交（绿），最后删除 `coupon/payment.py` 与 `points/payment.py` 中对 "savepoint" 错误字符串匹配的吞错逻辑。
- 外部调用使用**独立 `accounting_outbox` 表**（非 `inbox_events`）：`inbox_events` 按 ADR 0006 只承载入站事件，且其 `enqueue` 自提交、不能与账务 UoW 原子写入。微信关单/退款等外部动作统一写 `accounting_outbox`，与订单/余额/券/积分**同事务写入**，由独立投递 worker 消费并重试。**删除"outbox 或 Saga"的未决表述**——本决策即定稿为 `accounting_outbox` + 幂等投递。

### D1-B：券生命周期事件与当前态投影分离（唯一模型）

**唯一模型（批准后即定稿，不再保留多个实施候选）**：

- 事件表 `coupon_events`（v025+ 迁移）：每行一条券生命周期事件；**业务幂等键 `event_key`** 由（券实例 `coupon_id` + `mobile` + 来源 `source` + 业务引用 `order_no` / `refund_no` / 外部事件 ID + 周期序号）派生，支持 `TAKE → CONSUME → BACK → CONSUME` 多周期。
- **事件排序规则**：`(occurred_at, 事件写入序号 id)` 单调；来源权重不再参与事件排序（权重语义移入投影）。
- 当前态投影 `coupon_current_state`（条件投影）：按 `coupon_id + mobile` 聚合最新事件行，投影出 `status / order_no / refund_no / valid_from / valid_until / value_fen` 等当前态字段，供可用券列表、核销判定与 local 权威读取。
- 旧规则 `idx_coupon_inventory_dedup (coupon_id, status, mobile)` 标为**"现状待迁移"**：迁移期保留以服务既有数据，新写入走 `coupon_events.event_key`；迁移完成后删除旧唯一索引。
- local 权威下 webhook/import 券以事件形式入 `coupon_events`，不再被 `source IN ('order','local')` 过滤丢券；FP-2 切换唯一键冲突与 FP-3 券 BACK 二次核销限制一并解除。
- 该设计**必须前置于 FP-3 退款与 FP-2 权威切换**（二者执行前设计门禁）。

### D1-C：持久退款聚合（退款政策待裁决）

**全额 / 部分退款政策**由项目负责人先行裁决（当前主计划仅"全单退款"；若引入部分退款须同步裁决金额分摊规则），本 ADR 记录为执行前门禁。

- 新增 `refund_aggregate`：`refund_no`、`order_id`、`policy`（full / partial，待裁决）、**原支付快照**（`payment.json` 原文：total/coupon/balance/points/remain）、各资产分摊（微信款 / 余额 / 积分 / 券）、总状态集 `requested / processing / succeeded / failed / manual_review`、对账状态。
- 新增 `refund_operation`（子操作）：每步补偿一个资产——`operation_key` 幂等键、资产类型、金额 / 积分单位、状态 `pending / success / failed / manual_review`、重试计数、人工复核条件、微信退款号 / 异步结果关联。
- 微信适配器补齐：关单、退款、退款查询、异步退款结果通知。
- 券 `BACK` 作为 `refund_operation` 的一步接入；`compute_remain_fen(total, coupon, balance, points)` 为唯一金额公式。
- 补偿顺序：微信款 → 积分（退回 pointsUsed / 收回 pointsAwarded）→ 余额 → 券（核销回退）；任一步失败，微信退款成功后本地补偿失败时进入 `manual_review` 并由对账任务发现（**微信已退、本地未补偿**的恢复策略必须可观测、可人工补录）。

## Alternatives

- 维持现状（仓储自 commit + savepoint 吞错）：改动最小，但"券已核销订单已 paid 而积分失败"不可回滚，资金一致性无保证，否决。
- 引入分布式事务框架：当前单机 SQLite、单 worker，无跨服务事务需求；用本地 UoW + outbox/补偿即可满足，避免引入分布式事务基础设施，否决。
- 仅改文案/文档：不解决结构性回滚与券生命周期问题，否决。

## Consequences

- 所有支付 / 退款路径的事务边界收敛到 UoW 属主，失败可整体回滚。
- 券生命周期支持多周期核销与退回；local 切换唯一键冲突消除（需 v025+ 迁移与基线迁移）。
- 退款具备持久状态、幂等与对账能力。
- 涉及核心迁移（券表、退款表）与全量回归；故障注入测试纳入门禁。
- 实施期间建议配合方案 C（服务端关闭储值/积分/券写操作）作为临时边界，降低风险。

## Verification（实施阶段验收）

- 账务仓储清单"零 commit/rollback"静态检查通过（红绿迁移）。
- 故障注入集成测试：订单 / 余额 / 券 / 积分 / outbox 任一步注入失败，断言全部状态回滚（无 paid、无扣款、无核销、无发分、无外发）。
- 券生命周期测试：`TAKE → CONSUME → BACK → CONSUME` 全周期通过（基于 `coupon_events.event_key`）；local 权威下 webhook/import 有效券可迁移、可核销；旧去重规则标记待迁移并删除。
- 退款聚合测试：`refund_aggregate + refund_operation` 幂等、异步结果、补偿顺序、微信已退本地未补偿的人工复核路径、进程重启恢复、对账一致。
- `compute_remain_fen` 四资产组合支付与退款金额测试。
- 全量回归 + `ruff` + `check_project --skip-tests` 门禁通过。
