# LangChain AI 应用层生产增强计划书

> trace_id: `20260709-langchain-ai-layer-production-enhancement`
> 日期：2026-07-09
> 状态：计划冻结，待执行
> 前置成果：[LangChain 生态全面接管 AI 应用层计划书](./langchain-ecosystem-ai-layer-takeover-plan.md)
> 作品集入口：[LangChain AI 应用层作品集说明](./langchain-ai-layer-portfolio.md)

## 一、目标

当前项目已经完成 LangChain / LangGraph 对 AI 应用层的接管。下一阶段不再以“继续扩大框架覆盖率”为主要目标，而是把现有能力推进到可上线、可观测、可评估、可展示的工程状态。

本计划的核心目标是：

```text
把 LangChain / LangGraph 迁移成果转化为生产证据、持续评估体系、线上观测能力和作品集表达。
```

后续增强优先服务四件事：

1. 真实上线可验证。
2. 线上问题可追踪。
3. 效果改进可量化。
4. 面试展示可讲清。

## 二、当前基线

截至 2026-07-09，项目当前基线如下：

| 能力 | 当前状态 | 证据入口 |
|---|---|---|
| 客户机器人编排 | 已由 LangGraph 接管 | `app/service/agents/customer/graph.py` |
| 客户模型调用 | 已有 LangChain model adapter | `app/service/agents/customer/model.py` |
| 客户工具 | 已注册为 LangChain tools | `app/service/agents/tools/customer.py` |
| RAG adapter | 已接入 LangChain Retriever 形态 | `app/service/agents/rag/retriever.py` |
| RAG query plan / rerank | 已有离线 eval 路径 | `app/service/agents/rag/query.py`、`app/service/agents/rag/rerank.py` |
| 员工助手编排 | 已由 LangGraph 接管 | `app/service/agents/employee/graph.py` |
| 员工 planner | 已接入 LangChain structured output fallback | `app/service/agents/employee/structured_planner.py` |
| Agent Eval | 已有双机器人离线聚合报告 | `scripts/report_agent_eval.py` |
| 作品集说明 | 已有当前版架构说明 | `docs/architecture/langchain-ai-layer-portfolio.md` |

已验证的关键结果：

```text
agent_eval status=passed total=58 failed=0 pass_rate=1.0
真实 BGE embedding 路径下 hybrid / planned-hybrid / planned-hybrid+rerank 均达到 Recall@5=1.0、MRR=1.0
```

当前主要缺口：

1. 生产部署与回调探针证据尚未作为本轮 LangChain 接管的正式收口资产归档。
2. LangSmith / trace 观测入口已有配置基础，但缺少生产级运行报告闭环。
3. Eval 仍以 fixture 和离线脚本为主，真实业务回放样本不足。
4. planned-hybrid / rerank 尚未进入灰度热路径。
5. 面试材料已有文本说明，但缺少一套“一页讲清”的证据包。

## 三、边界原则

### 3.1 继续坚持的边界

LangChain / LangGraph 继续负责：

1. 模型调用。
2. 工具绑定。
3. Agent 节点编排。
4. Retriever adapter。
5. structured output。
6. tracing config。
7. eval 报告。

项目业务层继续负责：

1. 订单、商品、库存、退款、售后事实。
2. 客户主档和客户线索。
3. 知识发布状态。
4. SQLite repository 和 migration。
5. 有赞、企微、后台 API 的业务处理。

### 3.2 后续增强不做什么

本计划不把以下事项作为近期目标：

1. 不为了“更彻底”而让 LangChain 直接读写业务数据库。
2. 不把员工助手最终回复交给 LLM 自由润色。
3. 不在没有真实 eval 对照前打开 planned/rerank 热路径。
4. 不把观测、报告、作品集文档和业务逻辑混成一次大改。

## 四、阶段路线

### 阶段 P0：生产上线验证闭环

目标：确认当前 LangChain AI 应用层接管成果在生产服务器可运行，并形成可追溯证据。

改动范围：

- 原则上不改运行时代码。
- 必要时只补充探针脚本参数、报告输出和文档索引。
- 不引入新的 AI 行为。

执行步骤：

1. 确认本地工作区干净，记录当前 commit、VERSION 和依赖版本。
2. 推送 `origin/master` 和 `server/master`。
3. 在生产服务器确认 `/opt/yunxibakebot` fast-forward 到目标 commit。
4. 重启 `yunxibakebot` 服务。
5. 检查 `/health` 和 `/ready`。
6. 运行企微员工助手 callback probe。
7. 运行客户机器人最小 RAG 正向探针。
8. 运行员工助手订单查询正向探针。
9. 将生产验证输出登记到 evidence index 或 LOGBOOK。

验收命令：

```powershell
git status -sb
git rev-parse HEAD
git push origin master
git push server master
git ls-remote origin master
git ls-remote server master
python scripts/report_agent_eval.py --latest
python scripts/report_retrieval_eval_matrix.py --db data/bot.db --fixture tests/fixtures/customer_rag_golden_cases.json --k 5
python scripts/check_project.py --skip-tests
python scripts/check_evidence_index.py --summary
```

生产侧验收：

```powershell
curl.exe https://yunxifood.cn/health
curl.exe https://yunxifood.cn/ready
python scripts/check_wecom_employee_agent_callback.py --json --output reports/wecom-employee-agent/langchain-prod-callback.json
```

完成标准：

- 生产 `/health` 和 `/ready` 均通过。
- 企微 callback probe 有可读 JSON 证据。
- 至少一个客户机器人 RAG 正向问题和一个员工助手订单查询正向问题通过。
- LOGBOOK 或 evidence index 能追溯 commit、命令、结果和报告路径。

回滚策略：

- 若服务启动失败，回退到上一个已知健康 commit 并重启。
- 若 callback probe 失败但 `/health`、`/ready` 正常，先保留服务运行，定位企微入口或环境变量。
- 若客户 RAG 或员工助手行为失败，关闭相关 feature flag 或回退本次 commit。

### 阶段 P1：线上 Trace 与 LangSmith 观测

目标：让每次 AI 回复可以追踪模型、工具、RAG、耗时、失败回退和最终结果。

改动范围：

- `app/service/agents/observability.py`
- 客户 graph 节点 trace 输出。
- 员工 graph 节点 trace 输出。
- 本地 trace events 与 LangSmith 配置桥接。
- 运行报告脚本。

建议改动：

1. 明确统一 trace 字段：
   - `trace_id`
   - `conversation_id`
   - `channel`
   - `agent`
   - `node`
   - `model`
   - `tool_name`
   - `knowledge_entry_ids`
   - `latency_ms`
   - `fallback_reason`
   - `final_status`
2. 新增 LangSmith 开关：
   - 默认本地关闭。
   - 生产可通过环境变量打开。
   - 缺少 key 时不得影响主流程。
3. 为客户机器人补齐：
   - model 节点耗时。
   - tool 调用次数。
   - RAG 命中条目。
   - fallback 回复原因。
4. 为员工助手补齐：
   - rule-first 命中或 structured planner 命中。
   - 工具计划。
   - deterministic finalizer 状态。
5. 新增只读报告脚本：
   - 汇总最近一段 trace。
   - 输出失败率、平均耗时、工具调用分布、RAG 命中分布。

验收命令：

```powershell
python -m pytest tests/service/agents -q --no-cov
python scripts/report_agent_eval.py --latest
python scripts/check_project.py --skip-tests
```

建议新增验收：

```powershell
python scripts/report_agent_traces.py --latest --summary
python scripts/report_agent_traces.py --latest --json
```

完成标准：

- LangSmith 未配置时主流程不失败。
- 本地 trace 报告能看到客户机器人和员工助手的节点级摘要。
- 至少覆盖成功、工具失败、RAG 未命中、fallback 四类事件。
- 观测字段不包含手机号、地址、open_id 等未脱敏敏感信息。

### 阶段 P2：真实业务 Eval 数据集扩容

目标：把 eval 从工程 smoke 扩展为真实业务回归资产。

改动范围：

- `tests/fixtures/`
- `scripts/eval_customer_agent.py`
- `scripts/eval_employee_agent.py`
- `scripts/report_agent_eval.py`
- `docs/harness-engineering/core/evidence-index.md`

执行步骤：

1. 定义脱敏样本格式：
   - 用户问题。
   - 期望命中知识或工具。
   - 禁止出现的回复。
   - 必须出现的事实。
   - 允许转人工的条件。
2. 扩充客户机器人样本：
   - 商品咨询。
   - 库存咨询。
   - 配送时间。
   - 退款售后。
   - 转人工。
   - 知识未命中。
3. 扩充员工助手样本：
   - 查订单。
   - 查客户。
   - 查发货时间。
   - 弱关键词。
   - 不支持意图。
4. 给 eval 报告增加：
   - `--json-out`
   - `--fail-fast`
   - `--case-id`
   - `--agent customer|employee|all`
5. 把 eval 结果归档到 `reports/agent-eval/`，并在 evidence index 登记关键版本。

验收命令：

