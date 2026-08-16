# D1-A 最小资金核心纵向切片（设计定稿）

- trace_id: 20260816-accounting-d1a-minimal-slice
- 状态: 设计定稿（G0 决定记录第四节的 D1-A 立项；项目负责人 2026-08-16 指示启动开发测试）——**2026-08-16 复核追加整改包：公开支付入口事务语义 / 真实预占 / 储值账户身份高风险缺口按方案 B 聚焦整改（P1–P7），见 `docs/specs/2026-08-16-accounting-d1a-runtime-remediation.md`（不改写 69a31c9/6c2b2a0）**
- 范围边界: **仅 mock/余额订单**的 预占→结算→取消释放→重放 + 不可变账户 ID + 债务闭环；真实支付、真实券、正式导入、真实用户开放、权威切换保持 No-Go；`POINTS_DEDUCTION_FENCE=True` 保持
- 对齐: ADR 0008 D1-A（统一支付应用服务 / payment_attempt / account_hold / accounting_outbox / 单一 UoW）+ G0 决定记录验收六项

## 一、验收矩阵（六项，全部可复现）

| # | 场景 | 期望 |
|---|---|---|
| A1 | 预占后失败 | 结算中途失败 → `payment_attempt` 进入 `settling_retry`（保持 hold 占用），不释放、不二次消费 |
| A2 | 结算重放 | 对同一订单重复 `settle` → 幂等（attempt 已 `succeeded` 直接返回，legs/holds/ledger/outbox 不重复写） |
| A3 | 取消/超时释放 | 取消或超时 → attempt `cancelled`/`expired` + 全部 active hold 释放（`released`），不再消费 |
| A4 | 双连接单主体竞争 | 双连接同步屏障并发 settle → 恰一个 attempt 进入 `succeeded`（败者 CAS 冲突或瞬时锁），事实唯一 |
| A5 | 账户删除重建 | 按不可变 `member_balance_id` 结算/退回；账户行被删后重建（新 id）→ 旧 id 查无 → 阻断并进 `manual_review`，**禁止按手机号新建替代账户** |
| A6 | 短缺补足结案 | clawback 余额不足 → 欠账 `open`（含 remaining）；后续积分入账按 `min(入账额, remaining)` 原子部分偿还；补足后 `open→settled`（version CAS）；重复偿还幂等 |

## 二、数据模型（v027 迁移）

### payment_attempt（支付尝试，结算命令事实源 + 幂等源）
- `id`、`subject_type`（order / recharge）/ `subject_id`、`provider`（mock / wechat / balance）、`merchant_order_no`
- `payment_snapshot_json`（不可变快照，`snapshot_hash` = sha256）+ `member_balance_id`（快照绑定账户，B3.5 延续）
- `status`: `draft → prepay_ready → settling → (succeeded | settling_retry → prepay_ready | cancelled | expired | manual_review)`；`failed` 仅来自未进入结算的前置失败（B3.5 合同）
- `active_command_type` / `lease_token` / `lease_until` / `state_version`（CAS）/ `prepay_started_at` / `settled_at`
- **subject-slot 部分唯一索引**：`CREATE UNIQUE INDEX ... ON payment_attempt(subject_type, subject_id) WHERE status IN ('draft','prepay_requested','prepay_unknown','prepay_ready','settling','settling_retry','manual_review')`（单主体单活跃尝试，含人工复核未解除前禁止同主体新尝试，A4；终态 succeeded/cancelled/expired 不占槽）

### payment_attempt_leg（尝试腿，预占/消费额明细）
- `id`、`payment_attempt_id`、`asset_type`（balance / points / coupon / wechat）、`amount_fen`、`status`（reserved / consumed / released）
- `UNIQUE(payment_attempt_id, asset_type)`

### account_hold（预占）
- `id`、`hold_key UNIQUE`、`subject_type` / `subject_id`、`payment_attempt_id`、`asset_type`、`amount_fen`、`status`（active / consumed / released / expired）、`member_balance_id`（不可变账户绑定）、`expires_at`、`created_at/updated_at`

