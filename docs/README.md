# 文档导航

本目录同时包含当前设计文档、历史方案、评估报告和 Harness 证据入口。为避免把历史材料误读成当前架构，请优先按下面顺序阅读。

## 当前权威口径

- `README.md`
  - 产品命名、仓角色、启动方式和总入口说明。
- `docs/architecture/project-boundaries.md`
  - 当前 `Platform` / `Storefront MiniApp` 边界与 canonical 领域职责。
- `docs/architecture/platform-miniapp-api-contract-v1.md`
  - 当前双仓对接的 API 契约基线，明确 MiniApp 应消费哪些公开接口以及背后 canonical 归属域。
- `docs/architecture/customer-master-v1.md`
  - 当前客户主档 v1 设计基线，明确主档、身份链接、来源快照三层结构，以及有赞迁移审计落点。
- `docs/architecture/youzan-customer-migration-audit-checklist.md`
  - 当前有赞客户迁移审计清单，明确输入、标准化规则、风险分级、输出表头和分流规则。
- `项目进度与配置清单.md`
  - 当前进度、生产同步检查和阶段记录。
- `docs/api-spec.md`
  - 高层接口总览；真实契约仍以运行中的 OpenAPI 为准。

## 当前设计与过渡方案

- `docs/architecture/two-repo-rollout-plan.md`
  - 双仓推进节奏的历史路线图，当前主要用来解释过渡思路。
- `docs/architecture/miniapp-phase1-execution-checklist.md`
  - `Storefront MiniApp` 第一阶段边界对齐清单，属于历史过渡文档。
- `docs/architecture/miniapp-ai-handoff-plan.md`
  - 发给 `MiniApp` 仓 AI 的过渡阶段执行说明。

## 业务与技术背景

- `docs/design/`
  - 保存业务方案、工作流、技术架构和升级设计。
  - 这些文档大多保留了早期阶段表达；如与当前代码边界冲突，以 `docs/architecture/project-boundaries.md` 为准。

## Harness 与证据

- `docs/harness-engineering/README.md`
  - Harness Engineering 总入口。
- `docs/harness-engineering/core/evidence-index.md`
  - 历史证据索引，只做追溯，不作为当前架构口径来源。

## 历史评估与报告

- `docs/评估报告.md`
- `docs/HarnessEngineering评估报告_20260604.md`
- `docs/VibeCoding可持续性评估报告_20260604.md`

这些文档反映的是各自时间点的判断，适合回顾，不应直接当作当前设计结论。