```powershell
python scripts/eval_customer_agent.py --summary
python scripts/eval_employee_agent.py --summary
python scripts/report_agent_eval.py --latest
python scripts/report_agent_eval.py --latest --json-out reports/agent-eval/latest.json
python scripts/check_evidence_index.py --summary
```

完成标准：

- 客户机器人 eval cases 从当前 9 项扩到至少 40 项。
- 员工助手 eval cases 保持或超过 60 项。
- 每个 case 有稳定 `case_id`。
- eval 失败能定位到 agent、case、断言和实际输出。
- 报告可作为作品集证据引用。

## 十五、P2a 落地记录

2026-07-09 已完成 P2 真实业务 Eval 数据集扩容的第一切片：

- `app/service/agents/evaluation.py` 新增通用 eval helper：
  - `filter_agent_eval_result()` 支持按稳定 `case_id` 过滤。
  - `apply_fail_fast()` 支持保留到首个失败 case。
  - `write_json_report()` 支持写入 UTF-8 JSON 报告，并自动创建父目录。
- `scripts/eval_customer_agent.py` 新增：
  - `--case-id`
  - `--fail-fast`
  - `--json-out`
- `scripts/eval_employee_agent.py` 新增：
  - `--case-id`
  - `--fail-fast`
  - `--json-out`
- `scripts/report_agent_eval.py` 新增：
  - `--agent customer|employee|all`
  - `--case-id`
  - `--fail-fast`
  - `--json-out`
- 本切片不扩真实样本数量，先补齐 runner 能力，避免后续客户 40+、员工 60+ 样本扩容后无法快速定位失败。

P2a 验收：

```powershell
python -m pytest tests/service/agents/test_evaluation.py tests/scripts/test_agent_eval_scripts.py -q --no-cov
python -m ruff check app/service/agents/evaluation.py scripts/eval_customer_agent.py scripts/eval_employee_agent.py scripts/report_agent_eval.py tests/service/agents/test_evaluation.py tests/scripts/test_agent_eval_scripts.py
python -m ruff format --check app/service/agents/evaluation.py scripts/eval_customer_agent.py scripts/eval_employee_agent.py scripts/report_agent_eval.py tests/service/agents/test_evaluation.py tests/scripts/test_agent_eval_scripts.py
python scripts/eval_customer_agent.py --summary
python scripts/eval_employee_agent.py --summary
python scripts/report_agent_eval.py --latest --json-out reports/agent-eval/latest.json
python scripts/report_agent_eval.py --agent customer --case-id customer-product-001 --summary
python scripts/report_agent_eval.py --agent employee --case-id employee.capability_contracts --json
```

P2a 验证结果：

```text
10 项 targeted tests 通过。
Ruff check 通过。
Ruff format --check 通过。
customer_agent_eval status=passed total=9 failed=0 pass_rate=1.0。
employee_agent_eval status=passed total=49 failed=0 pass_rate=1.0。
agent_eval JSON 归档到 reports/agent-eval/latest.json，summary 为 passed 58/58。
customer case filter 可收敛到 total=1。
employee case filter 可输出 employee.capability_contracts 单 case JSON。
```

P2 后续：

- P2c 扩充员工助手 eval 样本，目标保持或超过 60 项，并强化查订单、查客户、查发货时间、弱关键词和不支持意图。

## 十六、P2b 落地记录

2026-07-09 已完成 P2 真实业务 Eval 数据集扩容的第二切片：

- `tests/fixtures/customer_rag_golden_cases.json` 从 8 条业务 case 扩充到 40 条业务 case。
- 客户 eval 总数从 9 项提升到 41 项，其中 1 项为 fixture governance，40 项为客户业务样本。
- 样本覆盖：
  - 商品咨询：10 条。
  - 库存咨询：8 条。
  - 配送时间 / 配送范围 / 自提：7 条。
  - 退款售后 / 改单 / 配送异常：7 条。
  - 转人工 / 过敏 / 定制 / 查订单：4 条。
  - 知识未命中治理：4 条。
- 新增 `inventory` 和 `knowledge_no_match` 两个 required group；`knowledge_no_match` 不写成无 relevant 的假空样本，而是要求命中人工客服 / 转人工 / 食品安全等治理知识，避免破坏 retrieval eval 的可评估性。

P2b 验收：

```powershell
python -m pytest tests/scripts/test_check_customer_rag_golden_cases.py tests/scripts/test_agent_eval_scripts.py::test_customer_eval_result_uses_golden_cases -q --no-cov
python scripts/check_customer_rag_golden_cases.py --summary
python scripts/eval_customer_agent.py --summary
python scripts/report_agent_eval.py --agent customer --summary
python scripts/report_agent_eval.py --latest --json-out reports/agent-eval/latest.json
python scripts/report_retrieval_eval_matrix.py --db data/bot.db --fixture tests/fixtures/customer_rag_golden_cases.json --k 5
```

P2b 验证结果：

```text
客户 fixture 结构校验通过：customer_rag_golden_cases status=passed total=47 failed=0。
客户 eval 通过：customer_agent_eval status=passed total=41 failed=0 pass_rate=1.0。
双机器人聚合 eval 通过：agent_eval status=passed total=90 failed=0 pass_rate=1.0。
RAG 矩阵在 400 条启用知识、40 条客户标注样本下可跑通；best=hybrid，Recall@5=0.975，MRR=0.9437。
```

P2 后续：

- P2c 已完成员工助手 eval 样本扩容，员工 eval 从 49 项推进到 62 项，覆盖查订单、查客户、查发货时间、弱关键词和不支持意图。
- P2d 已把 expanded customer fixture、员工 planner 和双机器人聚合结果的分组统计加入 eval 报告，方便作品集展示。

## 十七、P2c 落地记录

2026-07-09 已完成 P2 真实业务 Eval 数据集扩容的第三切片：

- `scripts/wecom_employee_agent_probe_cases.py` 新增 13 条 P2c 员工助手自由问法样本。
- 员工助手 planner 探针从 48 条提升到 61 条。
- 员工助手 eval 总数从 49 项提升到 62 项，其中 1 项为 capability contracts 聚合治理 case，61 项为 planner 离线样本。
- 样本覆盖：
  - 查订单：交易成功、已关闭、待收货、待发货。
  - 查发货时间：上午、下午待处理订单。
  - 商品销量：草莓蛋糕当日销量。
  - 精确订单：订单详情、客户复购。
  - 查客户：李四客户线索、王女士地址线索。
  - 知识问答：退款规则。
  - 不支持意图：写诗。
- 本切片不改线上 planner、工具执行、业务 service 或 deterministic finalizer，只把现有可识别能力固化为回归样本。

P2c 验收：

```powershell
python scripts/check_wecom_employee_agent_plans.py --json
python scripts/eval_employee_agent.py --summary
python scripts/report_agent_eval.py --latest --json-out reports/agent-eval/latest.json
python -m pytest tests/scripts/test_agent_eval_scripts.py::test_employee_eval_result_includes_planner_and_contracts -q --no-cov
```

P2c 验证结果：

```text
员工助手规划探针通过：61 项失败 0。
员工助手 eval 通过：employee_agent_eval status=passed total=62 failed=0 pass_rate=1.0。
双机器人聚合 eval 通过：agent_eval status=passed total=103 failed=0 pass_rate=1.0。
聚焦测试通过：1 项失败 0。
```

P2 当前状态：

- 客户机器人 eval：41 项通过，其中 40 条业务样本。
- 员工助手 eval：62 项通过，其中 61 条 planner 样本。
- 双机器人聚合 eval 已提升到 103 项，`python scripts/report_agent_eval.py --latest --json-out reports/agent-eval/latest.json` 可归档当前报告摘要。
- P2d 已把 case group 统计、agent 分布和新增样本摘要加入 eval report metadata，方便作品集展示。

## 十八、P2d 落地记录

2026-07-09 已完成 P2 真实业务 Eval 数据集扩容的第四切片：

- `app/service/agents/evaluation.py` 新增 `summarize_agent_eval_results()` 和 `summarize_eval_cases_by_group()`。
- 单 agent eval JSON 新增 `case_groups`：
  - 客户机器人可直接展示商品咨询、库存、配送、退款售后、转人工和知识未命中治理覆盖。
  - 员工助手可直接展示 planner 与 capability contracts 覆盖。
- 双机器人聚合 eval JSON 新增：
  - `agent_totals`：customer 41 项、employee 62 项。
  - 顶层 `case_groups`：跨 agent 的统一覆盖矩阵。
- 本切片只扩离线 eval 报告结构，不改变客户/员工热路径、planner、RAG、工具执行或业务 service。

P2d 验收：

```powershell
python -m pytest tests/service/agents/test_evaluation.py tests/scripts/test_agent_eval_scripts.py -q --no-cov
python scripts/report_agent_eval.py --latest --json-out reports/agent-eval/latest.json
```

P2d 验证结果：

```text
Agent Eval 模型和脚本测试通过：10 项失败 0。
双机器人聚合 eval 通过：agent_eval status=passed total=103 failed=0 pass_rate=1.0。
JSON 抽查已包含 agent_totals、顶层 case_groups 和每个 agent 的 case_groups。
```

P2 当前状态：