### accounting_outbox（账务出站事件，D1-C 预留）
- `id`、`operation_key UNIQUE`、`operation_type`（order.settled / order.released / ...）、`subject_type` / `subject_id`、`payload_json`、`status`（pending / processing / succeeded / failed / dead_letter）、`attempt_count`、`lease_token` / `lease_until`、`depends_on_operation_key`、`created_at/updated_at`
- claim/complete/fail 均条件更新（token/attempt CAS）；依赖行存在且 `succeeded`（B3.5 合同）

### refund_shortfall_debt 扩展（债务闭环）
- `ALTER TABLE ... ADD COLUMN remaining INTEGER NOT NULL DEFAULT 0`（剩余未偿额）
- `ALTER TABLE ... ADD COLUMN version INTEGER NOT NULL DEFAULT 1`（open→settled / 部分偿还 CAS）

## 三、统一支付应用服务（D1-A 核心）

`app/service/payment/unified.py` — `UnifiedPaymentApplicationService`（账务写唯一入口，ADR D1-0）：

- `settle_mock_order(order)`：**同一 UoW** 内——
  1. subject-slot 找活跃 attempt；无则创建（`prepay_ready` + legs reserved + holds active，快照绑定 `member_balance_id`）
  2. CAS `prepay_ready → settling`（`WHERE id=? AND status=? AND state_version=?`；败者读最新重放或抛冲突）
  3. 写 legs `consumed` + holds `consumed` + `ledger_operation`（settle_redeem / settle_award 既有）+ `order.payment` 置 `paid` + outbox `order.settled`
  4. CAS `settling → succeeded`；中途异常 → `settling_retry`（A1）
- `release_order_holds(order_id, reason)`：取消/超时 → 活跃 attempt → `cancelled`/`expired` + holds `released`（A3）；已 `succeeded` 禁止释放
- `replay_settle(order_id)`：`settling_retry` 重放（A2 幂等由 CAS 兜底）
- `confirm_mock_payment` 改造：对外行为不变（paid + 券核销 + 发分），内部改走统一入口
- 双连接：所有状态迁移用条件更新（A4）

## 四、不可变账户 ID（评审问题 2）

- `MemberBalanceRepo` 增 `get_by_id(id)` / `credit_points_by_id(id, amount)` / `deduct_points_if_sufficient_by_id(id, amount)`（**不 INSERT 新建**；行缺失返回 None/False）
- 结算（redeem 扣减 / award 发放）与退回一律按快照 `member_balance_id`；`get_by_id` 查无 → 阻断 + attempt/案件进 `manual_review`（A5）
- 账务路径禁止 `credit_points` 的按手机号 INSERT 新建分支（该分支仅保留给会员导入 upsert 通道）

## 五、债务闭环（评审问题 3）

- `RefundShortfallDebtRepo` 增 `repay(debt_id, amount, version)`：`UPDATE ... SET remaining = remaining - ?, version = version + 1, updated_at=? WHERE id=? AND status='open' AND version=? AND remaining >= ?`；`settle_if_fully_repaid`：remaining=0 → `open→settled`（同 UoW）
- 积分入账（award_on_payment / 退款 return）**先偿债后入账**：入账额 `min(入账额, 该账户所有 open 债务 remaining 之和)` 依次 repay，剩余才可用（A6）
- `open_case()` 接入冲突重现路径（legs/holds 数据冲突 → 案件 + attempt manual_review）

## 六、实施清单

1. `app/migrations/v027_accounting_d1a.sql`（四表 + 部分唯一索引 + debt 扩展列）
2. `app/repository/payment_attempt_repo.py` / `account_hold_repo.py` / `accounting_outbox_repo.py`（零 commit，条件更新）
3. `app/repository/member_balance_repo.py`（by-id 方法）、`refund_shortfall_debt_repo.py`（repay/settle）
4. `app/service/payment/unified.py` 统一服务；`payment_runtime.confirm_mock_payment` 改接入
5. 测试 `tests/service/test_payment_attempt_d1a.py`（A1–A6 + 现有 mock/combined/coupon/points 回归）
6. ADR 0008 注记（D1-A 落地） + `docs/specs/` 本设计定稿
7. 全量验证 → 两段提交推送审阅分支（master 保持 b30b206）

## 七、不进范围（保持 No-Go）

真实微信 prepay/notify 结算、真实券 TAKE/CONSUME 投影、provider inbox 回调 ACK、正式导入、真实用户开放、权威切换；`POINTS_DEDUCTION_FENCE` 与 `apply_points` 围栏不改。
