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
  4. 逐腿预占（**D1-A.2 复核 P1：预占整体包入自有事务**——写锁、attempt 创建、账户行预占、account_hold 审计、leg 写入任一数据库异常整体回滚，不留活跃 attempt/hold/账户预占的残缺状态；业务失败在事务内完成终态与释放后正常提交再抛出）：**账户行条件预占先行**（原子 reserve），再插 account_hold 审计行（hold_key `hold:{payment_attempt_id}:<asset>`，attempt 维度）；任一腿失败 → 回滚已预占账户行 + mark_failed_preclaim + 释放腿 + 抛「{资产}不足（含预占）…无法发起支付」；账户行查无 → mark_manual_review + 抛「{资产}账户不存在（已删除？）…不得发起支付」（B3.5 合同，前置失败）
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

## 九、D1-A.1 复核（R1–R6 代码整改，方案 B，2026-08-16）

> 复核结论：**暂不通过 D1-A 合入 master，也不放行 D1-B**。绿色测试证明主路径，
> 未覆盖会造成预占泄漏、账务事实不完整或账户漂移的运行时路径。本轮只做
> **代码整改包**（不再开文档整改轮），验收固定 5 项：①同订单重试无预占泄漏
> ②余额支付 outbox 可还原完整计划 ③历史无账户 ID 不写新账户 ④案件关闭后复发
> 必为 open ⑤CAS 落空可见且可处理。

| 问题 | 整改 |
|------|------|
| R1 同订单失败→重试→取消 held 永久残留 | hold_key 由 `hold:order:{order_id}:{asset}` 改为 **attempt 维度** `hold:{payment_attempt_id}:{asset}`；`reserve()` 返回 False（同键已存在）→ 回滚本腿账户行预占 + 整体阻断（预占/审计/leg 同一事务，任一失败或未新增都不留 held 无 hold 行泄漏态）；验证：`test_r1_retry_after_failed_preclaim_no_hold_leak`（失败→重试→取消 held 归零）；**D1-A.2 复核 P1**：预占整体包入自有事务（`ensure_mock_attempt` 内 `async with transaction()`），hold 插入 / leg 写入抛异常整体回滚，验证：`test_p1_fault_inject_*_no_residue`（held=0、无 active hold、无活跃 attempt、重试后取消） |
| R2 全额储值支付 attempt 快照/outbox 缺 balanceFen、provider 退化 mock | 创建 attempt 前生成并**落库规范支付计划**（method=balance、balanceFen、totalFen、currency=CNY、memberBalanceId、planVersion=1）；attempt 冻结快照/hash/outbox 均只引用该计划；paid 载荷延续同构计划；验证：`test_r2_full_balance_payment_attempt_outbox_consistent` |
| R3 历史积分订单缺 memberBalanceId 仍按手机号补绑（结算+退款） | **禁止一切按手机号替代**：结算遇未绑定快照 → `PaymentAccountError(code="legacy_unbound")` → manual_review（仅可证明原账户 ID 的单独迁移可回填）；退款账户解析仅回退到不可变结算事实 `ledger:settle_redeem`，再无则 account_missing 案件/欠账，不写重建新账户；验证：`test_r3_legacy_unbound_settle/refund_never_writes_new_account` |
| R4 open_case 从未调用（都走 append），关闭后复发唯一键静默失败案件保持 closed | `PointsRefundReconcileRepo.ensure_open_case()`：① closed→open reopen（先按订单+原因，再按 unique_id——同一冲突身份）② 新建（同 unique_id 幂等）③ 已存在确认为 open；`_open_case_and_review` 与全部退款案件写点改走 ensure_open_case，案件 + attempt 状态同一专用 UoW；验证：`test_r4_closed_case_reopens_on_recurrence`（关闭→复发必为 open，版本递增） |
| R5 `_commit_attempt_state` 忽略 CAS 返回值；错误分流依赖中文字符串 | 新增 `app/service/payment/errors.py::PaymentAccountError(code, message)`（account_missing / balance_insufficient / points_insufficient / account_changed / account_unresolved / legacy_unbound）；结算/预占分流改 **isinstance 判定**（账户型→manual_review，其余→settling_retry，预占不足→failed 契约不变）；`_commit_attempt_state(attempt_id, coro)` 检查 CAS 结果，落空重读仅接受已知幂等终态（succeeded/cancelled/expired/failed/manual_review），否则显式并发冲突；验证：`test_r5_points_insufficient_routes_to_manual_review`（积分余额不足→manual_review 而非 settling_retry）、`test_r5_cas_conflict_on_attempt_state_visible` |
| R6 组合支付微信通知仍直接 mark_paid 绕过统一服务（余额 hold 不消费/释放、无结算 outbox） | **D1-C 硬门槛，本轮不改代码**（真实支付 No-Go 不变）：`payment_notification.py::mark_paid` 接入统一结算服务（hold 消费/释放 + order.settled outbox）列入 D1-C 必须项，与 P8 outbox fencing 并列 |

## 十、D1-A.1 验证（exit=0，可复现）