- P2a eval runner 归档能力完成。
- P2b 客户机器人业务样本扩容完成。
- P2c 员工助手样本扩容完成。
- P2d eval report metadata 完成。
- 下一阶段建议进入 P3：RAG 热路径灰度增强，先做 feature flag 与 shadow compare，不直接改变线上回复。

### 阶段 P3：RAG 热路径灰度增强

目标：把 planned-hybrid / rerank 从离线评估能力推进到可灰度的线上候选能力。

改动范围：

- `app/service/agents/rag/retriever.py`
- `app/service/agents/rag/query.py`
- `app/service/agents/rag/rerank.py`
- 客户机器人 RAG 调用入口。
- retrieval logs。
- RAG eval matrix 脚本。

执行步骤：

1. 增加 feature flag：
   - `RAG_RETRIEVAL_MODE=hybrid`
   - `RAG_RETRIEVAL_MODE=planned-hybrid`
   - `RAG_RETRIEVAL_MODE=planned-hybrid-rerank`
2. 默认生产仍保持当前稳定模式。
3. 新增 shadow compare：
   - 主链路仍用稳定结果。
   - 后台并行计算 planned/rerank 候选。
   - 记录排序差异，不影响用户回复。
4. 增加检索日志字段：
   - query plan。
   - vector top-k。
   - BM25 top-k。
   - RRF 后 top-k。
   - rerank 后 top-k。
   - final injected context。
5. 连续收集真实问题差异报告后再决定是否灰度打开。

验收命令：

```powershell
python scripts/report_retrieval_eval_matrix.py --db data/bot.db --fixture tests/fixtures/customer_rag_golden_cases.json --k 5
python scripts/check_knowledge_retrieval_logs_smoke.py --json
python scripts/check_knowledge_audience_governance_smoke.py --json
python -m pytest tests/service/agents/test_rag_retriever.py tests/scripts/test_report_retrieval_eval_matrix.py -q --no-cov
```

建议新增验收：

```powershell
python scripts/report_retrieval_shadow_compare.py --db data/bot.db --fixture tests/fixtures/customer_rag_golden_cases.json --k 5 --json-out reports/retrieval-shadow/latest.json
```

完成标准：

- feature flag 默认值不改变现有生产行为。
- shadow compare 能输出稳定模式与候选模式的差异。
- planned/rerank 候选在真实样本上不低于稳定模式。
- RAG 日志能解释“为什么命中这条知识”。

## 十九、P3a 落地记录

2026-07-09 已完成 P3 RAG 热路径灰度增强的第一切片：

- 新增 `scripts/report_retrieval_shadow_compare.py`，默认以 `hybrid` 作为稳定 baseline，以 `planned-hybrid` 和 `planned-hybrid+rerank` 作为候选模式。
- shadow compare 复用 `scripts/report_retrieval_eval_matrix.py` 的索引构建与 searcher 组装，避免重复实现向量、BM25、planned query 和 rerank 包装逻辑。
- 报告输出：
  - baseline 指标。
  - candidate 指标。
  - `delta_recall_at_k` / `delta_mrr`。
  - 逐 case 的 baseline top-k、candidate top-k、title、changed 和 overlap_count。
- 本切片只做离线 shadow compare，不接入客户热路径，不改变线上回复，不启用 rerank。

P3a 验收：

```powershell
python -m pytest tests/scripts/test_report_retrieval_shadow_compare.py tests/scripts/test_report_retrieval_eval_matrix.py tests/scripts/test_eval_retrieval.py -q --no-cov
python scripts/report_retrieval_shadow_compare.py --db data/bot.db --fixture tests/fixtures/customer_rag_golden_cases.json --k 5 --json-out reports/retrieval-shadow/latest.json
```

P3a 验证结果：

```text
shadow compare / matrix / retrieval eval 测试通过：18 项失败 0。
真实 embedding 路径下，语料库 data\bot.db 400 条启用知识，客户 fixture 40 条可评估样本。
baseline hybrid: Recall@5=0.975, MRR=0.9437。
planned-hybrid: Recall@5=0.975, MRR=0.9437，delta_recall=0.0，delta_mrr=0.0。
planned-hybrid+rerank: Recall@5=0.95, MRR=0.9375，delta_recall=-0.025，delta_mrr=-0.0062。
```

P3 后续：

- P3b 已补 `RAG_RETRIEVAL_MODE` feature flag 的配置解析与默认值测试，生产默认仍保持 `hybrid`。
- P3c 再把 shadow compare 接入真实检索日志或显式运维探针，连续收集差异后再决定是否灰度打开 planned/rerank。
- 当前数据不支持热启 `planned-hybrid+rerank`，因为它低于 baseline。

## 二十、P3b 落地记录

2026-07-09 已完成 P3 RAG 热路径灰度增强的第二切片：

- `app/config.py` 新增 RAG 检索模式常量：
  - `hybrid`
  - `planned-hybrid`
  - `planned-hybrid-rerank`
- `Settings.RAG_RETRIEVAL_MODE` 默认值为 `hybrid`。
- `RAG_RETRIEVAL_MODE` 会在 Settings 初始化时做合法值校验：
  - 自动 `strip()` 和小写归一化。
  - 非法值直接抛出 pydantic validation error。
- 本切片不接入客户热路径，不改变线上回复，不启用 planned/rerank；配置字段只是为后续 P3c/P3d 灰度入口预留安全门禁。

P3b 验收：

```powershell
python -m pytest tests/test_config.py -q --no-cov
python -m ruff check app/config.py tests/test_config.py
python -m ruff format --check app/config.py tests/test_config.py
python -c "import sys; import app.config; print({name: (name in sys.modules) for name in ['langsmith','langchain_openai','langgraph']})"
```

P3b 验证结果：

```text
配置测试通过：7 项失败 0。
Ruff check 通过。
Ruff format --check 通过。
冷导入 app.config 不加载 langsmith、langchain_openai、langgraph。
```

P3 后续：

- P3c 已把 `RAG_RETRIEVAL_MODE` 接入只读 strategy/factory helper，生成对应的 LangChain retriever adapter 参数，但默认仍保持 `hybrid`。
- P3d 再考虑显式运维探针或 shadow logging，主链路继续使用稳定模式。

## 二十一、P3c 落地记录

2026-07-09 已完成 P3 RAG 热路径灰度增强的第三切片：

- 新增 `app/service/agents/rag/modes.py`。
- 新增 `RagRetrievalModeStrategy`：
  - `mode`
  - `query_planner`
  - `document_reranker`
  - `uses_query_planning`
  - `uses_rerank`
- 新增 `resolve_rag_retrieval_mode_strategy()`：
  - `hybrid` -> 不挂 query planner / reranker。
  - `planned-hybrid` -> 挂 `build_customer_rag_query_plan()`。
  - `planned-hybrid-rerank` -> 挂 `build_customer_rag_query_plan()` 和 `rerank_documents_by_query_rules()`。
- 新增 `build_langchain_knowledge_retriever_for_mode()`，把 mode strategy 转成 `LangChainKnowledgeRetriever` 参数。
- 本切片不接入客户 graph、context builder 或线上回复；只提供后续灰度入口需要的受控 helper。

P3c 验收：

```powershell
python -m pytest tests/service/agents/test_rag_retriever.py -q --no-cov
python -m ruff check app/service/agents/rag/modes.py tests/service/agents/test_rag_retriever.py
python -m ruff format --check app/service/agents/rag/modes.py tests/service/agents/test_rag_retriever.py
python -c "import sys; import app.service.agents.rag.modes; print({name: (name in sys.modules) for name in ['langsmith','langchain_openai','langgraph','langchain_core']})"
```

P3c 验证结果：

```text
RAG retriever adapter 测试通过：12 项失败 0。
Ruff check 通过。
Ruff format --check 通过。
冷导入 app.service.agents.rag.modes 不加载 langsmith、langchain_openai、langgraph、langchain_core。
```

P3 后续：

- P3d 已新增显式 shadow compare 运维探针，把当前稳定检索结果与候选策略并排输出，并把当前 `RAG_RETRIEVAL_MODE` 写入报告 metadata。
- P3e 再考虑将 `RAG_RETRIEVAL_MODE` 接入客户 RAG 热路径；默认仍保持 `hybrid`，且只有当 shadow compare 连续证明候选不低于 baseline，才考虑打开 planned/rerank。

## 二十二、P3d 落地记录

2026-07-10 已完成 P3 RAG 热路径灰度增强的第四切片：

- `scripts/report_retrieval_shadow_compare.py` 新增 `--baseline-mode`，可显式选择 baseline 检索模式。
- `scripts/report_retrieval_shadow_compare.py` 新增可重复的 `--candidate-mode`，支持只比较一个候选模式，也支持继续使用默认候选：
  - `planned-hybrid`
  - `planned-hybrid-rerank`
  - `planned-hybrid+rerank`
- shadow compare 报告 metadata 新增 `configured_rag_retrieval_mode`，用于并排展示当前运行配置与离线候选模式。
- Windows 控制台下 `--json` 输出改为 UTF-8 stdout，避免知识标题含特殊符号时触发 GBK 编码失败。
- 本切片仍不接入客户 graph、context builder 或线上回复；只增强显式运维探针和离线证据。

