# 后续工作包 FP-2：本地权威切换（2027-06）

- status: pending
- parent_trace_id: `20260812-member-loyalty-storedvalue`
- 执行时须生成独立 trace_id（如 `2027MMDD-member-loyalty-local-authority`），不得复用父计划 trace
- 决策依据：[ADR 0007](../harness-engineering/adr/0007-local-authority-cutover.md)
- 所属计划：[2026-08-12-member-loyalty-storedvalue-plan.md](./2026-08-12-member-loyalty-storedvalue-plan.md)（M3 积分 / M4 优惠券第二阶段）
- 执行时点：2027-06
- 前置依赖：FP-1（会员数据正式导入）、FP-3（真实微信支付）、FP-4（小程序正式发布）全部完成
- 拆分来源：2026-08-14 M1–M6 完整评审（方案 B 分阶段结项）；2026-08-14 深度复核修正

## 背景与决策

M3 与 M4 第一阶段已上线 `POINTS_AUTHORITY=youzan`、`COUPON_AUTHORITY=youzan`（有赞维护余额 / 券库存）。第二阶段目标：切换为 `local`，本小程序替代有赞小程序成为权威，切换完成后关停有赞小程序。决策详见 ADR 0007。

## 当前实现事实（复核修正）

- `POINTS_AUTHORITY` / `COUPON_AUTHORITY` 均为**进程级配置**（`app/config.py`），不支持"受控范围灰度"到单客户 / 单店铺。
- 积分 `local`：`event_member.py` 在 `POINTS_AUTHORITY != "local"` 时用有赞 `total` 覆盖 `member_balance.points`；`local` 时只写流水 / 审计镜像（已实现）。
- 优惠券 `local`：`coupon_inventory_repo` 在 `authority=local` 时**只识别 `source IN ('order','local')` 的券行**，现有 `import` / `webhook` 来源的有效券行会被过滤，导致已有有效有赞券从可用列表消失。
- 本地写入后不能仅靠改回环境变量实现无损回滚（已落库数据不会自动回退）。

## 逐聚合权威矩阵

| 聚合 | 当前权威 | 目标权威 | 切换前置条件 |
|---|---|---|---|
| 积分余额（`member_balance.points`） | youzan | local | 积分数据对账通过；事件审计语义确认；灰度观察 |
| 优惠券（`coupon_inventory`） | youzan | local | **有效券基线迁移**；切换水位线；写入围栏；影子读对账；观察期 |
| 会员卡 / 身份（`member_balance`） | youzan | local | 随积分/券切换完成身份归属核对 |

积分与优惠券**分别切换**，各自完成对账与回滚演练，禁止一次性切换全部聚合。

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

### C. 回滚与补偿

1. 回滚验证：本地写入后可回滚到 `youzan`（需定义补偿机制——被本地修改的数据如何反向同步到有赞，或接受差异并记录）。
2. 明确 **RPO / RTO**：切换过程允许丢失 / 回补的窗口（如 RPO=5 分钟、RTO=30 分钟），执行前书面确认并演练。

### D. 收口

1. 二次部署：`POINTS_AUTHORITY=local` + `COUPON_AUTHORITY=local` 全量部署，`/health` `/ready` 与核心 API 回验。
2. **有赞小程序下线**：仅在本工作包及 FP-4 正式发布完成后执行；下线前与有赞运营协调，确认无在途用户。
3. LOGBOOK / 证据索引收口，使用独立 trace_id；M3 / M4 生产部署证据条目一并补齐。

## 验收标准

- 积分与优惠券分别切换，各自对账通过、回滚演练通过。
- 有效券基线迁移后，已有有效券在 `local` 下仍可查询、可核销。
- 切换水位线、写入围栏、影子读对账均有运行记录，观察期无差异漂移。
- RPO / RTO 达成并演练。
- 有赞小程序下线后，本小程序为唯一权威，无业务中断。

## 边界

- 必须先完成 FP-1（数据正式导入）、FP-3（真实支付）与 FP-4（正式发布），否则不切换权威。
- 权威切换涉及真实资金与券资产，未完成对账 / 演练 / 围栏前，禁止切换。
