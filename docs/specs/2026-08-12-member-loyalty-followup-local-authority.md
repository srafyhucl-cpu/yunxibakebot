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
- **唯一键冲突（切换模型阻断项）**：`coupon_inventory` 唯一索引 `idx_coupon_inventory_dedup (coupon_id, status, mobile)`（v024:66）不含 `source`。webhook 来源券行已占用 `(coupon_id, status, mobile)` 键位后，local 状态无法再写入同状态行；`source IN ('order','local')` 过滤叠加唯一键独占，使切换模型在无补偿设计下不可执行，须按 B.6 解除。

## 逐聚合权威矩阵

| 聚合 | 当前权威 | 目标权威 | 切换前置条件 |
|---|---|---|---|
| 积分余额（`member_balance.points`） | youzan | local | 积分数据对账通过；事件审计语义确认；灰度观察 |
| 优惠券（`coupon_inventory`） | youzan | local | **有效券基线迁移**；切换水位线；写入围栏；影子读对账；观察期 |
| 会员卡 / 身份（`member_balance`） | youzan | local | 随积分/券切换完成身份归属核对 |

积分与优惠券**拆为两个独立切换窗口**（先积分窗口、后优惠券窗口，各自完成部署 / 观察 / 回滚后再进入下一个），禁止同窗口同时部署两个 authority 开关；进程级配置全量切换不等同灰度，实例级灰度方案在临近 2027-06 时再评审确定。

## 任务清单

### A. 积分切换

1. 数据对账：本地 `member_balance.points` 与有赞 `total` 逐客户核对一致，差异清零或豁免。
2. 事件语义确认：`local` 下有赞 `POINTS` 事件只写 `points_ledger` 审计镜像，不覆盖余额（已实现，需生产复验）。
3. 灰度观察：以进程级开关在低峰窗口切换并观察 ≥ N 天，比对本地余额与有赞变化。

### B. 优惠券切换（新增迁移与围栏）

1. **有效券基线迁移**：切换前把现有 `source IN ('import','webhook')` 的有效券行迁移 / 重写为 `local` 来源（或引入兼容读取），确保已有有效有赞券不会消失。
2. **切换水位线**：记录迁移完成时刻为水位线；水位线之后到达的 `webhook` 券事件按 `local` 语义处理，杜绝双写。
3. **写入围栏**：切换后本地写入期间，对有赞券管理端写入做围栏 / 停写确认，避免本地与有赞同时改券导致分裂。
4. **影子读对账**：`local` 权威下继续影子读有赞券，定期对账差异（新增 / 核销 / 退回）。
5. **稳定观察期**：观察期内每日对账，券核销 / 退回 / 到期行为一致，方可推进。
6. **唯一键冲突解除设计（必须项）**：为 local 状态写入提供 authority epoch / shadow audit / 状态投影之一：
   - authority epoch：为券记录增加切换纪元标记，local 行与 webhook 行按纪元区分，不共享同一去重键；
   - shadow audit：webhook 行改写为审计 / 影子行（不同状态语义），本地状态用独立键位写入；
   - 状态投影：按 `coupon_id + mobile` 投影最新状态，弱化 `(coupon_id, status, mobile)` 唯一键对写入的限制。
   该设计必须先隔离环境验证，再进入迁移。
7. **设计门禁（执行前必须完成，不属于当前定稿）**：FP-2 正式执行前，必须从上述三选一中选定具体模型，并产出设计文档，写清：表结构变更（schema / 迁移）、最新态查询投影、迁移批次与停写窗口、回滚条件与补偿 SQL。未通过该设计评审不得执行切换；本工作包当前仅记录风险与候选方案。

### C. 回滚与补偿

1. 回滚验证：本地写入后可回滚到 `youzan`（需定义补偿机制——被本地修改的数据如何反向同步到有赞，或接受差异并记录）。
2. 明确 **RPO / RTO**：切换过程允许丢失 / 回补的窗口（如 RPO=5 分钟、RTO=30 分钟），执行前书面确认并演练。

### D. 收口

1. 二次部署：按两个独立切换窗口分别部署——先 `POINTS_AUTHORITY=local` 窗口（观察通过后再开下一窗口），再 `COUPON_AUTHORITY=local` 窗口；每窗口各自 `/health` `/ready` 与核心 API 回验。
2. **有赞小程序下线**：仅在本工作包及 FP-4 正式发布完成后执行；下线前与有赞运营协调，确认无在途用户。
3. LOGBOOK / 证据索引收口，使用独立 trace_id；M3 / M4 生产部署证据条目一并补齐。

## 验收标准

- 积分与优惠券分别切换，各自对账通过、回滚演练通过。
- 有效券基线迁移后，已有有效券在 `local` 下仍可查询、可核销。
- 切换水位线、写入围栏、影子读对账均有运行记录，观察期无差异漂移。
- 唯一键冲突解除设计（authority epoch / shadow audit / 状态投影）在隔离环境验证通过，local 状态可正常写入。
- RPO / RTO 达成并演练。
- 有赞小程序下线后，本小程序为唯一权威，无业务中断。

## 边界

- 必须先完成 FP-1（数据正式导入）、FP-3（真实支付）与 FP-4（正式发布），否则不切换权威。
- 权威切换涉及真实资金与券资产，未完成对账 / 演练 / 围栏前，禁止切换。
- 即使上述条件全部满足，也必须取得项目负责人的明确上线批准；2027-06 不等于自动开放真实用户。