P3d 验收：

```powershell
python -m pytest tests\scripts\test_report_retrieval_shadow_compare.py tests\service\agents\test_rag_retriever.py -q --no-cov
python -m ruff check scripts\report_retrieval_shadow_compare.py tests\scripts\test_report_retrieval_shadow_compare.py
python -m ruff format --check scripts\report_retrieval_shadow_compare.py tests\scripts\test_report_retrieval_shadow_compare.py
python scripts\report_retrieval_shadow_compare.py --db data\bot.db --fixture tests\fixtures\customer_rag_golden_cases.json --k 5 --json-out reports\retrieval-shadow\latest.json
python scripts\report_retrieval_shadow_compare.py --db data\bot.db --fixture tests\fixtures\customer_rag_golden_cases.json --k 5 --candidate-mode planned-hybrid-rerank --json
```

P3d 验证结果：

```text
RAG shadow compare 与 mode strategy 测试通过：17 项失败 0。
Ruff check 通过。
Ruff format --check 通过。
真实 embedding 路径下，语料库 data\bot.db 400 条启用知识，客户 fixture 40 条可评估样本。
baseline hybrid: Recall@5=0.975, MRR=0.9437。
planned-hybrid: Recall@5=0.975, MRR=0.9437，delta_recall=0.0，delta_mrr=0.0。
planned-hybrid+rerank: Recall@5=0.95, MRR=0.9375，delta_recall=-0.025，delta_mrr=-0.0062。
显式单候选 `--candidate-mode planned-hybrid-rerank --json` 通过，不再因 Windows 控制台编码失败。
```

P3 后续：

- P3e 已把 `RAG_RETRIEVAL_MODE` 接入客户 RAG 热路径；默认 `hybrid` 仍保持原稳定路径，非默认模式才走 LangChain retriever adapter。
- 当前数据仍不支持热启 `planned-hybrid-rerank`。

## 二十三、P3e 落地记录

2026-07-10 已完成 P3 RAG 热路径灰度增强的第五切片：

- 客户 RAG 热路径现在读取 `settings.RAG_RETRIEVAL_MODE`。
- 默认 `hybrid` 模式继续直接调用 `KnowledgeRetriever.search()`，不额外进入 LangChain retriever，确保生产默认行为稳定。
- `planned-hybrid` 和 `planned-hybrid-rerank` 模式通过 `build_langchain_knowledge_retriever_for_mode()` 进入 LangChain retriever adapter：
  - `planned-hybrid` 启用 query planner。
  - `planned-hybrid-rerank` 启用 query planner + document reranker。
- 新增 `document_to_knowledge_entry()`，把 LangChain Document 还原成现有 `KnowledgeEntry`，让 prompt、context budget、guard source、知识 ID trace 继续复用原业务模型。
- 本切片不让 LangChain 直接读取数据库，不绕过 `KnowledgeRetriever` 的 audience 过滤、发布状态、有效期、实时价格/库存注入和检索日志。

P3e 验收：

```powershell
python -m pytest tests\service\test_chat_refactor.py tests\service\agents\test_rag_retriever.py -q --no-cov
python -m ruff check app\service\chat_context.py app\service\agents\rag\documents.py tests\service\test_chat_refactor.py
python -m ruff format --check app\service\chat_context.py app\service\agents\rag\documents.py tests\service\test_chat_refactor.py
python scripts\eval_customer_agent.py --summary
$env:RAG_RETRIEVAL_MODE='planned-hybrid'; python scripts\eval_customer_agent.py --summary; Remove-Item Env:\RAG_RETRIEVAL_MODE
python scripts\report_retrieval_eval_matrix.py --db data\bot.db --fixture tests\fixtures\customer_rag_golden_cases.json --k 5
```

P3e 验证结果：

```text
chat_context 与 RAG retriever 测试通过：37 项失败 0。
Ruff check 通过。
Ruff format --check 通过。
客户机器人默认模式 eval 通过：41 项失败 0。
客户机器人 planned-hybrid 环境变量模式 eval 通过：41 项失败 0。
RAG 矩阵保持：hybrid Recall@5=0.975、MRR=0.9437；planned-hybrid 持平；planned-hybrid+rerank Recall@5=0.95、MRR=0.9375。
```

P3 当前状态：

- P3a shadow compare 报告完成。
- P3b `RAG_RETRIEVAL_MODE` 配置门禁完成。
- P3c retrieval mode strategy/helper 完成。
- P3d 显式 shadow compare 运维探针完成。
- P3e 客户 RAG 热路径 feature flag 接入完成。
- 下一阶段建议进入 P4：事实敏感场景治理增强，继续强化订单、退款、售后、库存、价格和转人工等高风险场景。

### 阶段 P4：事实敏感场景治理增强

目标：强化订单、售后、退款、库存、转人工等高风险场景的可控性。

改动范围：

- 客户机器人 guard。
- RAG context builder。
- transfer / handoff 策略。
- golden cases。
- eval scripts。

执行步骤：

1. 定义事实敏感场景清单：
   - 订单状态。
   - 退款规则。
   - 售后承诺。
   - 实时库存。
   - 价格。
   - 转人工。
2. 为每类场景定义回复策略：
   - 必须来自工具。
   - 必须来自知识。
   - 必须转人工。
   - 可以一般性说明。
3. 增加禁止行为断言：
   - 不编造订单。
   - 不承诺未配置退款。
   - 不输出过期库存。
   - 不泄露客户隐私。
4. 对库存继续坚持动静分离：
   - embedding 文本保留静态语义。
   - 在线 context 注入实时库存。
5. 增加敏感场景 eval cases。

验收命令：

```powershell
python scripts/report_agent_eval.py --latest
python scripts/check_customer_rag_golden_cases.py --summary
python scripts/check_knowledge_audience_governance_smoke.py --json
python scripts/check_project.py --skip-tests
```

完成标准：

- 每类事实敏感场景至少 5 个 eval cases。
- 对订单、退款、库存、转人工有明确断言。
- 回复策略能在作品集里讲成“AI 客服治理能力”，而不是单纯 prompt 约束。

## 二十四、P4a 落地记录

2026-07-10 已完成 P4 事实敏感场景治理增强的第一切片：

- `tests/fixtures/customer_rag_golden_cases.json` 新增 `required_sensitive_scenarios`：
  - `order`
  - `refund`
  - `after_sales`
  - `inventory`
  - `price`
  - `human_transfer`
- 客户业务样本从 40 条扩展到 70 条，客户 eval 总数从 41 项提升到 71 项。
- 新增 30 条事实敏感样本，覆盖：
  - 订单状态、改地址、提前配送、忘记订单号。
  - 退款、已制作订单退款、退运费、退款到账。
  - 售后破损、漏发、投诉、名字写错、食品安全。
  - 实时库存、批量预订、预留、门店/小程序库存不一致、下架商品。
  - 商品价格、优惠价、定制报价、配送费、最低价。
  - 明确转人工、投诉、过敏、团购价格账期、订单退款复合场景。
- `scripts/check_customer_rag_golden_cases.py` 新增敏感场景覆盖检查，每类至少 5 条。
- `scripts/eval_customer_agent.py` 在 case metadata 中输出 `sensitive_scenarios`，后续作品集和报告可以直接展示治理覆盖。
- 本切片只扩展脱敏 eval 和机器检查，不改变客户热路径、prompt、工具执行或转人工策略。

P4a 验收：

```powershell
python scripts\check_customer_rag_golden_cases.py --summary
python scripts\eval_customer_agent.py --summary
python scripts\report_agent_eval.py --latest --json-out reports\agent-eval\latest.json
python -m pytest tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py tests\scripts\test_report_retrieval_eval_matrix.py tests\scripts\test_eval_retrieval.py -q --no-cov
python -m ruff check scripts\check_customer_rag_golden_cases.py scripts\eval_customer_agent.py tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py
python -m ruff format --check scripts\check_customer_rag_golden_cases.py scripts\eval_customer_agent.py tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py
python scripts\report_retrieval_eval_matrix.py --db data\bot.db --fixture tests\fixtures\customer_rag_golden_cases.json --k 5
```

P4a 验证结果：

```text
客户 golden cases 结构与敏感场景覆盖检查通过：83 项失败 0。
客户机器人 eval 通过：71 项失败 0。
双机器人聚合 eval 通过：133 项失败 0。
相关脚本与 eval 测试通过：26 项失败 0。
Ruff check 通过。
Ruff format --check 通过。
RAG 矩阵在 400 条启用知识、70 条可评估客户样本下可跑通。
hybrid: Recall@5=0.9857, MRR=0.8881。
planned-hybrid: Recall@5=0.9857, MRR=0.8881。
planned-hybrid+rerank: Recall@5=0.9714, MRR=0.9136。
```

P4 后续：

- P4b 已把 `sensitive_scenarios` 接入更明确的 guardrail 策略契约断言，例如订单必须禁止编造或要求人工/确认，退款必须禁止承诺或要求按订单状态确认，库存必须强调实时/门店/人工确认。
- P4c 再考虑在 trace 中记录事实敏感场景分类，但不记录敏感明文。

