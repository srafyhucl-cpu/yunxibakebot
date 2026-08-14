# 后续工作包 FP-1：会员数据正式导入

- 状态：🔴 待执行
- 所属计划：[2026-08-12-member-loyalty-storedvalue-plan.md](./2026-08-12-member-loyalty-storedvalue-plan.md)（M1 数据底座）
- trace_id：`20260812-member-loyalty-storedvalue`
- 阻塞依赖：真实有赞店铺 API / Webhook 契约
- 拆分来源：2026-08-14 M1–M6 完整评审（方案 B 分阶段结项）

## 背景

M1 已完成 v021 三表迁移与 Webhook 会员路由部署（生产 v0.111.0，ecffa3b），但 `scripts/import_member_loyalty.py --apply` 的正式全量导入尚未执行，真实店铺 API / Webhook 契约联调待完成。

## 目标

调用真实有赞店铺 API 执行全量导入，确认积分、券、会员卡字段契约，落地打底数据，并由 Webhook 增量维持。

## 任务清单

1. 受控小批 dry-run：`scripts/import_member_loyalty.py --dry-run --limit N`，核对积分 / 券 / 会员卡字段契约。
2. 核对导入字段与目标表结构一致（`points_ledger` / `coupon_inventory` / `member_balance`）。
3. 全量执行：`scripts/import_member_loyalty.py --apply`。
4. 核对：导入数量与有赞源一致、幂等无重复、余额快照正确。
5. 增量验证：真实 `POINTS` / `COUPON_CUSTOMER_PROMOTION` 事件触发后 ledger / inventory 正确更新。
6. LOGBOOK / 证据索引收口。

## 验收标准

- 导入数量与有赞源一致，无重复、无孤儿。
- 幂等重跑不产生重复数据。
- 增量 Webhook 事件正确维持余额与券库存。

## 边界

- 不导入积分明细流水（由 Webhook 增量维护），只落余额快照与券库存，避免导入快照污染明细。
- 导入涉及生产数据，执行前需备份并确认回滚路径。
