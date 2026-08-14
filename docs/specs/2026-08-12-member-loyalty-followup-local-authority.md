# 后续工作包 FP-2：本地权威切换（2027-06）

- 状态：🔴 待执行
- 所属计划：[2026-08-12-member-loyalty-storedvalue-plan.md](./2026-08-12-member-loyalty-storedvalue-plan.md)（M3 积分 / M4 优惠券第二阶段）
- trace_id：`20260812-member-loyalty-storedvalue`
- 执行时点：2027-06
- 决策背景：以本小程序替代有赞小程序，`local` 权威切换为既定决策，需按计划执行
- 拆分来源：2026-08-14 M1–M6 完整评审（方案 B 分阶段结项）

## 背景

M3 与 M4 第一阶段已上线 `POINTS_AUTHORITY=youzan`、`COUPON_AUTHORITY=youzan`（有赞 `total` / 券库存继续维护）。按原计划，第二阶段需切换为 `local`，由本地 `member_balance` / `coupon_inventory` 作为权威。

## 目标

将 `POINTS_AUTHORITY` / `COUPON_AUTHORITY` 切换为 `local`，本小程序替代有赞小程序成为会员余额、积分、券库存的唯一权威，替代完成后关停有赞小程序对外服务。

## 任务清单

1. 数据对账：本地 `member_balance` / `coupon_inventory` 与有赞 `total` / 券库存逐项核对一致。
2. 灰度切换：先在受控范围切 `local`，观察余额、积分、券核销行为。
3. 回滚验证：确认切换后若异常可一键回滚 `youzan`，验证回滚路径可用。
4. 二次部署：`POINTS_AUTHORITY=local` + `COUPON_AUTHORITY=local` 全量部署。
5. 事件语义确认：`local` 下有赞 `POINTS` / 券事件只写流水 / 审计镜像，不再覆盖余额与券库存。
6. 有赞小程序下线：确认本地权威稳定后，关停有赞小程序对外服务。
7. LOGBOOK / 证据索引收口。

## 验收标准

- 切换后本地余额、积分、券库存与有赞源一致（对账通过）。
- `local` 权威下事件仅写审计，不覆盖余额 / 券库存。
- 灰度与回滚演练通过，无数据不一致或重复入账。

## 边界

- 切换前必须先完成 FP-1（会员数据正式导入）与 FP-3（真实微信支付）验证，避免在未验证链路上切换权威。
- 有赞侧余额 / 券数据的停更与下线需与有赞运营协调，避免双写冲突。