## 二十五、P4b 落地记录

2026-07-10 已完成 P4 事实敏感场景治理增强的第二切片：

- `scripts/check_customer_rag_golden_cases.py` 新增 `SENSITIVE_SCENARIO_POLICY_KEYWORDS`，集中定义 6 类事实敏感场景的 guardrail 策略契约：
  - `order`
  - `refund`
  - `after_sales`
  - `inventory`
  - `price`
  - `human_transfer`
- 每个带 `sensitive_scenarios` 的客户样本都必须在 `guardrails` 中命中对应场景的策略关键词组。
- `scripts/eval_customer_agent.py` 复用同一套策略契约，为每条敏感 case 输出 `sensitive_policy.<scenario>` 断言。
- P4b 过程中机器检查抓出 4 个 guardrail 缺口，已补强 3 条事实敏感样本文案：
  - 订单提前配送必须落到订单/人工确认。
  - 退运费必须明确退款/退运费不能承诺。
  - 退款到账时间必须明确不能编造并转人工或按支付平台确认。
- 本切片仍只强化脱敏 eval、fixture governance 和报告断言，不改变线上回复热路径。

P4b 验收：

```powershell
python -m pytest tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py -q --no-cov
python scripts\check_customer_rag_golden_cases.py --summary
python scripts\eval_customer_agent.py --summary
python scripts\report_agent_eval.py --latest --json-out reports\agent-eval\latest.json
python -m ruff check scripts\check_customer_rag_golden_cases.py scripts\eval_customer_agent.py tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py
python -m ruff format --check scripts\check_customer_rag_golden_cases.py scripts\eval_customer_agent.py tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py
python scripts\report_retrieval_eval_matrix.py --db data\bot.db --fixture tests\fixtures\customer_rag_golden_cases.json --k 5
```

P4b 验证结果：

```text
策略契约与 eval 脚本测试通过：12 项失败 0。
客户 golden cases 结构、覆盖与策略契约检查通过：130 项失败 0。
客户机器人 eval 通过：71 项失败 0。
双机器人聚合 eval 通过：133 项失败 0。
Ruff check 通过。
Ruff format --check 通过。
RAG 矩阵保持：hybrid Recall@5=0.9857、MRR=0.8881；planned-hybrid 持平；planned-hybrid+rerank Recall@5=0.9714、MRR=0.9136。
```

P4 后续：

- P4c 已在报告层记录事实敏感场景分类，只输出结构化标签、数量、失败数和通过率，不记录用户原文、订单号、手机号、地址或 open_id。
- P4d 可进一步增加“回复输出禁止行为”离线断言，例如订单场景不能出现编造状态、退款场景不能出现未验证承诺。

## 二十六、P4c 落地记录

2026-07-10 已完成 P4 事实敏感场景治理增强的第三切片：

- `app/service/agents/evaluation.py` 新增 `summarize_eval_cases_by_sensitive_scenario()`。
- 单 agent eval JSON 新增 `sensitive_scenarios`。
- 双机器人聚合 eval JSON 顶层新增 `sensitive_scenarios`。
- 汇总字段只包含：
  - `scenario`
  - `total`
  - `failed`
  - `passed`
  - `pass_rate`
- 本切片只记录结构化场景标签和统计，不记录用户原文、订单号、手机号、地址、open_id 或工具结果明文。

P4c 验收：

```powershell
python -m pytest tests\service\agents\test_evaluation.py tests\scripts\test_agent_eval_scripts.py -q --no-cov
python scripts\report_agent_eval.py --latest --json-out reports\agent-eval\latest.json
python -m ruff check app\service\agents\evaluation.py tests\service\agents\test_evaluation.py tests\scripts\test_agent_eval_scripts.py
python -m ruff format --check app\service\agents\evaluation.py tests\service\agents\test_evaluation.py tests\scripts\test_agent_eval_scripts.py
```

P4c 验证结果：

```text
Agent Eval 模型与脚本测试通过：10 项失败 0。
双机器人聚合 eval 通过：133 项失败 0。
Ruff check 通过。
Ruff format --check 通过。
JSON 抽查显示顶层与 customer agent 均包含：
after_sales 8、human_transfer 16、inventory 5、order 6、price 6、refund 6，失败数均为 0。
```

P4 后续：

- P4d 已增加“回复输出禁止行为”离线契约，订单、退款、售后、库存、价格和转人工场景均可派生 `forbidden_reply_patterns`，为后续真实回复回放断言做准备。
- P4e 再根据需要决定是否把事实敏感场景分类写入真实 trace，但必须保持脱敏，只写结构化标签。

## 二十七、P4d 落地记录

2026-07-10 已完成 P4 事实敏感场景治理增强的第四切片：

- `scripts/check_customer_rag_golden_cases.py` 新增 `SENSITIVE_SCENARIO_FORBIDDEN_REPLY_PATTERNS`。
- 禁止回复模式按 `sensitive_scenarios` 派生，不要求每条 fixture 重复维护：
  - 订单：禁止编造“已查到订单 / 正在制作 / 已发货 / 可以直接改订单”。
  - 退款：禁止承诺“全额退款 / 马上退款 / 一定退款 / 确定到账时间”。
  - 售后：禁止承诺“一定赔偿 / 一定补发 / 责任归属 / 可以继续食用”。
  - 库存：禁止承诺“一定有货 / 保证有货 / 已经预留 / 下架商品可做”。
  - 价格：禁止承诺“最低价 / 免配送费 / 直接优惠 / 定制固定价”。
  - 转人工：禁止说“不需要人工 / 无需转人工 / 我可以直接处理 / 不用客服确认”。
- `scripts/eval_customer_agent.py` 在每条敏感 case metadata 中输出 `forbidden_reply_patterns`。
- 客户 eval 新增 `forbidden_reply_patterns.present` 断言，保证后续真实回复回放可以直接使用这些模式做禁止输出检测。
- 本切片仍不调用 LLM、不改变线上回复，只补离线输出契约。

P4d 验收：

```powershell
python -m pytest tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py -q --no-cov
python scripts\check_customer_rag_golden_cases.py --summary
python scripts\eval_customer_agent.py --summary
python scripts\report_agent_eval.py --latest --json-out reports\agent-eval\latest.json
python -m ruff check scripts\check_customer_rag_golden_cases.py scripts\eval_customer_agent.py tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py
python -m ruff format --check scripts\check_customer_rag_golden_cases.py scripts\eval_customer_agent.py tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py
```

P4d 验证结果：

```text
禁止回复模式与 eval 脚本测试通过：13 项失败 0。
客户 golden cases 检查通过：136 项失败 0。
客户机器人 eval 通过：71 项失败 0。
双机器人聚合 eval 通过：133 项失败 0。
Ruff check 通过。
Ruff format --check 通过。
JSON 抽查 customer 敏感 case 已包含派生的 forbidden_reply_patterns。
```

P4 后续：

- P4e 可新增真实或 fake 回复回放脚本，把 `forbidden_reply_patterns` 应用于实际回复文本，验证“不当承诺/编造”不会出现在输出中。
- P4f 再决定是否把事实敏感场景分类写入真实 trace，仍只写结构化标签。

### 阶段 P5：作品集证据包

目标：把项目整理成求职可展示材料，不只是代码仓库。

改动范围：

- `docs/architecture/langchain-ai-layer-portfolio.md`
- `README.md`
- `docs/README.md`
- `reports/`
- 架构图或 Mermaid 图。

执行步骤：

1. 增加一页式项目说明：
   - 项目背景。
   - 技术栈。
   - LangChain 接管边界。
   - 业务事实边界。
   - eval 结果。
   - 生产验证结果。
2. 增加“迁移前后对比”：
   - 自研工具循环。
   - LangGraph 编排。
   - LangChain tools。
   - Retriever adapter。
   - structured output。
3. 增加“我少写了什么代码”：
   - 模型消息适配。
   - 工具 schema。
   - structured output 解析。
   - graph 状态流转。
   - retriever 标准接口。
   - eval 报告结构。
4. 增加“为什么没有让 LangChain 接管业务层”：
   - 数据真实性。
   - 可追溯性。
   - 订单/库存/退款风险。
   - repository 分层边界。
5. 增加面试问答版：
   - 为什么选 LangChain 而不是 LlamaIndex。
   - 为什么用了 LangGraph。
   - RAG 是什么范式。
   - 如何做 eval。
   - 如何保证客服回复可控。

验收命令：

```powershell
python scripts/report_agent_eval.py --latest
python scripts/report_retrieval_eval_matrix.py --db data/bot.db --fixture tests/fixtures/customer_rag_golden_cases.json --k 5
python scripts/check_text_encoding.py README.md docs/README.md docs/architecture/langchain-ai-layer-portfolio.md docs/architecture/langchain-ai-layer-production-enhancement-plan.md
git diff --check
```

完成标准：

- 面试官 3 分钟内能看懂项目价值。
- 技术栈不是堆名词，而是能映射到代码路径和验证命令。
- 每个关键能力都有证据：代码入口、eval 输出、生产探针或文档决策。

