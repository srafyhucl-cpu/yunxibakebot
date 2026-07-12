# 全局风险整改当前列车完成审计

- trace_id: `20260711-global-risk-remediation`
- audited_at: 2026-07-12
- audited_commit: `c4a100ceaf7fd917d304ba2f397dfeab1dc1c60b`
- production_version: `0.109.5`
- decision: 当前 systemd 生产列车完成；Docker 真实验证按用户决定后置，主目标保持 active。

## 完成定义核对

| 完成定义 | 当前证据 | 结论 |
|---|---|---|
| P0 攻击链与 PII 快照风险关闭 | 攻击链负向测试、订单归属/定价/支付合同、安全快照白名单测试均进入 1303 项全量套件；生产入口与配置门禁已发布 | pass |
| 标准测试、CI、readiness、部署、迁移和恢复可重复 | 当前 HEAD 全量 `1303/1303`；Quality Gate 通过；生产 health/ready；migration dry-run/apply/rollback staging；本地加密备份任务结果 0 | pass |
| 订单事务与消息幂等依赖数据库原子语义，崩溃可恢复 | UoW 故障注入、原子 message claim、inbox lease 测试；生产合成 inbox processing kill/reclaim `8/8` | pass |
| consent、撤回、删除、TTL 和外发脱敏闭环 | 隐私聚合生产门禁 `8/8`；生产合成主体真实 JWT/API 删除 `8/8`；最终零残留 | pass |
| AI 应用层只有 LangChain/LangGraph 默认路径 | 模型入口自动发现 9 个，统一共享 factory/脱敏；旧文本 facade 归零，OpenAI SDK 仅保留 ASR 窄适配 | pass |
| 模型 client/compiled graph 复用，trace 进入真实 sink | LangChain运行时版本与容量门禁通过；本地受控 trace sink 已在生产验证，LangSmith外发保持关闭 | pass |
| L3-L5 证据和文档可追溯 | evidence index、LOGBOOK、ADR 0005/0006、主计划和本报告共用 trace_id；本地/GitHub/生产 SHA 同步 | pass |

## 当前生产复验

- systemd active，`/health` 与 `/ready` 均为 `0.109.5`。
- 隐私出站 `8/8`，外部离线路径和 LangSmith关闭。
- 安全出站 `10/10`，员工服务端授权配置 ready。
- LangChain生产版本和容量门禁通过。
- callback `61/61`，failed=0；报告未落盘，不在本证据中保存业务回复正文。
- Windows 加密备份任务 Ready，最近 `LastTaskResult=0`，下一次 03:30；D 盘现有 4 份 `.ybak`。

## 后置项

Docker 真实 build、漏洞扫描和容器 health/smoke 尚未执行。用户已明确 Docker 暂后置，因此它不阻断当前 systemd 生产列车，但仍阻止把整个长期目标标记为 complete。后续恢复该项时必须使用可用 Docker 环境执行真实验证，静态容器合同不能替代。

## 敏感数据边界

本报告只记录版本、计数、布尔状态和证据引用，不包含客户内容、订单明细、员工/群/企业 ID、JWT、callback token、AES key、备份密钥或数据库内容。
