# ADR 0008：账务核心一致性（Unit of Work / 券事件-投影 / 持久退款聚合）

- status: proposed
- date: 2026-08-14
- trace_id: `20260812-member-loyalty-storedvalue`
- decision_owner: project owner / AI (Codex)
- related_docs:
  - `docs/specs/2026-08-12-member-loyalty-storedvalue-plan.md`
  - `docs/specs/2026-08-12-member-loyalty-followup-wechat-pay.md`
  - `docs/specs/2026-08-12-member-loyalty-followup-local-authority.md`
  - `docs/harness-engineering/adr/0007-local-authority-cutover.md`
  - `app/service/order/application.py`、`app/service/order/payment_runtime.py`、`app/service/order/payment_notification.py`
  - `app/service/stored_value/payment.py`、`app/service/points/payment.py`、`app/service/coupon/payment.py`
  - `app/repository/coupon_inventory_repo.py`、`app/repository/base.py`

## Context

2026-08-14 完整复核确认三项结构性风险（均基于代码实测）：

1. **Unit of Work 名存实亡**：`CouponInventoryRepo.insert`（`app/repository/coupon_inventory_repo.py:70`）与 `PointsLedgerRepo.insert`（`app/repository/points_ledger_repo.py:44`）在流程中途自行 `commit()`，把外层复合事务连根提交。`payment_runtime.py` / `payment_notification.py` / `stored_value/payment.py` 的"扣余额 → 置 paid → 核销券 → 发分"复合事务，其真实提交点内嵌于声明边界（`order/application.py:141/166` 的 `transaction()`）。后果：**券已核销、订单已置 paid 之后，若发分失败，无法整体回滚**——订单/余额/券固化、分未发。base.py 的 SAVEPOINT 机制退化，`coupon/payment.py:143/169` 用字符串匹配捕获 savepoint 释放异常后吞错。
2. **券唯一索引同时承担生命周期去重与当前态约束**：`idx_coupon_inventory_dedup (coupon_id, status, mobile)`（v024:66）不含 source。`TAKE → CONSUME → BACK → CONSUME` 的第二次核销在结构上被禁止（当前靠"仅 TAKE 可消费"状态检查使 BACK 成为终态）；同时 local 权威下 webhook/import 券行占用键位导致本地状态无法写入——这是 FP-2 切换唯一键冲突的根因。
3. **退款聚合缺失**：无 `refund` 服务、无退款持久表；微信适配器无关单/退款/退款查询；券 BACK 写入链路（`CouponService.refund_coupon`）无任何订单流程调用；跨"微信款 → 积分 → 余额 → 券"的补偿顺序未实现。现有补偿仅覆盖未支付关单（余额 → 积分 → 清券快照）。
4. **文档与代码金额公式不一致**：代码 `compute_remain_fen(total, coupon, balance, points)`（`payment_state.py:118`）已含券；主计划与 FP-3 文档公式漏 `coupon_fen`。

本 ADR 处于 **proposed**：作为设计裁决，代码实施（D1 实施阶段）须在批准后单独落地。

## Decision

### D1-A：单一 Unit of Work

- 仓储（repository）**只执行 SQL，不自行 commit / rollback**。移除 `CouponInventoryRepo.insert`、`PointsLedgerRepo.insert` 等内部 `commit()`。
- 事务边界唯一属主为应用服务（UoW 属主）：`OrderApplicationService`、`StoredValueOrderPaymentService` 等通过统一事务上下文声明边界，退出时统一提交，异常时整体回滚。
- 跨仓储复合操作（订单置 paid + 扣余额 + 核销券 + 发分 + 写流水）必须处于同一事务；任一后续步骤失败，整体回滚（无 paid、无扣款、无核销、无发分）。
- 移除 `coupon/payment.py` 与 `points/payment.py` 中对 "savepoint" 错误字符串匹配的吞错逻辑（根因消除后不再需要）。
- 微信等外部调用不进入本地 SQLite 事务：使用持久 outbox（`inbox_events` 既有模型）或显式补偿/Saga，保证外部调用失败可重试或补偿。

### D1-B：券生命周期事件与当前态投影分离

- `coupon_inventory` 语义收敛为**生命周期事件表**：去重键从 `(coupon_id, status, mobile)` 改为业务幂等键（外部事件 ID / 订单号 + 核销周期 / refund_no），允许 `TAKE → CONSUME → BACK → CONSUME` 多周期。
- 新增**当前态投影**（`coupon_current_state` 或等价聚合查询），按 `coupon_id + mobile` 投影最新有效状态，供可用券列表、核销判定与 local 权威读取。
- 事件与投影分离后，FP-2 的 local 切换唯一键冲突与 FP-3 券 BACK 二次核销限制一并解除。
- 该设计**必须前置于 FP-3 退款与 FP-2 权威切换**（作为二者执行前设计门禁的一部分）。

### D1-C：持久退款聚合

- 新增持久退款聚合表：`refund_no`、`order_id`、金额分摊（微信款 / 余额 / 积分 / 券）、状态集 `requested / processing / succeeded / failed / manual_review`、退款单幂等键、异步结果、补偿状态、对账状态。
- 微信适配器补齐：关单、退款、退款查询、异步退款结果通知。
- 券 `BACK` 接入退款聚合；`compute_remain_fen(total, coupon, balance, points)` 为唯一金额公式（文档同步修正）。
- 跨资金补偿顺序：微信款 → 积分（退回 pointsUsed / 收回 pointsAwarded）→ 余额 → 券（核销回退），失败进入重试/人工复核。

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

- 故障注入集成测试：订单 / 余额 / 券 / 积分任一步注入失败，断言全部状态回滚（无 paid、无扣款、无核销、无发分）。
- 券生命周期测试：`TAKE → CONSUME → BACK → CONSUME` 全周期通过；local 权威下 webhook/import 有效券可迁移、可核销。
- 退款聚合测试：退款单幂等、异步结果、补偿顺序、进程重启恢复、对账一致。
- `compute_remain_fen` 四资产组合支付与退款金额测试。
- 全量回归 + `ruff` + `check_project --skip-tests` 门禁通过。