## 二十八、P5a 落地记录

2026-07-10 已完成 P5 作品集证据包的第一切片：

- `docs/architecture/langchain-ai-layer-portfolio.md` 更新为当前作品集证据包，覆盖 LangChain / LangGraph 接管边界、RAG retrieval mode gate、133 项双机器人 eval、RAG 矩阵、事实敏感治理矩阵、禁止回复契约、少写代码估算和面试问答。
- `README.md` 新增 LangChain / LangGraph AI 应用层作品集入口。
- `docs/README.md` 更新作品集文档描述，明确 133 项 eval、RAG 矩阵和事实敏感客服治理。
- 本切片只做文档与证据收口，不改客户机器人、员工助手、RAG、工具调用、数据库或生产配置。

P5a 验收：

```powershell
python scripts\report_agent_eval.py --latest --json-out reports\agent-eval\latest.json
python scripts\report_retrieval_eval_matrix.py --db data\bot.db --fixture tests\fixtures\customer_rag_golden_cases.json --k 5
python scripts\check_text_encoding.py README.md docs\README.md docs\architecture\langchain-ai-layer-portfolio.md docs\architecture\langchain-ai-layer-production-enhancement-plan.md LOGBOOK.md
git diff --check
```

P5a 验证结果：

```text
双机器人聚合 eval 通过：133 项失败 0。
客户机器人 eval 通过：71 项失败 0。
员工助手 eval 通过：62 项失败 0。
RAG 矩阵通过：400 条启用知识、70 条可评估客户样本；hybrid Recall@5=0.9857、MRR=0.8881，planned-hybrid 持平，planned-hybrid+rerank Recall@5=0.9714、MRR=0.9136。
文本编码检查通过。
git diff --check 通过，仅有 CRLF 工作区换行提醒。
```

P5 后续：

- P5b 可按需补一页式 PDF/Markdown 摘要，但仓库内作品集入口已经可从 README 追溯到代码路径、eval、RAG 和事实敏感治理证据。
- 下一阶段建议进入 P6：真实或 fake 客户回复回放，把 P4d 的 `forbidden_reply_patterns` 应用于最终回复文本，验证“不当承诺/编造”不会出现在输出中。

## 二十九、P6a 落地记录

2026-07-10 已完成 P6 客户回复回放安全检查的第一切片：

- 新增 `scripts/check_customer_reply_replay.py`，读取客户 RAG golden cases 中带 `sensitive_scenarios` 的事实敏感 case，并复用 P4d 的 `build_forbidden_reply_patterns()` 检查最终回复文本。
- 脚本支持默认安全假回复和外部 `--replies-json` 两种来源：
  - 默认安全假回复用于验证离线回放管线、报告结构和门禁脚本。
  - 外部 JSON 可接入后续真实脱敏回复、模型输出或生产回放结果。
- 报告继续使用通用 Agent Eval 模型，支持 `--summary`、`--json`、`--json-out`、`--case-id` 和 `--fail-fast`。
- 本切片不接入客户热路径，不调用线上 LLM，不写数据库，不改变 RAG、工具调用、转人工或生产配置。

P6a 验收：

```powershell
python -m pytest tests\scripts\test_agent_eval_scripts.py -q --no-cov
python -m ruff check scripts\check_customer_reply_replay.py tests\scripts\test_agent_eval_scripts.py
python -m ruff format --check scripts\check_customer_reply_replay.py tests\scripts\test_agent_eval_scripts.py
python scripts\check_customer_reply_replay.py --json-out reports\agent-eval\customer-reply-replay-latest.json --summary
```

P6a 验证结果：

```text
脚本测试通过：9 项失败 0。
Ruff check 通过。
Ruff format --check 通过。
客户回复回放安全检查通过：30 条事实敏感 case 失败 0。
```

P6 后续：

- P6b 可把客户 graph 的受控 fake model 输出接入 `--replies-json`，验证真实 prompt/finalizer 生成的回复文本，而不调用外部 LLM。
- P6c 再接入脱敏真实会话或生产 shadow 回复，形成“真实问题 -> 最终回复 -> forbidden pattern 断言”的回归资产。

## 三十、P6b 落地记录

2026-07-10 已完成 P6 客户 graph 回复回放探针：

- 新增 `scripts/probe_customer_reply_replay.py`，复用 `CustomerAgentGraphService.answer_with_trace()` 对 30 条事实敏感客户 case 生成 replies JSON。
- 探针通过 monkeypatch 客户模型请求为受控 fake model，并禁用客户工具注册；因此不调用外部 LLM、不访问真实数据库、不发送消息。
- 探针输出可直接作为 P6a `scripts/check_customer_reply_replay.py --replies-json` 输入，完成“客户 graph 输出 -> 最终回复文本 -> forbidden pattern 断言”的离线闭环。
- 本切片不改变客户机器人线上热路径、RAG、工具调用、转人工或生产配置。

P6b 验收：

```powershell
python -m pytest tests\scripts\test_probe_customer_reply_replay.py tests\scripts\test_agent_eval_scripts.py -q --no-cov
python -m ruff check scripts\probe_customer_reply_replay.py scripts\check_customer_reply_replay.py tests\scripts\test_probe_customer_reply_replay.py tests\scripts\test_agent_eval_scripts.py
python -m ruff format --check scripts\probe_customer_reply_replay.py scripts\check_customer_reply_replay.py tests\scripts\test_probe_customer_reply_replay.py tests\scripts\test_agent_eval_scripts.py
python scripts\probe_customer_reply_replay.py --output reports\agent-eval\customer-reply-replay-probe-latest.json; python scripts\check_customer_reply_replay.py --replies-json reports\agent-eval\customer-reply-replay-probe-latest.json --json-out reports\agent-eval\customer-reply-replay-latest.json --summary
```

P6b 验证结果：

```text
脚本测试通过：11 项失败 0。
Ruff check 通过。
Ruff format --check 通过。
客户 graph fake model 回复回放生成成功，P6a 检查通过：30 条事实敏感 case 失败 0。
```

P6 后续：

- P6c 可从脱敏真实客服会话或生产 shadow 输出生成 `--replies-json`，让同一套检查覆盖真实问题分布。
- P6d 可把 `check_customer_reply_replay.py` 接入聚合 Agent Eval 报告，形成 `customer_reply_replay` agent 维度。

## 三十一、P6d 落地记录

2026-07-10 已完成 P6 回复回放并入聚合 Agent Eval：

- `scripts/report_agent_eval.py` 新增 `customer_reply_replay` agent 维度。
- 默认 `python scripts\report_agent_eval.py --latest` 仍只聚合客户 RAG eval 和员工助手 eval，保持 133 项基线不变。
- 显式传入 `--include-reply-replay` 时，聚合报告额外包含客户回复回放检查，当前总数为 163 项。
- 支持 `--reply-replay-json` 传入 P6b 生成的 graph fake model replies JSON；报告 metadata 输出 `include_reply_replay` 和 `reply_replay_source`。
- 本切片仍不调用外部 LLM、不改客户热路径、不写数据库、不改变生产配置。

P6d 验收：

```powershell
python -m pytest tests\scripts\test_agent_eval_scripts.py tests\scripts\test_probe_customer_reply_replay.py -q --no-cov
python -m ruff check scripts\report_agent_eval.py tests\scripts\test_agent_eval_scripts.py
python -m ruff format --check scripts\report_agent_eval.py tests\scripts\test_agent_eval_scripts.py
python scripts\report_agent_eval.py --latest --summary
python scripts\probe_customer_reply_replay.py --output reports\agent-eval\customer-reply-replay-probe-latest.json; python scripts\report_agent_eval.py --latest --include-reply-replay --reply-replay-json reports\agent-eval\customer-reply-replay-probe-latest.json --json-out reports\agent-eval\latest-with-reply-replay.json --summary
```

P6d 验证结果：

```text
脚本测试通过：13 项失败 0。
Ruff check 通过。
Ruff format --check 通过。
默认聚合 eval 通过：133 项失败 0。
扩展聚合 eval 通过：163 项失败 0，其中包含 30 条 customer_reply_replay 回复回放检查。
```

P6 后续：

- P6c/P6e 可继续接入脱敏真实客服会话或生产 shadow replies JSON，让 `customer_reply_replay` 从 fake model 逐步走向真实问题分布。
- 可在 P10 发布门禁中增加 `report_agent_eval.py --include-reply-replay` 作为加强验收，而不是替代默认 133 项基线。

## 三十二、P10a 落地记录

2026-07-10 已完成 P10 生产级发布门禁的第一切片：

- 新增 `scripts/check_langchain_ai_layer_release_gate.py`，作为 LangChain AI 应用层发布前聚合门禁。
- 默认门禁串联：
  - 默认双机器人 Agent Eval，保持 133 项基线。
  - 客户 graph fake model 回复回放 probe。
  - 带 `customer_reply_replay` 的扩展 Agent Eval，当前 163 项。