- `tests/service/test_payment_attempt_d1a.py`（24 项）：原 16 项 + R1–R5 验收 7 项 + v027 守卫
- `tests/service/test_stored_value.py`、`tests/service/test_points_payment.py`（种子绑定不可变账户 ID 与真实流程对齐；unbound/bind_id 逃生口）、`tests/service/test_coupon_payment.py`（预占失败语义）全绿
- 全量 `python -m pytest -q --no-cov -p no:cacheprovider --basetemp=D:\Temp\pytest-outside-repo-d1a` exit=0
- `python scripts/check_project.py` D1-0 守卫 passed=True（显式写方法补 `ensure_open_case`）
- ruff check/format、mypy（改动文件作用域无新增错误）、`git diff --check` 通过

## 十一、不进范围 / 移交（D1-C 硬门槛清单）

- **R6**：`payment_notification.py::mark_paid` 真实支付通知接入统一支付应用服务（余额 hold 消费/释放 + order.settled outbox）——真实支付 No-Go 维持，受控真实微信支付条件不具备
- **P8**：outbox fencing（claim 租约 / 依赖 fail-closed 运行时 worker）
- order.payment 降级为引用（D1-B）；真实支付/真实券/正式导入/真实用户开放/权威切换 No-Go；`POINTS_DEDUCTION_FENCE` 保持 True
- 审阅分支追加提交，**不改写** `5bc022e…`（内容）/ `d438bc0…`（归档）；master 双远端保持 `b30b2066ac27ef2326edae01240ab33882a3bf6e` 直至项目负责人复核放行

## 十二、D1-A.2 复核（有界整改，方案 B，2026-08-16）

> 复核结论（项目负责人对 `4596d7e` / 归档头 `ab4b11b`）：**暂不通过，推荐方案 B
> （D1-A.2 有界整改）**——R2/R3/R5 主验收基本成立；R1 的异常事务原子性和 R4 的
> 退款案件复发仍未完整修复。不 fast-forward master，不放行 D1-B。整改后**只复核
> 两项高风险验收**，不再扩展审查范围。

| 问题 | 整改 |
|------|------|
| P1【高】预占缺少自有事务（unified.py） | attempt、账户行预占、account_hold、leg 连续写入无自有事务边界——账户预占成功后 reserve()/upsert_leg() 抛异常会留下「有预占、无 hold/leg」的残缺状态。整改：`ensure_mock_attempt` **预占整体包入 `async with self._order_repo.transaction()`**（写锁、create_active、账户行预占、hold 审计、leg 写入同一事务，数据库异常整体回滚，不留活跃 attempt/hold/账户预占）；余额不足 / 账户缺失等业务失败在事务内完成 failed / manual_review 终态与释放（正常提交）后于事务外抛出，CAS 落空（同事务写锁下理论不可达）显式抛并发冲突；预占事务内直接调 mark_* 原语（不再经 `_commit_attempt_state` 的内部 commit，避免嵌套事务提前提交）。验证：`test_p1_fault_inject_hold_reserve_raises_no_residue` / `test_p1_fault_inject_leg_upsert_raises_no_residue`（held_*=0、无 active hold、无活跃 attempt、故障解除后可重试并取消） |
| P2【高】退款案件复发未完整修复（points/payment.py 383/520/534/596/607） | R4 只修了支付计划变更路径；退款运行时 account_missing / redeem_missing / redeem_mismatch / award_missing / award_mismatch 仍直接 `append()`（INSERT OR IGNORE），案件人工关闭后复发保持 closed 却被记为「存在 open 案件」。整改：退款运行时**全部**案件写点统一改走 `ensure_open_case()`（7 处全量转换），**仅确认案件为 open 后**设置案件标记（case_appended）。验证：`test_p2_refund_case_reopens_on_recurrence`（参数化 5 原因，每种执行「开案→人工关闭→同一异常再次退款」，断言 open 且版本递增） |
| P3【低】文档键不一致 | 本规格第 28 行仍写旧键 `hold:order:<id>:<asset>` 与实际 attempt 维键不一致。整改：统一为 `hold:{payment_attempt_id}:<asset>`（第 28 行 + R1 映射表同步更新），杜绝后续按旧合同回归 |

## 十三、D1-A.2 验证（exit=0，可复现）

- `tests/service/test_payment_attempt_d1a.py`（31 项）：原 24 项 + P1 故障注入 2 项 + P2 参数化复发 5 项
- `tests/service/test_stored_value.py`（prepare 嵌套事务场景）、`test_points_payment.py`、`test_coupon_payment.py`、`test_order.py` 全绿
- 全量 `python -m pytest -q --no-cov -p no:cacheprovider --basetemp=D:\Temp\pytest-outside-repo-d1a` exit=0
- `python scripts/check_project.py` D1-0 守卫 passed=True（`--skip-tests` 模式 = pre-commit 同参）
- ruff check/format、mypy（改动文件作用域无新增错误）、`git diff --check` 通过
- 审阅分支追加提交，**不改写** `4596d7e…`（内容）/ `ab4b11b…`（归档）；master 双远端保持 `b30b2066` 直至项目负责人按两项高风险验收复核放行
