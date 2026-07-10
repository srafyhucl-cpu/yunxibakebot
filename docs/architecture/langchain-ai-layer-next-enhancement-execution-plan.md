# LangChain AI 应用层后续增强可执行计划书

> trace_id: `20260709-langchain-ai-layer-production-enhancement`
> 日期：2026-07-10
> 状态：待执行
> 上游计划：[LangChain AI 应用层生产增强计划书](./langchain-ai-layer-production-enhancement-plan.md)

## 一、目标

本计划承接 LangChain / LangGraph AI 应用层接管后的剩余增强工作，不再讨论是否迁移框架，而是把现有成果推进到可长期维护、可生产观测、可灰度、可作品集展示的状态。

核心目标：

```text
把当前 LangChain AI 应用层从“已接管、可运行”推进到“真实数据可评估、线上效果可观测、RAG 可灰度、发布证据可复盘”。
```

## 二、当前已收口基线

截至 `0.105.13`：

1. 客户机器人主编排已由 LangGraph 接管。
2. 员工助手主编排已由 LangGraph 接管。
3. LangChain tool、retriever adapter、structured planner fallback、trace 报告、release gate 和生产证据包已落地。
4. 生产 `/opt/yunxibakebot` 已部署 `0.105.13`，严格发布证据包已通过，`packet_ready=true`。
5. 真实脱敏样本仍未接入，`candidate_ready=false`、`real_sample_ready=false` 仍是正确状态。
6. LangSmith 生产外发仍未启用，`langsmith_enabled=false` 仍是正确状态。
7. RAG 生产默认模式仍为 `hybrid`；`planned-hybrid` 只能作为受控灰度候选，`planned-hybrid+rerank` 继续 shadow-only。

## 三、执行原则

1. LangChain / LangGraph 继续负责模型调用、工具绑定、Agent 编排、retriever adapter、structured output、trace 和 eval。
2. 业务事实继续由 service / repository / models 管理，不让 LangChain 直接接管订单、库存、退款、客户主档或知识发布状态。
3. 所有真实客户样本必须先脱敏、审核、证明来源，不能用合成样本冒充真实样本。
4. 所有生产灰度必须先有只读证据，再有小流量开关，最后才允许扩大。
5. 所有发布收口必须能通过 LOGBOOK、evidence index、release gate JSON 和证据包追溯。

## 四、阶段 E0：P22a 生产证据基线复核

### 目标

确认当前 `0.105.13` 生产发布证据已经收口，后续增强从干净基线开始。

### 当前状态

已完成：

```text
production commit=29b4822ec9fa5cafea9dd88ea559bb0df9042f3c
runtime VERSION=0.105.13
service=active
packet_ready=true
```

### 复核命令

```powershell
git status -sb
git rev-parse master origin/master server/master
python scripts\check_langchain_production_runtime_version.py --summary
python scripts\build_langchain_release_evidence_packet.py --require-production-evidence --summary
python scripts\check_evidence_index.py --summary
```

### 完成标准

1. 本地、`origin/master`、`server/master` 指向同一 commit。
2. 生产 runtime version 等于本地 `VERSION`。
3. 严格发布证据包通过，`packet_ready=true`。
4. evidence index 结构检查通过。

## 五、阶段 E1：P17b 首批真实脱敏样本接入

### 目标

把真实客服会话从仓库外脱敏输入推进到 replay candidate，通过准入审计后进入真实样本池。

### 前置条件

1. 必须有仓库外真实客服记录持有人提供的脱敏 JSON / JSONL。
2. 每条样本必须声明来源类型、脱敏方法、审核人、审核时间、原始来源不入仓。
3. 不允许提交原始客户消息、手机号、地址、open_id、完整订单号。

### 输入合同

候选 fixture 至少包含：

```text
metadata.source_type
metadata.redaction_method
metadata.reviewed_by
metadata.reviewed_at
metadata.raw_source_retained_outside_repo
cases[].case_id
cases[].messages
cases[].expected
cases[].sensitive_scenario
```

### 执行步骤

1. 使用 `scripts\build_real_conversation_replay_intake_packet.py --summary` 生成外部接入说明。
2. 把仓库外脱敏输入放到用户指定的非仓库目录。
3. 运行候选准入审计，只生成报告和 manifest draft，不直接改 manifest。
4. 人工复核审计报告。
5. 通过后再把 manifest entry 写入真实 replay pool。
6. 跑 real replay、coverage、pool 和 release gate。

### 验收命令

