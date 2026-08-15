# 后续工作包 FP-2：本地权威切换（2027-06）

- status: pending
- parent_trace_id: `20260812-member-loyalty-storedvalue`
- 执行时须生成独立 trace_id（如 `2027MMDD-member-loyalty-local-authority`），不得复用父计划 trace
- 决策依据：[ADR 0007](../harness-engineering/adr/0007-local-authority-cutover.md)
- 所属计划：[2026-08-12-member-loyalty-storedvalue-plan.md](./2026-08-12-member-loyalty-storedvalue-plan.md)（M3 积分 / M4 优惠券第二阶段）
- 最早候选执行窗口：2027-06；不得自动执行，须由项目负责人明确批准
- 上线边界：2027-05-31（含）前仅开发 / 调试 / 测试，不开放真实用户
- 前置依赖：FP-1（会员数据正式导入）、FP-3（真实微信支付）、FP-4（小程序正式发布）全部完成
- 拆分来源：2026-08-14 M1–M6 完整评审（方案 B 分阶段结项）；2026-08-14 深度复核修正

## 背景与决策

M3 与 M4 第一阶段已上线 `POINTS_AUTHORITY=youzan`、`COUPON_AUTHORITY=youzan`（有赞维护余额 / 券库存）。第二阶段目标：以 **Platform 本地账务域为权威**（`member_balance` / `coupon_inventory` / `points_ledger`），小程序仅是用户入口；切换完成后关停有赞小程序。储值、积分、券、身份分别建模，各自独立对账与切换。决策详见 ADR 0007。

本工作包的 **2027-06** 仅表示最早候选切换窗口，不构成自动执行授权。在项目负责人明确批准正式上线前，小程序不承接真实用户流量，所有切换演练仅限隔离环境、受控数据或授权测试账号。

## 当前实现事实（复核修正）

- `POINTS_AUTHORITY` / `COUPON_AUTHORITY` 均为**进程级配置**（`app/config.py`），不支持"受控范围灰度"到单客户 / 单店铺。
- 积分 `local`：`event_member.py` 在 `POINTS_AUTHORITY != "local"` 时用有赞 `total` 覆盖 `member_balance.points`；`local` 时只写流水 / 审计镜像（已实现）。
- 优惠券 `local`：`coupon_inventory_repo` 在 `authority=local` 时**只识别 `source IN ('order','local')` 的券行**，现有 `import` / `webhook` 来源的有效券行会被过滤，导致已有有效有赞券从可用列表消失。
- 本地写入后不能仅靠改回环境变量实现无损回滚（已落库数据不会自动回退）。
- **唯一键冲突（切换模型阻断项）**：`coupon_inventory` 唯一索引 `idx_coupon_inventory_dedup (coupon_id, status, mobile)`（v024:66）不含 `source`。webhook 来源券行已占用 `(coupon_id, status, mobile)` 键位后，local 状态无法再写入同状态行；`source IN ('order','local')` 过滤叠加唯一键独占，使切换模型在无补偿设计下不可执行，须按 ADR 0008 的 `coupon_events.transition_key` 唯一模型 + `origin_event_id` 外部事件幂等解除（该模型为 B1.6 + B1.7 定稿，不再三选一）。

## 逐聚合权威矩阵

| 聚合 | 当前权威 | 目标权威 | 切换前置条件 |
|---|---|---|---|
| 储值余额（`member_balance.stored_value_fen`） | Platform 本地账本 | Platform 本地账本（`local → local`，**无需切换**） | 与有赞侧（若存在）一致性核对 + 审计 |
| 积分余额（`member_balance.points`） | youzan | local | 积分数据对账通过；事件审计语义确认；灰度观察 |
| 优惠券（`coupon_inventory`） | youzan | local | **有效券基线迁移**；切换水位线；写入围栏；影子读对账；观察期 |
| 会员身份（`member_balance` / `customer_identity_links`） | Platform 本地投影 | Platform 本地投影（**一致性核对，非切换**） | 与有赞身份归属核对一致 |

积分与优惠券**拆为两个独立切换窗口**（先积分窗口、后优惠券窗口，各自完成部署 / 观察 / 回滚后再进入下一个），禁止同窗口同时部署两个 authority 开关；进程级配置全量切换不等同灰度，实例级灰度方案在临近 2027-06 时再评审确定。

### 裁决记录（每个工作包执行前必填）

执行前生成不可变裁决记录，固定：负责人（**project owner**，唯一批准人）、观察期天数、重试上限、RPO / RTO、回滚条件、证据路径。未经裁决记录不得切换权威或开放真实用户。

## 任务清单

### A. 积分切换

1. 数据对账：本地 `member_balance.points` 与有赞 `total` 逐客户核对一致，差异清零或豁免。
2. 事件语义确认：`local` 下有赞 `POINTS` 事件只写 `points_ledger` 审计镜像，不覆盖余额（已实现，需生产复验）。
3. 灰度观察：以进程级开关在低峰窗口切换，观察期天数在执行前裁决记录中固定（项目负责人批准），比对本地余额与有赞变化。

### B. 优惠券切换（新增迁移与围栏）

> **券数据模型以 [ADR 0008](../harness-engineering/adr/0008-accounting-core-consistency.md) 为唯一来源**（B1.6 + B1.7 定稿）：事件表 `coupon_events`（`transition_key` + `ingest_source` + `origin_event_id`）+ 当前态投影 `coupon_current_state`（`RESERVED` 预占 + 投影 CAS）。以下 B.1–B.7 均在该模型下执行；旧 `idx_coupon_inventory_dedup (coupon_id, status, mobile)` 标为**"第一阶段现状，禁止用于新实现"**。