- 加强门禁通过 `--include-rag-matrix` 额外运行 RAG 检索矩阵，适合发布前或作品集证据刷新。
- 脚本对子进程输出使用 `errors="replace"`，避免 embedding / jieba / tqdm 等第三方库的控制台编码噪声导致门禁崩溃。
- 脚本会提前创建报告父目录，避免 RAG 矩阵 JSON 输出目录不存在。
- 本切片不改客户或员工热路径，不调用线上 LLM，不写业务数据库。

P10a 验收：

```powershell
python -m pytest tests\scripts\test_check_langchain_ai_layer_release_gate.py -q --no-cov
python -m ruff check scripts\check_langchain_ai_layer_release_gate.py tests\scripts\test_check_langchain_ai_layer_release_gate.py
python -m ruff format --check scripts\check_langchain_ai_layer_release_gate.py tests\scripts\test_check_langchain_ai_layer_release_gate.py
python scripts\check_langchain_ai_layer_release_gate.py --json-out reports\agent-eval\langchain-ai-layer-release-gate-latest.json --summary
python scripts\check_langchain_ai_layer_release_gate.py --include-rag-matrix --json-out reports\agent-eval\langchain-ai-layer-release-gate-with-rag-latest.json --summary
```

P10a 验证结果：

```text
脚本测试通过：6 项失败 0。
Ruff check 通过。
Ruff format --check 通过。
默认 release gate 通过：3 步失败 0。
加强 release gate 通过：4 步失败 0，包含 RAG 检索矩阵。
```

P10 后续：

- P10b 已把 release gate 输出和生产 `/health`、`/ready`、callback probe 合并成生产同步前门禁。
- P10c 可在需要时把 `--include-rag-matrix` 的核心指标抽取成结构化 release summary，便于面试或上线报告直接引用。

## 三十三、P10b 落地记录

2026-07-10 已完成 P10 生产级发布门禁的第二切片：

- `scripts/check_langchain_ai_layer_release_gate.py` 新增显式 `--include-production-smoke` 和 `--production-base-url`。
- 默认 release gate 仍只跑本地 AI 层门禁，不访问生产服务。
- 显式生产门禁会在默认 3 步之后追加：
  - `scripts/smoke_test.py --http-only --base-url <url> --json --output reports/smoke/langchain-prod-smoke-{timestamp}.json`
  - `scripts/check_wecom_employee_agent_callback.py --base-url <url> --json --output reports/wecom-employee-agent/langchain-prod-callback-{timestamp}.json`
- `scripts/smoke_test.py` 新增 `--http-only`，只检查服务端口可达、`/health` 和 `/ready`，不读取本地数据库、向量、`.env`、生产通道配置或后台 dist，避免本地静态配置被误判为远程生产失败。
- 本切片只编排已有只读探针，不改客户或员工热路径，不写业务数据库，不重启生产服务。

P10b 验收：

```powershell
python -m pytest tests\scripts\test_smoke_test.py tests\scripts\test_check_langchain_ai_layer_release_gate.py -q --no-cov
python -m ruff check scripts\smoke_test.py scripts\check_langchain_ai_layer_release_gate.py tests\scripts\test_smoke_test.py tests\scripts\test_check_langchain_ai_layer_release_gate.py
python -m ruff format --check scripts\smoke_test.py scripts\check_langchain_ai_layer_release_gate.py tests\scripts\test_smoke_test.py tests\scripts\test_check_langchain_ai_layer_release_gate.py
python scripts\check_langchain_ai_layer_release_gate.py --json-out reports\agent-eval\langchain-ai-layer-release-gate-latest.json --summary
python scripts\check_langchain_ai_layer_release_gate.py --include-production-smoke --production-base-url https://yunxifood.cn --json-out reports\agent-eval\langchain-ai-layer-release-gate-prod-latest.json --summary
```

P10b 验证结果：

```text
smoke/release gate 脚本测试通过：59 项失败 0。
Ruff check 通过。
Ruff format --check 通过。
默认 release gate 通过：3 步失败 0。
显式生产 release gate 已跑通到生产 callback 阶段：本地 133 eval、客户 graph 回复回放 probe、扩展 163 eval、生产 http-only smoke 均通过；生产 callback probe 在当前线上 0.85.2 返回 61 项中 2 项语义失败。
```

P10b 残余风险：

- 本次显式生产门禁访问到的线上 `/health` 和 `/ready` 版本为 `0.85.2`，低于本地当前 `0.89.0`；因此 callback 语义失败不能视为当前代码部署后的最终结论。
- 失败 case 为 `p2c-today-wait-buyer-confirm-list` 和 `p2c-refund-policy-knowledge`：前者受生产当天待收货订单数据波动影响，后者暴露生产员工知识库退款规则未命中或旧版本检索行为不足。
- 后续完成部署或生产知识补齐后，应复跑 `--include-production-smoke`，并将通过报告登记为正式发布证据。

## 五、推荐执行顺序

推荐顺序如下：

```text
P0 生产上线验证闭环
  -> P1 线上 Trace 与 LangSmith 观测
  -> P2 真实业务 Eval 数据集扩容
  -> P3 RAG 热路径灰度增强
  -> P4 事实敏感场景治理增强
  -> P5 作品集证据包
```

理由：

1. 先证明能在线上跑，再继续增强。
2. 先有 trace，后面才能解释线上问题。
3. 先有真实 eval，再灰度 RAG 高级能力。
4. 先治理事实敏感场景，再包装作品集，避免只有表面材料。

## 六、验收矩阵

| 阶段 | 最低验收 | 加强验收 | 是否改热路径 |
|---|---|---|---|
| P0 | `/health`、`/ready`、callback probe | 客户 RAG 与员工助手正向探针 | 否 |
| P1 | trace 报告可生成 | LangSmith 可选接入且不影响主流程 | 低风险 |
| P2 | eval cases 扩容并可定位失败 | report 支持 JSON 归档和 case filter | 否 |
| P3 | shadow compare 可运行 | planned/rerank 灰度优于稳定模式 | 是，需 feature flag |
| P4 | 敏感场景断言通过 | 每类场景至少 5 个真实脱敏 cases | 是，需回滚策略 |
| P5 | 作品集文档完整 | 有生产证据、eval 证据和架构图 | 否 |

## 七、风险与控制

| 风险 | 控制方式 |
|---|---|
| LangChain / LangSmith 依赖增加生产内存压力 | 继续保持懒加载；每次生产前运行 capacity probe |
| RAG 高级模式影响线上回复 | 默认关闭；先 shadow compare，再灰度 |
| Eval 样本过少导致虚高 | 引入真实脱敏问题，按业务场景扩容 |
| Trace 泄露敏感信息 | 统一脱敏字段；报告默认不输出手机号、地址、open_id |
| 作品集只像包装 | 每个亮点必须对应代码路径和验收命令 |

## 八、每阶段收口格式

每个阶段完成后按固定格式追加到 LOGBOOK：

```text
## [日期] - feat/docs/ops(...): 阶段名称
- trace_id:
- 背景:
- 决策:
- 改动:
- 验证结果:
- 证据路径:
- 后续:
```

需要生产证据时，同时登记到：

```text
docs/harness-engineering/core/evidence-index.md
```

## 九、下一步建议

下一步建议直接进入阶段 P0：

```text
目标：把当前 LangChain AI 应用层接管成果同步到生产，并完成 health / ready / callback / 客户 RAG / 员工助手正向探针。
```

P0 不应再扩功能。它的价值是把“代码已经完成”变成“真实服务器已经验证”的证据。

## 十、P0 落地记录

2026-07-09 已完成 P0 生产上线验证闭环首轮：

- 本地 commit `0fa3f18431c30620b58cd3e0e48251aa32b72a52` 已推送到 `origin/master` 和 `server/master`。
- 生产服务器 `/opt/yunxibakebot` 已位于 `0fa3f18431 fix: stabilize employee callback stock probes`。
- `systemctl restart yunxibakebot` 后服务为 `active`。
- `https://yunxifood.cn/health` 返回 `status=ok, version=0.85.2`。
- `https://yunxifood.cn/ready` 返回 `status=ready, version=0.85.2`，企微、智能机器人、handoff staff、后台前端和数据库等 readiness 检查均为 true。
- `python scripts/check_wecom_employee_agent_callback.py --base-url https://yunxifood.cn --json --output reports/wecom-employee-agent/langchain-prod-callback-20260709-2210.json` 通过，48 项失败 0。
- 首次 callback 失败集中在商品库存语义探针：生产实时库存已从本地固定样本变化，且 `招牌牛奶吐司` 在生产已下架。已将探针从固定库存数字 `72` 调整为动态库存治理口径，并允许“在售零库存”和“已下架未命中”两种安全结果。

P0 后续：

- 当前 P0 已证明生产运行版本和员工助手回调探针通过。
- 下一阶段应进入 P1：线上 Trace 与 LangSmith 观测。

## 十一、P1a 落地记录

2026-07-09 已完成 P1 线上 Trace 与 LangSmith 观测的第一切片：

