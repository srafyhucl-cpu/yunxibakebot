# D1-A 运行时整改包（复核评审问题 P1–P7 聚焦整改，方案 B）

- trace_id: 20260816-accounting-d1a-runtime-remediation
- 状态: 整改完成（审阅分支追加整改提交，不改写 69a31c9/6c2b2a0；等待项目负责人固定范围复核后决定 D1-A 合入 master 与 D1-B 放行）
- parent_trace_id: `20260816-accounting-d1a-minimal-slice`
- 来源: 项目负责人对 D1-A 正式收口的复核结论（2026-08-16，Go/No-Go=暂不通过）——「成功路径、CAS 和仓储去自提交方向正确，但公开支付入口的事务语义、真实预占和储值账户身份仍有高风险缺口；当前绿色测试不能证明真实入口满足 A1/A5」；8 项问题 P1–P8，推荐方案 B（审阅分支追加整改包，不改写已归档提交）
- 范围: P1–P7 聚焦整改（P8 outbox fencing 不阻断本轮，D1-C 前必须实现）；真实支付/真实券/正式导入/真实用户开放/权威切换保持 No-Go；`POINTS_DEDUCTION_FENCE=True` 保持

## 一、评审问题 → 整改映射

| 问题 | 评审要点 | 整改落地 |
|---|---|---|
| P1 | 公开支付入口（confirm_mock_payment）失败时整体回滚，settling_retry 只存在于测试显式 commit 场景 | **两阶段结算**：阶段一预占（attempt+legs+holds）在**自有 UoW** 提交；阶段二结算（置 paid+核销券+发分+消费 hold）在独立事务；失败时事务回滚资产副作用，处理器重读 attempt 后以**当前 state_version** 持久化 settling_retry/manual_review（新 UoW），再抛出 |
| P2 | 储值账户身份：余额支付/组合支付在结算前才解析手机号账户，账户删除重建后身份漂移 | **首次储值操作即固定不可变账户**：`resolve_member_balance_id`（移动→余额账户 id，查无即阻断）；`pay_order_with_balance` 先写 `payment.memberBalanceId` 再**重读订单**（attempt 快照含绑定）；`prepare_combined_payment` 预占即绑定；未绑定储值退款 → `_append_refund_debt`（operation_key `order_refund:<id>`）不 credit |
| P3 | 预占只在 account_hold 表记审计行，可用额未真正被占用（可用额公式未生效） | **账户行真实预占**：`member_balance` 增 `held_points / held_stored_value_fen`（v027 追加列）；原子 reserve/clear（单条条件 UPDATE，`points-held_points>=?`）；可用额 = 余额 − 预占；多腿部分失败回滚已预占账户行 |
| P4 | 支付计划在预占后可能变更（下单快照≠结算快照），且 outbox 载荷读调用前 order.payment | **attempt 快照校验**：复用活跃尝试时校验 snapshot_hash（sha256(dumps_payment(loads_payment(payment)))）+ 腿金额；不一致 → open_case（`points:settle:<id>`，reason=plan_changed）+ mark_manual_review + 阻断；**outbox 载荷 = attempt 不可变快照 + 结算结果**（不读调用前 order.payment） |
| P5 | manual_review 状态无处置矩阵：无副作用可释放、有副作用（已 paid）禁止释放 | **release_order_holds 矩阵**（按订单最新支付快照裁决）：manual_review + paid → 抛「仅可人工结案」；manual_review + 未付 → 可释放；succeeded → 禁止释放 |
| P6 | 偿债只记扣减金额，全量 award 事实不可对账（clawback 核验依据缺失） | **points_ledger 记实际入账**（credit_amount），偿债为独立 `ledger_operation REFUND_DEBT_REPAY` 事实；**全量 award 事实 = `ledger:settle_award:<id>`**（clawback 核验依据，legacy 无此操作时回退 award_entry）；`_repay_open_debts` 只偿 `:clawback` 键债务（防跨资产偿储值债）；open_case 接入统一服务 |
| P7 | v027 回填 `remaining=0` 会连已结案行一起回填成 remaining>0 矛盾态 | **回填限定 open**：`UPDATE refund_shortfall_debt SET remaining = amount WHERE remaining = 0 AND status = 'open'`（已结案行保持 remaining=0）；迁移文本守卫测试 |
| P8 | outbox fencing 未实现（claim 租约/依赖 fail-closed 的运行时 worker） | **不阻断本轮**，明确移交 D1-C 前必须实现（本包保持 outbox enqueue 同事务写入 + 幂等键） |

## 二、两阶段结算（P1）事务语义

- **阶段一（`ensure_mock_attempt`，自有 UoW 提交）**：
  1. **写锁串行化**：无操作 `UPDATE orders SET updated_at = updated_at WHERE id = ?` 先行（WAL + deferred 事务下 UNIQUE 索引只在语句期检查、不在 COMMIT 复查——无写锁时两个并发 `INSERT OR IGNORE` 同一 subject-slot 可同时成功；首个写者持写锁，第二写者按 busy_timeout 等待首个提交后重读并复用胜者尝试）
  2. subject-slot 找活跃尝试 → 命中即校验一致性（P4）复用；终态 succeeded 直接返回原尝试
  3. 无活跃 → create_active（prepay_ready，快照冻结支付计划 + member_balance_id 绑定）
  4. 逐腿预占：**账户行条件预占先行**（原子 reserve），再插 account_hold 审计行（hold_key `hold:order:<id>:<asset>`）；任一腿失败 → 回滚已预占账户行 + mark_failed_preclaim + 释放腿 + 抛「{资产}不足（含预占）…无法发起支付」；账户行查无 → 抛「{资产}账户不存在（已删除？）…不得发起支付」（B3.5 合同，前置失败）