1. **有效券基线迁移**：切换前把现有 `source IN ('import','webhook')` 的有效券行按 ADR 0008 迁移为 `coupon_events` 事件行（`transition_key = legacy:<coupon_inventory.id>`，不伪造外部事件 ID；`ingest_source=legacy`），投影到 `coupon_current_state`；迁移期保留旧表以兼容读取，确保已有有效有赞券不会消失。
2. **兼容读取合同（迁移期）**：旧 `coupon_inventory` 只读、禁写；可用券列表 / 核销判定 / local 权威读取统一走 `coupon_current_state` 投影；旧表仅作迁移核对与回滚底稿。
3. **切换水位线（B1.7 唯一水位）**：以 **`inbox_events.id`** 为唯一切换水位（AUTOINCREMENT 不可变），**不用时间戳、不引入事件派生游标**；水位线之后到达的 `webhook` 券事件按 `local` 语义写入 `coupon_events`，杜绝双写。
4. **写入围栏**：切换后本地写入期间，对有赞券管理端写入做围栏 / 停写确认，避免本地与有赞同时改券导致分裂。
5. **影子读对账**：`local` 权威下继续影子读有赞券，定期对账差异（新增 / 核销 / 退回）。
6. **稳定观察期**：观察期内每日对账，券核销 / 退回 / 到期行为一致，方可推进。
7. **切换 / 回滚合同（固定，不再三选一）**：
   - `transition_key` 精确定义（B1.8）：`sha256(coupon_id + ":" + mobile + ":" + transition_type + ":" + business_ref + ":" + cycle_no + ":" + payment_attempt_id)`（不含来源；`transition_type ∈ {TAKE, RESERVE, RELEASE, CONSUME, BACK, EXPIRE}`，`payment_attempt_id` 仅订单路径携带，`RESERVE` 分配周期、`CONSUME` 复用）；`business_ref` 为 `order:<order_no>` / `refund:<refund_no>` / `take:<外部事件 ID>` / `import:<导入批次 ID>` / `legacy:<coupon_inventory.id>`；`origin_event_id` 须为可跨 import/webhook 对齐的上游稳定 ID，导入批次行 ID 不默认等同 webhook `msg_id`，缺失隔离待对账。
   - 状态迁移表：`初始 → TAKE → RESERVE → RESERVED → RELEASE/TAKE → CONSUME → BACK → TAKE`（多周期）与 `TAKE/RESERVED/CONSUME → EXPIRE`，禁止跳转。
   - 迟到 / 乱序事件：按事件版本合同（`event_version` / `ordering_kind` / `payload_hash`）判定新旧，**禁止以 `(occurred_at, id)` 承担因果语义**（仅作同源展示序）；不可比冲突进入对账队列。
   - 跨来源重复事件：`transition_key` 含来源无关逻辑键（含类型与支付尝试），同一 `transition_key` / 同一可证实对齐的 `origin_event_id` 幂等拒绝，不同来源不再互相占用唯一键位。
   - 切换执行前先产出设计文档（表结构变更、投影查询、迁移批次与停写窗口、roll-forward 补偿规则与回滚条件），未通过该设计评审不得执行切换。

### C. 回滚与补偿

1. **不可逆边界（B1.7 裁决：仅 roll-forward）**：本地权威首次写入后**只允许 roll-forward，不回写有赞**（有赞侧不做反向同步）。回滚验证改为：切换演练验证 roll-forward 补偿——对账差异以本地快照为权威追加修正，被本地修改的数据不反向同步有赞；该不可逆风险列为正式放行的**显式审批项**（见 FP-4B2 Go/No-Go 清单）。
2. 明确 **RPO / RTO**：切换过程允许丢失 / 回补的窗口，由项目负责人在执行前裁决记录中固定数值（不再以示例值代替）并演练。

### D. 收口

1. 二次部署：按两个独立切换窗口分别部署——先 `POINTS_AUTHORITY=local` 窗口（观察通过后再开下一窗口），再 `COUPON_AUTHORITY=local` 窗口；每窗口各自 `/health` `/ready` 与核心 API 回验。
2. **有赞小程序下线**：仅在本工作包及 FP-4 正式发布完成后执行；下线前与有赞运营协调，确认无在途用户。
3. LOGBOOK / 证据索引收口，使用独立 trace_id；M3 / M4 生产部署证据条目一并补齐。

## 验收标准

- 积分与优惠券分别切换，各自对账通过、roll-forward 补偿演练通过。
- 有效券基线迁移后，已有有效券在 `local` 下仍可查询、可核销。
- 切换水位线（唯一 `inbox_events.id`）、写入围栏、影子读对账均有运行记录，观察期无差异漂移。
- 唯一键冲突解除设计（ADR 0008 `coupon_events.transition_key` 唯一模型）在隔离环境验证通过，local 状态可正常写入。
- RPO / RTO 达成并演练；不可逆（仅 roll-forward）风险已列为正式放行显式审批项。
- 有赞小程序下线后，Platform 本地账务域成为唯一数据权威，小程序作为唯一用户入口，无业务中断。

## 边界

- 必须先完成 FP-1（数据正式导入）、FP-3（真实支付）与 FP-4（正式发布），否则不切换权威。
- 权威切换涉及真实资金与券资产，未完成对账 / 演练 / 围栏前，禁止切换。
- 即使上述条件全部满足，也必须取得项目负责人的明确上线批准；2027-06 不等于自动开放真实用户。