- 新增 `app/service/agents/trace_report.py`，把本地 `trace_events` 聚合为双机器人 Agent trace 报告，统计 agent、node、event、fallback、tool call、knowledge hit 和平均耗时。
- 扩展 `app/service/agents/observability.py`，新增递归脱敏函数 `safe_trace_payload()`，统一过滤 `open_id`、`phone`、`mobile`、`address`、token、密钥、消息原文、历史记录、客户画像和工具结果等敏感字段。
- 新增 `scripts/report_agent_traces.py`，支持 `--input` 读取指定 trace JSON、`--latest` 读取 `reports/agent-traces/` 最新 JSON、`--summary` 和 `--json` 两种输出。
- 新增 `tests/service/agents/test_trace_report.py` 和 `tests/scripts/test_report_agent_traces.py`，覆盖客户机器人和员工助手双 agent 摘要、fallback 计数、工具调用计数、RAG 命中计数、敏感字段脱敏和 CLI 输出。
- 本切片不改客户/员工 graph 热路径，不写业务表，不引入 LangSmith 外发，不导入 `langchain_openai`、`langgraph` 或 `langsmith`。

P1a 验收：

```powershell
python -m pytest tests/service/agents/test_observability.py tests/service/agents/test_trace_report.py tests/scripts/test_report_agent_traces.py -q --no-cov
python -m ruff check app/service/agents/observability.py app/service/agents/trace_report.py scripts/report_agent_traces.py tests/service/agents/test_observability.py tests/service/agents/test_trace_report.py tests/scripts/test_report_agent_traces.py
python -m ruff format --check app/service/agents/observability.py app/service/agents/trace_report.py scripts/report_agent_traces.py tests/service/agents/test_observability.py tests/service/agents/test_trace_report.py tests/scripts/test_report_agent_traces.py
python scripts/report_agent_traces.py --latest --summary
```

P1a 验证结果：

```text
18 项 targeted tests 通过。
Ruff check 通过。
Ruff format --check 通过。
当前本地 reports/agent-traces/ 暂无 trace JSON 时，脚本稳定输出：agent_traces status=no_traces total_runs=0 agents=0。
```

P1 后续：

- P1b 应把真实 graph 运行后的 `trace_events` 显式导出为可序列化的 `AgentTraceRun`，使 eval、运维脚本或手动探针可以安全写入 `reports/agent-traces/`。
- P1c 再补客户和员工节点字段完整度：`trace_id`、`model`、`tool_name`、`knowledge_entry_ids`、`latency_ms`、`fallback_reason`。
- LangSmith 仍保持可选开关，未配置 key 时不得影响主流程。

## 十二、P1b 落地记录

2026-07-09 已完成 P1 线上 Trace 与 LangSmith 观测的第二切片：

- `CustomerAgentGraphService` 新增 `answer_with_trace()`，返回 `(reply, AgentTraceRun)`；原 `answer()` 保持只返回字符串，外部调用方行为不变。
- `EmployeeAgentGraphService` 新增 `answer_with_trace()`，返回 `(reply, AgentTraceRun)`；原 `answer()` 保持只返回确定性回复。
- `AgentTraceRun` 新增 `to_dict()`，序列化时自动通过 `safe_trace_payload()` 过滤敏感字段，后续 eval 或运维探针可直接写入 JSON。
- 客户 trace run 写入 `agent=customer`、`conversation_id=session.id`、`channel=session.channel`、`final_status` 和节点事件。
- 员工 trace run 写入 `agent=employee`、`channel=wecom_employee`、`final_status` 和节点事件。
- 本切片不默认写 `reports/agent-traces/`，避免生产热路径每条消息产生文件；真实落盘应由显式探针、eval 或后续结构化日志配置触发。

P1b 验收：

```powershell
python -m pytest tests/service/agents/test_customer_graph.py tests/service/agents/test_employee_graph.py tests/service/agents/test_trace_report.py tests/scripts/test_report_agent_traces.py tests/service/agents/test_observability.py -q --no-cov
python -m ruff check app/service/agents/customer/service.py app/service/agents/employee/service.py app/service/agents/trace_report.py app/service/agents/observability.py scripts/report_agent_traces.py tests/service/agents/test_customer_graph.py tests/service/agents/test_employee_graph.py tests/service/agents/test_trace_report.py tests/scripts/test_report_agent_traces.py tests/service/agents/test_observability.py
python -m ruff format --check app/service/agents/customer/service.py app/service/agents/employee/service.py app/service/agents/trace_report.py app/service/agents/observability.py scripts/report_agent_traces.py tests/service/agents/test_customer_graph.py tests/service/agents/test_employee_graph.py tests/service/agents/test_trace_report.py tests/scripts/test_report_agent_traces.py tests/service/agents/test_observability.py
```

P1b 验证结果：

```text
33 项 targeted tests 通过。
Ruff check 通过。
Ruff format --check 通过。
```

P1 后续：

- P1d 再决定是否增加显式探针脚本，把一次客户机器人和一次员工助手运行写入 `reports/agent-traces/` 后用 `scripts/report_agent_traces.py --latest --summary` 汇总。

## 十三、P1c 落地记录

2026-07-09 已完成 P1 线上 Trace 与 LangSmith 观测的第三切片：

- 客户模型 adapter 的 `CustomerModelResult` 新增 `model_name`，模型节点 trace 可记录实际使用模型。
- 客户 `load_session_context` trace 新增 `latency_ms`、`knowledge_entry_ids`、`knowledge_hit_count`，字段来自 RAG 上下文构造结果，不包含知识正文或用户原文。
- 客户 `model_with_tools` trace 新增 `model`、`latency_ms`、`tool_call_count`，fallback 时额外记录 `fallback_reason`。
- 客户 `execute_tools` trace 新增 `tool_name`、`tool_names`、`tool_call_count`。
- 员工 `select_tools` 和 `execute_tools` trace 新增 `tool_name`、`tool_call_count`，`deterministic_finalizer` trace 新增 `final_status=success`。
- `ChatContext` 新增 `knowledge_entry_ids`，只把知识 ID 写入 timing，不把知识正文、客户画像或历史消息写入 trace。

P1c 验收：

```powershell
python -m pytest tests/service/agents/test_customer_model.py tests/service/agents/test_customer_graph.py tests/service/agents/test_employee_graph.py tests/service/agents/test_trace_report.py tests/service/test_chat_refactor.py -q --no-cov
python -m ruff check app/service/agents/customer/model.py app/service/chat_context.py app/service/agents/customer/nodes.py app/service/agents/employee/nodes.py tests/service/agents/test_customer_model.py tests/service/agents/test_customer_graph.py tests/service/agents/test_employee_graph.py
python -m ruff format --check app/service/agents/customer/model.py app/service/chat_context.py app/service/agents/customer/nodes.py app/service/agents/employee/nodes.py tests/service/agents/test_customer_model.py tests/service/agents/test_customer_graph.py tests/service/agents/test_employee_graph.py
```

P1c 验证结果：

```text
46 项 targeted tests 通过。
Ruff check 通过。
Ruff format --check 通过。
```

P1 后续：

- P1e 若需要线上 LangSmith，单独处理环境变量注入和生产容量探针，仍保持缺 key 不影响主流程。

## 十四、P1d 落地记录

2026-07-09 已完成 P1 线上 Trace 与 LangSmith 观测的第四切片：

- 新增 `scripts/probe_agent_traces.py`，使用受控 fake 依赖运行一次客户机器人 graph 和一次员工助手 graph，不访问真实数据库、不调用外部 LLM、不发送企微消息。
- probe 通过 `answer_with_trace()` 收集 `AgentTraceRun`，写入 `reports/agent-traces/agent-traces-{timestamp}.json`。
- `scripts/report_agent_traces.py --latest --summary` 现在可以读取最新 probe 输出，并展示客户机器人和员工助手节点级摘要。
- 新增 `tests/scripts/test_probe_agent_traces.py`，覆盖 probe 输出 JSON 结构和 report 脚本读取链路。

P1d 验收：

```powershell
python -m pytest tests/scripts/test_probe_agent_traces.py tests/scripts/test_report_agent_traces.py -q --no-cov
python -m ruff check scripts/probe_agent_traces.py tests/scripts/test_probe_agent_traces.py scripts/report_agent_traces.py tests/scripts/test_report_agent_traces.py
python -m ruff format --check scripts/probe_agent_traces.py tests/scripts/test_probe_agent_traces.py scripts/report_agent_traces.py tests/scripts/test_report_agent_traces.py
python scripts/probe_agent_traces.py
python scripts/report_agent_traces.py --latest --summary
python scripts/report_agent_traces.py --latest --json
```

P1d 验证结果：

```text
5 项 targeted tests 通过。
Ruff check 通过。
Ruff format --check 通过。
probe 输出 reports/agent-traces/agent-traces-20260709-224837.json。
summary 输出：agent_traces status=ok total_runs=2 agents=2。
json 输出包含 customer 4 个节点、employee 7 个节点，未包含敏感明文字段。
```

P1 当前状态：

- P1 的本地 trace 报告、显式 trace 导出、节点字段补齐和本地 probe 闭环已完成。
- LangSmith 仍是可选配置能力，当前未做生产环境变量注入和外发验证；这部分应在需要线上 LangSmith 时单独做容量探针和生产配置确认。
