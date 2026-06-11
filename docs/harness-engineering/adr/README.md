# Architecture Decision Records

本目录记录会影响项目长期演进的架构决策。ADR 的作用不是写长论文，而是让后续 AI Agent 和人工开发者能快速知道：为什么当时这么选、替代方案是什么、后续什么条件下可以重新评估。

______________________________________________________________________

## 何时需要 ADR

- 改变分层边界、数据流、部署方式、上线流程或 Harness 机制。
- 引入或移除关键依赖。
- 修改会影响多个模块的运行时行为。
- 用户或 AI 已经围绕同一问题反复讨论，后续容易“重走一遍”。
- 决策会影响生产同步、数据安全、可观测性或恢复流程。

______________________________________________________________________

## 命名规则

```text
NNNN-short-title.md
```

示例：

```text
0001-traceable-memory-harness.md
```

______________________________________________________________________

## 状态

| 状态 | 说明 |
|---|---|
| proposed | 已提出，尚未执行 |
| accepted | 当前采用 |
| superseded | 已被后续 ADR 替代 |
| rejected | 明确不采用 |

______________________________________________________________________

## 模板

```markdown
# ADR NNNN：标题

- status: proposed | accepted | superseded | rejected
- date: YYYY-MM-DD
- trace_id:
- decision_owner:
- related_docs:

## Context

背景、约束、现有问题。

## Decision

明确采用的方案。

## Alternatives

- 方案 A：优点 / 缺点
- 方案 B：优点 / 缺点

## Consequences

- 正向影响
- 负向影响
- 后续需要补的 Harness、测试或文档

## Verification

- 如何证明该决策被正确落地
```

