# 后续工作包 FP-5：技术债承接

- status: pending
- parent_trace_id: `20260812-member-loyalty-storedvalue`
- 执行时须生成独立 trace_id（如 `2026MMDD-member-loyalty-techdebt`），不得复用父计划 trace
- 所属计划：[2026-08-12-member-loyalty-storedvalue-plan.md](./2026-08-12-member-loyalty-storedvalue-plan.md)
- 拆分来源：2026-08-14 深度复核——原拆分未承接全部已知技术债

## 背景

会员账务域评审与执行中累积的技术债未全部被 FP-1 / FP-3 承接。复核后明确归属：券 `BACK` 退款接入 → FP-3；真实券字段 / 非数值折扣解析 → FP-1；以下两项由本工作包承接。

## 承接范围

1. **仓储返回类型注解**（M4 评审遗留 #5）：补全仓储方法返回类型注解，消除 `Optional[X]` 禁令的例外与不完整标注，纳入 `mypy` 门禁。
2. **tests/scripts 覆盖率 flaky**：`tests/scripts` 目录覆盖率不稳定（M4 评审遗留），定位 flaky 来源并固定，恢复稳定覆盖率基线。

## 任务清单

1. 盘点仓储返回类型标注缺口，逐个补齐，`mypy` 通过。
2. 定位 `tests/scripts` 覆盖率抖动根因（如顺序依赖 / 随机时序 / 环境变量污染），修复并加并发隔离。
3. 建立覆盖率稳定性断言，连续 N 次运行无抖动。
4. LOGBOOK / 证据索引收口，使用独立 trace_id。

## 验收标准

- 仓储返回类型注解完整，`mypy` 门禁无新增豁免。
- `tests/scripts` 覆盖率连续稳定运行通过。
- 无运行时行为变更（纯类型与测试工程）。

## 边界

- 本工作包不引入业务行为变更；若发现类型注解缺口暴露运行时缺陷，转入对应功能工作包处理。
