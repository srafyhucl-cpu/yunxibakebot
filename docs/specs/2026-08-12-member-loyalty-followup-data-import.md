# 后续工作包 FP-1：会员数据正式导入

- status: pending
- parent_trace_id: `20260812-member-loyalty-storedvalue`
- 执行时须生成独立 trace_id（如 `2026MMDD-member-loyalty-import`），不得复用父计划 trace
- 所属计划：[2026-08-12-member-loyalty-storedvalue-plan.md](./2026-08-12-member-loyalty-storedvalue-plan.md)（M1 数据底座）
- 阻塞依赖：真实有赞店铺 API / Webhook 契约
- 拆分来源：2026-08-14 M1–M6 完整评审（方案 B 分阶段结项）；2026-08-14 深度复核修正

## 背景

M1 已完成 v021 三表迁移与 Webhook 会员路由部署（生产 v0.111.0，ecffa3b）。`scripts/import_member_loyalty.py` 已具备 dry-run / apply / limit / JSON 报告能力，但生产正式全量导入尚未执行，真实店铺 API / Webhook 契约未联调。

## 当前实现事实（复核修正）

- 脚本**不存在** `--dry-run` 参数；**不传 `--apply` 即只查询不写入**（dry-run）。
- 实际写入目标：`member_balance`（积分余额快照、会员卡）、`coupon_inventory`（券库存）、`coupon_templates`（券模板）；**不写** `points_ledger`（由 Webhook 增量维护）。
- 脚本缺陷：单客户失败仅计入 `failed`，最终仍返回退出码 `0`，部分失败可能被误判为成功。**执行 apply 前必须先完成脚本增强（阶段一）。**

## 阶段一：脚本增强（先于任何 apply）

1. `failed > 0` 时进程以非 0 退出码结束，并把 failed 明细写入 JSON 报告。
2. apply 阶段强制生成 JSON 报告（`--json --output`），报告元数据含 `batch_id`（时间戳 + 随机后缀），禁止只打控制台。
3. 限流退避：有赞 API 429 / 限流时按 Retry-After 退避重试，配置重试上限。
4. 断点续跑：以 customer 主档为断点（记录已处理游标），中断后可续跑，不重复处理已成功客户。
5. 失败重试：单客户失败进入 retry 队列，收尾统一重试（上限 N 次）。
6. 备份与恢复：apply 前先做 SQLite 备份并校验；执行备份恢复 round-trip 演练，通过后视为可恢复。
7. 回归：上述增强配合同级单元 / 脚本测试，`ruff` / `check_project --skip-tests` 门禁通过。

## 阶段二：真实店铺契约联调

1. 受控小批 dry-run：`python scripts/import_member_loyalty.py --limit 20`（不传 `--apply`），核对积分 / 券 / 会员卡字段契约。
2. 真实券字段解析：核对 `parse_youzan_template` / `extract_template_fields` 对真实有赞响应的折扣、券类型、有效期字段；修复**非数值折扣解析健壮性**（承接 M4 评审遗留 #4）。
3. 契约核对通过后，方进入全量 apply。

## 阶段三：生产全量导入与核对

1. 全量执行：`python scripts/import_member_loyalty.py --apply --json --output "reports/import/member-loyalty-{timestamp}.json"`。
2. eligible population 界定：以 `customer_master` 中具备 `primary_phone` 的主档为导入范围（含授权测试账号），报告中明确 `total_eligible / 已导入 / 无手机号跳过 / 豁免`，作为验收基线。
3. 核对：导入数量与 eligible population 一致、幂等无重复、余额快照正确、`failed=0` 且退出码为 0。
4. Webhook 起止双水位：导入开始前记录 `start_watermark`，结束后记录 `end_watermark`；`[start, end]` 窗口内到达的真实 `POINTS` / `COUPON_CUSTOMER_PROMOTION` / `SCRM_CUSTOMER_CARD` / `SCRM_CUSTOMER_EVENT` 事件必须回放或补拉核对，防止旧快照覆盖新事件。
5. 导入期间若增量处理暂停，恢复时必须先回放水位线窗口内事件再继续（禁止无回放的直接续跑）。
6. 四类事件验收：`POINTS`（余额/流水一致）、`COUPON_CUSTOMER_PROMOTION`（券库存/状态一致）、`SCRM_CUSTOMER_CARD`（会员卡状态）、`SCRM_CUSTOMER_EVENT`（身份归属）各自核对通过。

## 验收标准

- 脚本增强通过（`failed>0` 非 0 退出、JSON 报告必带 `batch_id`、限流退避 / 断点续跑 / 失败重试有测试）。
- dry-run 与全量 apply 报告 `failed=0`，导入数量与 eligible population 一致，幂等无重复，四类事件验收全部通过。
- eligible population 界定明确；起止双水位校验通过，水位线窗口内事件回放无漏单、无重复。
- coupon_templates 同步校验：模板数量、字段（折扣 / 类型 / 有效期）与 `coupon_inventory.template_id` 关联一致。
- 备份与恢复 round-trip 演练通过。
- LOGBOOK / 证据索引收口，使用独立 trace_id。

## 边界

- 不导入积分明细流水（由 Webhook 增量维护），只落余额快照、券库存与券模板（`member_balance` / `coupon_inventory` / `coupon_templates`），避免导入快照污染明细。
- 导入涉及生产数据：未完成阶段一脚本增强、未通过备份恢复演练前，禁止执行 apply。