```powershell
python scripts\build_real_conversation_replay_intake_packet.py --summary
python scripts\audit_real_conversation_replay_candidate.py --fixture <redacted-fixture-path> --require-fixture --summary
python scripts\prepare_real_conversation_replay_pool_entry.py --fixture <redacted-fixture-path> --summary
python scripts\check_real_conversation_replay.py --fixture <redacted-fixture-path> --summary
python scripts\check_real_conversation_replay_coverage.py --fixture <redacted-fixture-path> --summary
python scripts\check_real_conversation_replay_pool.py --require-real --summary
python scripts\report_agent_eval.py --latest --include-real-replay --summary
```

### 完成标准

1. `candidate_ready=true` 只在真实脱敏候选输入存在且审计通过后出现。
2. `real_sample_ready=true` 只在真实样本池 manifest 满足准入要求后出现。
3. eval 报告能展示真实 replay 样本数量、覆盖场景和失败定位。
4. LOGBOOK 和 evidence index 记录真实样本只含脱敏数据，不含敏感原文。

### 回滚策略

若发现样本来源或脱敏证明不完整：

1. 不写入真实样本池 manifest。
2. 保持 `candidate_ready=false` 或 `real_sample_ready=false`。
3. 只保留审计失败摘要，不提交敏感样本内容。

## 六、阶段 E2：真实 RAG Shadow Log 接入

### 目标

用真实脱敏用户检索日志评估 `hybrid`、`planned-hybrid`、`planned-hybrid+rerank` 的线上候选差异，避免只靠 golden cases 决策。

### 前置条件

1. 仓库外提供脱敏 RAG shadow log。
2. 默认不输出 query 原文。
3. `metadata.contains_sensitive_data=false` 必须为真。

### 输入合同

```text
metadata.source_type
metadata.contains_sensitive_data
records[].id
records[].query
records[].baseline_top_keys
records[].group
```

### 执行步骤

1. 用默认模式确认当前没有真实输入时仍明确 `shadow_log_ready=false`。
2. 接入仓库外脱敏 shadow log。
3. 运行严格模式，复算 planned / rerank 候选差异。
4. 输出按 group 的 changed cases、recall delta、排序差异。
5. 给出是否允许 E3 灰度的机器结论。

### 验收命令

```powershell
python scripts\report_rag_shadow_log_observability.py --summary
python scripts\report_rag_shadow_log_observability.py --input <redacted-shadow-log-path> --require-input --summary
python scripts\report_rag_shadow_log_observability.py --input <redacted-shadow-log-path> --require-input --json-out reports\retrieval-shadow\rag-shadow-log-latest.json
python scripts\check_langchain_ai_layer_production_plan.py --summary
```

### 完成标准

1. 严格模式在真实脱敏输入存在时通过。
2. 报告默认只输出 `query_hash`，不输出 query 原文。
3. `planned-hybrid` 不低于 baseline 时才可进入 E3。
4. `planned-hybrid+rerank` 若 recall 仍低于 baseline，继续 shadow-only。

## 七、阶段 E3：RAG planned-hybrid 小流量灰度

### 目标

在真实 shadow 证据支持下，把 `planned-hybrid` 从候选路径推进到受控热路径灰度。

### 前置条件

1. E2 真实 shadow log 证明 `planned-hybrid` 不低于 baseline。
2. `planned-hybrid+rerank` 未达标前不得热启。
3. 生产默认仍保持 `hybrid`，灰度必须有显式环境变量或配置变更。

### 执行步骤

1. 确认当前生产 RAG 模式为 `hybrid`。
2. 准备灰度配置 `RAG_RETRIEVAL_MODE=planned-hybrid`。
3. 先在本地和 staging 等价环境跑 release gate。
4. 生产启用小流量后跑 runtime、capacity、callback、客户 RAG smoke。
5. 观察真实 shadow log 和用户回复风险。
6. 指标下降时立即回滚到 `hybrid`。

### 验收命令

```powershell
python scripts\report_retrieval_eval_matrix.py --db data\bot.db --fixture tests\fixtures\customer_rag_golden_cases.json --k 5
python scripts\report_rag_shadow_observability.py --summary
python scripts\check_langchain_ai_layer_capacity.py --include-production-runtime --summary
python scripts\check_langchain_ai_layer_release_gate.py --include-production-smoke --include-observability-evidence --include-production-runtime-capacity --summary
python scripts\build_langchain_release_evidence_packet.py --require-production-evidence --summary
```

### 完成标准

1. 生产灰度前后都有 release evidence。
2. `planned-hybrid` 灰度期间无 release gate 失败。
3. 回复回放、事实敏感断言和 callback probe 不回退。
4. 回滚命令写入 LOGBOOK 或 evidence index。

## 八、阶段 E4：LangSmith 生产小流量外发

### 目标

在合规、脱敏和容量可控的前提下，让 LangChain trace 小流量进入 LangSmith。

