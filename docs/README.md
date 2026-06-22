# 文档导航

本目录同时包含当前设计文档、历史方案、评估报告和 Harness 证据入口。为避免把历史材料误读成当前架构，请优先按下面顺序阅读。

## 当前权威口径

除非你是在回顾历史决策，否则当前实施、迁移和双仓协作都应从本节进入；下方“历史方案”和“业务与技术背景”只用于参考，不作为执行起点。

- `README.md`
  - 产品命名、仓角色、启动方式和总入口说明。
- `docs/architecture/project-boundaries.md`
  - 当前 `Platform` / `Storefront MiniApp` 边界与 canonical 领域职责。
- `docs/architecture/platform-miniapp-api-contract-v1.md`
  - 当前双仓对接的 API 契约基线，明确 MiniApp 应消费哪些公开接口以及背后 canonical 归属域。
- `docs/architecture/platform-domain-migration-inventory.md`
  - 当前 `Platform` 内部从历史 `miniapp_*` 命名继续迁到 canonical 领域的盘点、风险分级和建议执行批次。
- `docs/architecture/customer-group-operations-phase1.md`
  - 当前客户群运营一期说明，覆盖客户群触达、小程序结构化登记、后台汇总和微信客服单聊承接的最小闭环。
- `docs/architecture/customer-master-v1.md`
  - 当前客户主档 v1 设计基线，明确主档、身份链接、来源快照三层结构，以及有赞迁移审计落点。
- `docs/architecture/customer-master-v1-schema-draft.md`
  - 当前客户主档 v1 四表 schema 草案，明确 `customer_master / customer_identity_links / customer_source_snapshots / customer_merge_reviews` 的字段、索引、唯一约束和 `pending_review` 闭环。
- `docs/architecture/youzan-customer-migration-audit-checklist.md`
  - 当前有赞客户迁移审计清单，明确输入、标准化规则、风险分级、输出表头和分流规则。
- `docs/architecture/youzan-customer-formal-import-runbook.md`
  - 当前有赞客户正式迁移执行 runbook，明确审计、dry-run、apply、报告留档和重跑语义。
- `scripts/verify_youzan_customer_import.py`
  - 当前有赞客户迁移后核对脚本，按批次核对快照、主档、身份与复核汇总，可选对比正式导入报告。
- `docs/architecture/youzan-customer-import-handoff-and-rollback-runbook.md`
  - 当前有赞客户迁移交接与回滚 runbook，明确异常中止、交接证据、同批次重跑和恢复优先级。
- `scripts/import_youzan_customers.py`
  - 当前有赞客户正式迁移入口；默认 dry-run，显式 `--apply` 才写库。
- `项目进度与配置清单.md`
  - 当前进度、生产同步检查和阶段记录。
- `docs/api-spec.md`
  - 高层接口总览；真实契约仍以运行中的 OpenAPI 为准。

## 历史方案

- `docs/architecture/two-repo-rollout-plan.md`
  - 双仓推进节奏的历史路线图，只用于回顾过渡思路。
- `docs/architecture/miniapp-phase1-execution-checklist.md`
  - `Storefront MiniApp` 第一阶段边界对齐清单，只保留历史过渡记录。
- `docs/architecture/miniapp-ai-handoff-plan.md`
  - 发给 `MiniApp` 仓 AI 的过渡阶段执行说明，只作为历史参考。

## 业务与技术背景

- `docs/design/`
  - 保存业务方案、工作流、技术架构和升级设计。
  - 这些文档大多保留了早期阶段表达；如与当前代码边界冲突，以 `docs/architecture/project-boundaries.md` 为准。

## Harness 与证据

- `docs/harness-engineering/README.md`
  - Harness Engineering 总入口。
- `docs/harness-engineering/adr/0002-platform-storefront-boundaries-and-instance-naming.md`
  - 固化逻辑总项目、双仓边界和 `Yunxi` 实例名定位的长期决策。
- `docs/harness-engineering/core/evidence-index.md`
  - 历史证据索引，只做追溯，不作为当前架构口径来源。

## 历史评估与报告

- `docs/评估报告.md`
- `docs/HarnessEngineering评估报告_20260604.md`
- `docs/VibeCoding可持续性评估报告_20260604.md`

这些文档反映的是各自时间点的判断，适合回顾，不应直接当作当前设计结论。