- **阶段二（`settle_mock_order` 结算 UoW）**：begin_settle CAS（prepay_ready/settling_retry→settling，败者重读幂等或抛冲突）→ 储值腿按 by-id 扣减（余额不足 → 抛「储值账户余额不足（含预占）…需人工复核」）→ settle_actions（置 paid CAS → 核销券 → 发分）→ 消费 holds（账户行 clear + 审计行 consumed）→ legs consumed → outbox（attempt 快照 + result）→ complete_settle CAS
- **失败处置**：事务回滚后重读 attempt（回到 begin_settle 前状态，即 prepay_ready/settling_retry）；账户型错误 → mark_manual_review；其余 → mark_retry；**新 UoW 提交后再抛出**
- 公开路径 confirm_mock_payment 不再包外层事务（unified 自持 UoW）；_perform_settle（置 paid+券+分）在结算 UoW 内

## 三、真实预占（P3）账户行语义

- `member_balance` 增列：`held_points INTEGER NOT NULL DEFAULT 0` / `held_stored_value_fen INTEGER NOT NULL DEFAULT 0`
- **可用额 = balance − held**（真实占用，非仅审计）：`reserve_points/reserve_stored_value_fen` 单条条件 UPDATE（`WHERE id=? AND points-held_points>=?`，失败即不足）；`clear_points_hold/clear_stored_value_fen_hold` 同构
- 顺序：账户行 reserve（原子）→ account_hold 审计行 insert；多腿部分失败 → `_rollback_partial_reserve` 只回滚已预占账户行
- 结算消费 / 取消释放对称：账户行 clear + 审计行 consumed/released
- 储值端 P2 配套：`credit_by_id/deduct_by_id`（幂等 unique_id），`deduct_by_id` 不足/查无返回 None → 债务化

## 四、attempt 快照校验与 outbox 载荷（P4）

- 复用活跃尝试校验：`snapshot_hash = sha256(dumps_payment(loads_payment(payment)))` 比对 + 各腿金额比对（leg_by_asset）；不一致 → open_case + mark_manual_review（提交）+ 抛「支付计划已变更…禁止按旧计划结算」
- outbox `order:settled:<id>` payload：`{"attempt_id", "snapshot": 快照内嵌支付计划, "result": "settled"}`；`order:released:<id>` 同构

## 五、manual_review 处置矩阵（P5）

| 订单最新支付快照 | release_order_holds 行为 |
|---|---|
| manual_review + paid（有资产副作用） | 抛「订单已结算（支付成功），人工复核尝试禁止取消释放，仅可人工结案」 |
| manual_review + 未付（无副作用） | 正常释放（cancelled/expired + holds released + outbox 事件） |
| succeeded | 禁止释放（返回 False） |

## 六、可对账事实（P6）

- points_ledger：award/refund_return 记**实际入账额**（credit_amount）；偿债记独立 `ledger_operation`（REFUND_DEBT_REPAY，`ledger:debt_repay:<id>`）
- 全量 award 事实：`ledger:settle_award:<id>`（award_on_payment 写）；clawback 核验优先读它，legacy 订单回退 award_entry，两者皆无 → award_missing 案件
- `_repay_open_debts` 只偿 `operation_key` 含 `:clawback` 的债务（避免跨资产把储值债一并偿还）
- 余额对账：账户余额 = 期初 + Σ(实际入账) − Σ(扣减)；测试断言 award 流水 40 = award 100 − 偿债 60

## 七、验证（全部可复现，exit=0）

- `tests/service/test_payment_attempt_d1a.py`（16 项）：原 A1–A6 + P1 公开路径失败→settling_retry→修复重放；P3 双订单超预占阻断 + 释放后重预占（账户行 held 断言）；P4 计划变更→open_case + manual_review + outbox 快照载荷断言；P5 manual_review 矩阵两用例；P6 实际入账/全额事实/债务 remaining 对账；P7 回填仅 open（行为 + 迁移文本守卫）
- `tests/service/test_stored_value.py`（P2/P3 语义更新：prepare 预占不扣减、结算才扣减、取消释放预占）等关联套件全绿
- 全量 `python -m pytest -q --no-cov -p no:cacheprovider --basetemp=D:\Temp\pytest-outside-repo-d1a` exit=0
- `python scripts/check_project.py` D1-0 守卫 passed=True（unified.py 方法级 allowlist 增补内部写点、member.py {credit_by_id, deduct_by_id}、显式写方法补 `mark_failed_preclaim / reserve_* / clear_*_hold`）
- ruff check/format、mypy（改动文件作用域无新增错误）、`git diff --check` 通过

## 八、不进范围 / 移交

- P8 outbox fencing（claim 租约/依赖 fail-closed 运行时 worker）：**D1-C 前必须实现**（本包仅保持 enqueue 同事务 + 幂等键）
- order.payment 降级为引用（D1-B）；真实支付/真实券/正式导入/真实用户开放/权威切换 No-Go；`POINTS_DEDUCTION_FENCE` 保持 True
- 审阅分支追加提交，**不改写** `69a31c98333a49001033d1f791510e800e72beb8`（内容）/ `6c2b2a0ca3223afc16a2a0f69a7b7c627ad83f9a`（归档）；master 双远端保持 `b30b2066ac27ef2326edae01240ab33882a3bf6e` 直至项目负责人复核放行