### 前置条件

1. 人工确认允许向 LangSmith 外发脱敏 metadata。
2. API key 不入仓，不打印。
3. 初始采样率建议 `0.01` 到 `0.05`。
4. 缺少 key 或配置错误时主流程必须降级，不影响回复。

### 执行步骤

1. 运行 LangSmith runtime config 检查。
2. 生成生产启用操作包。
3. 人工确认外发合规。
4. 注入生产环境变量。
5. 重启服务。
6. 跑容量门禁和 release gate。
7. 验证 LangSmith 项目中出现脱敏 trace。
8. 若延迟、内存或错误率升高，关闭 tracing。

### 验收命令

```powershell
python scripts\check_langsmith_runtime_config.py --summary
python scripts\check_langsmith_production_rollout.py --summary
python scripts\build_langsmith_production_enablement_packet.py --summary
python scripts\check_langchain_ai_layer_capacity.py --include-production-runtime --summary
python scripts\check_langchain_ai_layer_release_gate.py --include-production-smoke --include-observability-evidence --include-production-runtime-capacity --summary
```

### 完成标准

1. `langsmith_enabled=true` 只在人工合规确认和生产配置完成后出现。
2. trace metadata 不含敏感字段。
3. 生产容量门禁通过。
4. 关闭 LangSmith 后主流程仍正常。

## 九、阶段 E5：事实敏感场景真实样本强化

### 目标

把订单、售后、退款、库存、价格、转人工等高风险场景从合成 eval 推进到真实脱敏 replay 覆盖。

### 执行步骤

1. 基于 E1 的真实 replay pool 按场景统计覆盖。
2. 每类事实敏感场景至少接入 5 条真实脱敏样本。
3. 对每条样本声明必须出现事实、禁止出现内容和允许转人工条件。
4. 跑 real replay coverage 和 forbidden reply patterns。
5. 将失败 case 输出为可复现命令。

### 验收命令

```powershell
python scripts\check_real_conversation_replay_coverage.py --fixture <redacted-fixture-path> --summary
python scripts\report_agent_eval.py --latest --include-real-replay --include-reply-replay --summary
python scripts\check_langchain_ai_layer_release_gate.py --include-real-replay --include-real-replay-coverage --summary
```

### 完成标准

1. order、refund、after_sales、inventory、price、human_transfer 每类至少 5 条。
2. 禁止回复模式检查通过。
3. 失败能定位到 case id、场景、断言和实际输出摘要。

## 十、阶段 E6：作品集证据包升级

### 目标

把工程成果整理成能在面试中讲清楚的证据链，而不是只说“用了 LangChain”。

### 输出物

1. 一页架构图。
2. LangChain / LangGraph 接管边界。
3. Modular RAG 说明。
4. RAG shadow 和灰度证据。
5. Agent Eval 和真实 replay 证据。
6. LangSmith / trace 观测证据。
7. 生产 release evidence packet。
8. 关键取舍说明：为什么 AI 应用层接管，而业务领域层不交给 LangChain。

### 验收命令

```powershell
python scripts\report_agent_eval.py --latest --json-out reports\agent-eval\portfolio-latest.json
python scripts\report_rag_shadow_observability.py --summary
python scripts\report_langchain_observability_evidence.py --summary
python scripts\build_langchain_release_evidence_packet.py --require-production-evidence --summary
python scripts\check_project.py --skip-tests
```

### 完成标准

1. 每个作品集亮点都能对应代码路径。
2. 每个效果结论都有命令或报告证据。
3. 文档能解释长期维护边界，而不是把 LangChain 当作业务框架。

## 十一、推荐执行顺序

```text
E0 P22a 生产证据基线复核
  -> E1 P17b 首批真实脱敏样本接入
  -> E2 真实 RAG shadow log 接入
  -> E3 RAG planned-hybrid 小流量灰度
  -> E4 LangSmith 生产小流量外发
  -> E5 事实敏感场景真实样本强化
  -> E6 作品集证据包升级
```

## 十二、暂停条件

遇到以下情况必须暂停，不得伪造完成：

1. 没有真实脱敏样本，却试图让 `real_sample_ready=true`。
2. 没有真实 RAG shadow log，却试图打开 RAG 灰度。
3. 没有人工合规确认，却试图开启 LangSmith 生产外发。
4. release gate、capacity gate、callback probe 任一失败。
5. 发现样本、trace 或报告包含敏感原文。

## 十三、下一步

立即下一步应执行 E1：

```text
接入首批真实脱敏客服会话 replay 样本。
```

如果暂时拿不到真实样本，则可以先执行 E2 的输入包准备和严格门禁复核，但不能把 readiness 状态改为 ready。
