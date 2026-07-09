
## E-20260710-005：LangChain AI 应用层 P4c 事实敏感场景报告汇总

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-10
- evidence_type: local/p4c-sensitive-scenario-report-summary
- file: `D:\Project\YunxiBakeBot\app\service\agents\evaluation.py`; `D:\Project\YunxiBakeBot\tests\service\agents\test_evaluation.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_agent_eval_scripts.py`; `D:\Project\YunxiBakeBot\reports\agent-eval\latest.json`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\service\agents\test_evaluation.py tests\scripts\test_agent_eval_scripts.py -q --no-cov`; `python scripts\report_agent_eval.py --latest --json-out reports\agent-eval\latest.json`; `python -m ruff check app\service\agents\evaluation.py tests\service\agents\test_evaluation.py tests\scripts\test_agent_eval_scripts.py`; `python -m ruff format --check app\service\agents\evaluation.py tests\service\agents\test_evaluation.py tests\scripts\test_agent_eval_scripts.py`; JSON 抽查 `sensitive_scenarios`
- result: pass
- related_logbook: 2026-07-10 - feat(eval): 增加 P4c 事实敏感场景报告汇总
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: 本轮只登记结构化场景标签、数量、失败数和通过率；不包含真实客户原文、订单号、手机号、地址、open_id 或密钥；`reports\agent-eval\latest.json` 位于 gitignored reports 目录。
- summary: P4c 在通用 Agent Eval 模型层新增事实敏感场景汇总，单 agent 与双机器人聚合报告均输出 `sensitive_scenarios`。当前报告显示 after_sales 8、human_transfer 16、inventory 5、order 6、price 6、refund 6，失败数均为 0；双机器人聚合 eval 继续通过 133/133。

## E-20260710-004：LangChain AI 应用层 P4b 事实敏感策略契约断言

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-10
- evidence_type: local/p4b-customer-sensitive-policy-contracts
- file: `D:\Project\YunxiBakeBot\scripts\check_customer_rag_golden_cases.py`; `D:\Project\YunxiBakeBot\scripts\eval_customer_agent.py`; `D:\Project\YunxiBakeBot\tests\fixtures\customer_rag_golden_cases.json`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_customer_rag_golden_cases.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_agent_eval_scripts.py`; `D:\Project\YunxiBakeBot\reports\agent-eval\latest.json`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py -q --no-cov`; `python scripts\check_customer_rag_golden_cases.py --summary`; `python scripts\eval_customer_agent.py --summary`; `python scripts\report_agent_eval.py --latest --json-out reports\agent-eval\latest.json`; `python -m ruff check scripts\check_customer_rag_golden_cases.py scripts\eval_customer_agent.py tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py`; `python -m ruff format --check scripts\check_customer_rag_golden_cases.py scripts\eval_customer_agent.py tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py`; `python scripts\report_retrieval_eval_matrix.py --db data\bot.db --fixture tests\fixtures\customer_rag_golden_cases.json --k 5`
- result: pass
- related_logbook: 2026-07-10 - feat(eval): 增加 P4b 事实敏感策略契约断言
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: 本轮只登记脱敏 fixture、策略关键词契约、eval 报告结构和汇总指标；不包含真实客户原文、订单号、手机号、地址、open_id 或密钥；`reports\agent-eval\latest.json` 位于 gitignored reports 目录。
- summary: P4b 将 P4a 的 `sensitive_scenarios` 标签升级为可机器检查的策略契约。订单、退款、售后、库存、价格、转人工 6 类高风险场景均要求 guardrails 命中对应策略关键词组；客户 eval 对每条敏感 case 输出 `sensitive_policy.<scenario>` 断言。客户 golden cases 检查通过 130/130，客户 eval 通过 71/71，双机器人聚合 eval 通过 133/133。

## E-20260710-003：LangChain AI 应用层 P4a 客户事实敏感场景 eval 扩容

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-10
- evidence_type: local/p4a-customer-sensitive-eval-expansion
- file: `D:\Project\YunxiBakeBot\tests\fixtures\customer_rag_golden_cases.json`; `D:\Project\YunxiBakeBot\scripts\check_customer_rag_golden_cases.py`; `D:\Project\YunxiBakeBot\scripts\eval_customer_agent.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_customer_rag_golden_cases.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_agent_eval_scripts.py`; `D:\Project\YunxiBakeBot\reports\agent-eval\latest.json`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python scripts\check_customer_rag_golden_cases.py --summary`; `python scripts\eval_customer_agent.py --summary`; `python scripts\report_agent_eval.py --latest --json-out reports\agent-eval\latest.json`; `python -m pytest tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py tests\scripts\test_report_retrieval_eval_matrix.py tests\scripts\test_eval_retrieval.py -q --no-cov`; `python -m ruff check scripts\check_customer_rag_golden_cases.py scripts\eval_customer_agent.py tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py`; `python -m ruff format --check scripts\check_customer_rag_golden_cases.py scripts\eval_customer_agent.py tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py`; `python scripts\report_retrieval_eval_matrix.py --db data\bot.db --fixture tests\fixtures\customer_rag_golden_cases.json --k 5`
- result: pass
- related_logbook: 2026-07-10 - feat(eval): 扩充 P4a 客户事实敏感场景样本
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: 新增样本为脱敏合成客服问法和治理断言，不包含真实客户原文、订单号、手机号、地址、open_id 或密钥；`reports\agent-eval\latest.json` 位于 gitignored reports 目录。
- summary: P4a 将客户 RAG golden cases 从 40 条业务样本扩展到 70 条，新增 `sensitive_scenarios` 标签和每类至少 5 条的机器检查，覆盖订单、退款、售后、库存、价格和转人工 6 类事实敏感场景。客户 eval 通过 71/71，双机器人聚合 eval 通过 133/133；70 条可评估客户样本下 hybrid Recall@5=0.9857、MRR=0.8881，planned-hybrid 持平，planned-hybrid+rerank Recall@5=0.9714、MRR=0.9136。

## E-20260710-002：LangChain AI 应用层 P3e RAG 检索模式热路径门禁

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-10
- evidence_type: local/p3e-rag-retrieval-mode-hot-path-gate
- file: `D:\Project\YunxiBakeBot\app\service\chat_context.py`; `D:\Project\YunxiBakeBot\app\service\agents\rag\documents.py`; `D:\Project\YunxiBakeBot\tests\service\test_chat_refactor.py`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\service\test_chat_refactor.py tests\service\agents\test_rag_retriever.py -q --no-cov`; `python -m ruff check app\service\chat_context.py app\service\agents\rag\documents.py tests\service\test_chat_refactor.py`; `python -m ruff format --check app\service\chat_context.py app\service\agents\rag\documents.py tests\service\test_chat_refactor.py`; `python scripts\eval_customer_agent.py --summary`; `$env:RAG_RETRIEVAL_MODE='planned-hybrid'; python scripts\eval_customer_agent.py --summary; Remove-Item Env:\RAG_RETRIEVAL_MODE`; `python scripts\report_retrieval_eval_matrix.py --db data\bot.db --fixture tests\fixtures\customer_rag_golden_cases.json --k 5`
- result: pass
- related_logbook: 2026-07-10 - feat(rag): 接入 P3e RAG 检索模式热路径门禁
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: 本轮只登记 RAG 热路径门禁代码、脱敏 eval 命令和汇总指标；不包含真实客户原文、订单明细、手机号、地址、open_id 或密钥。
- summary: P3e 将 `RAG_RETRIEVAL_MODE` 接入客户 RAG 热路径。默认 `hybrid` 仍直接调用原 `KnowledgeRetriever.search()`，保持生产稳定路径；`planned-hybrid` 和 `planned-hybrid-rerank` 才通过 LangChain retriever adapter 进入 query planning / rerank 编排，并把 Document 还原为现有 `KnowledgeEntry`。客户 eval 默认模式与 `planned-hybrid` 环境变量模式均 41/41 通过；检索矩阵显示 planned-hybrid 与 hybrid 持平，planned-hybrid+rerank 仍低于 baseline。

## E-20260710-001：LangChain AI 应用层 P3d RAG shadow compare 显式探针

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-10
- evidence_type: local/p3d-rag-shadow-compare-probe
- file: `D:\Project\YunxiBakeBot\scripts\report_retrieval_shadow_compare.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_report_retrieval_shadow_compare.py`; `D:\Project\YunxiBakeBot\reports\retrieval-shadow\latest.json`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\scripts\test_report_retrieval_shadow_compare.py tests\service\agents\test_rag_retriever.py -q --no-cov`; `python -m ruff check scripts\report_retrieval_shadow_compare.py tests\scripts\test_report_retrieval_shadow_compare.py`; `python -m ruff format --check scripts\report_retrieval_shadow_compare.py tests\scripts\test_report_retrieval_shadow_compare.py`; `python scripts\report_retrieval_shadow_compare.py --db data\bot.db --fixture tests\fixtures\customer_rag_golden_cases.json --k 5 --json-out reports\retrieval-shadow\latest.json`; `python scripts\report_retrieval_shadow_compare.py --db data\bot.db --fixture tests\fixtures\customer_rag_golden_cases.json --k 5 --candidate-mode planned-hybrid-rerank --json`
- result: pass
- related_logbook: 2026-07-10 - feat(rag): 增强 P3d 检索 shadow compare 显式探针
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: shadow compare 使用脱敏 fixture 和本地 SQLite 知识语料，仅登记 case id、query、group、top-k key/title、配置模式和汇总指标；不包含真实客户原文、订单明细、手机号、地址、open_id 或密钥；`reports\retrieval-shadow\latest.json` 位于 gitignored reports 目录。
- summary: P3d 将 RAG shadow compare 升级为显式运维探针，支持 `--baseline-mode` 和可重复 `--candidate-mode`，报告 metadata 记录当前 `RAG_RETRIEVAL_MODE`。真实 embedding 路径下，400 条启用知识、40 条客户样本的 baseline hybrid Recall@5=0.975、MRR=0.9437；planned-hybrid 持平；planned-hybrid+rerank Recall@5=0.95、MRR=0.9375。当前证据仍不支持热启 rerank。

## E-20260709-012：LangChain AI 应用层 P3c RAG 检索模式策略 helper

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-09
- evidence_type: local/p3c-rag-retrieval-mode-strategy
- file: `D:\Project\YunxiBakeBot\app\service\agents\rag\modes.py`; `D:\Project\YunxiBakeBot\tests\service\agents\test_rag_retriever.py`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\service\agents\test_rag_retriever.py -q --no-cov`; `python -m ruff check app\service\agents\rag\modes.py tests\service\agents\test_rag_retriever.py`; `python -m ruff format --check app\service\agents\rag\modes.py tests\service\agents\test_rag_retriever.py`; `python -c "import sys; import app.service.agents.rag.modes; print({name: (name in sys.modules) for name in ['langsmith','langchain_openai','langgraph','langchain_core']})"`
- result: pass
- related_logbook: 2026-07-09 - feat(rag): 增加 P3c 检索模式策略 helper
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: 本轮只登记 RAG 策略 helper、测试命令和冷导入结果，不包含真实客户原文、订单明细、手机号、地址、open_id 或密钥。
- summary: P3c 新增只读 RAG retrieval mode strategy/helper，把 `hybrid` 映射为稳定单查询，把 `planned-hybrid` 映射为 query planner，把 `planned-hybrid-rerank` 映射为 query planner + reranker。该 helper 尚未接入客户 graph 或线上回复，生产默认仍由现有稳定链路承载；冷导入 helper 不加载 LangChain 或 LangGraph 重依赖。

## E-20260709-011：LangChain AI 应用层 P3b RAG 检索模式配置门禁

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-09
- evidence_type: local/p3b-rag-retrieval-mode-config
- file: `D:\Project\YunxiBakeBot\app\config.py`; `D:\Project\YunxiBakeBot\tests\test_config.py`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\test_config.py -q --no-cov`; `python -m ruff check app\config.py tests\test_config.py`; `python -m ruff format --check app\config.py tests\test_config.py`; `python -c "import sys; import app.config; print({name: (name in sys.modules) for name in ['langsmith','langchain_openai','langgraph']})"`
- result: pass
- related_logbook: 2026-07-09 - feat(rag): 增加 P3b RAG 检索模式配置门禁
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: 本轮只登记配置字段、合法值和测试命令，不包含真实客户原文、订单明细、手机号、地址、open_id 或密钥。
- summary: P3b 新增 `RAG_RETRIEVAL_MODE` 配置门禁，默认保持 `hybrid`，允许 `hybrid`、`planned-hybrid` 和 `planned-hybrid-rerank`，非法值在 `Settings` 初始化时失败。该配置当前只完成解析和测试，不接入客户热路径、不改变生产回复；冷导入 `app.config` 不加载 `langsmith`、`langchain_openai` 或 `langgraph`。

## E-20260709-010：LangChain AI 应用层 P3a RAG shadow compare

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-09
- evidence_type: local/p3a-rag-shadow-compare
- file: `D:\Project\YunxiBakeBot\scripts\report_retrieval_shadow_compare.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_report_retrieval_shadow_compare.py`; `D:\Project\YunxiBakeBot\reports\retrieval-shadow\latest.json`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\scripts\test_report_retrieval_shadow_compare.py tests\scripts\test_report_retrieval_eval_matrix.py tests\scripts\test_eval_retrieval.py -q --no-cov`; `python scripts\report_retrieval_shadow_compare.py --db data\bot.db --fixture tests\fixtures\customer_rag_golden_cases.json --k 5 --json-out reports\retrieval-shadow\latest.json`
- result: pass
- related_logbook: 2026-07-09 - feat(rag): 增加 P3a 检索 shadow compare 报告
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: shadow compare 使用脱敏 fixture 和本地 SQLite 知识语料，仅登记 case id、query、group、top-k key/title 和汇总指标；不包含真实客户原文、订单明细、手机号、地址、open_id 或密钥；`reports\retrieval-shadow\latest.json` 位于 gitignored reports 目录。
- summary: P3a 新增离线 RAG shadow compare 报告，baseline 默认为 `hybrid`，候选为 `planned-hybrid` 与 `planned-hybrid+rerank`。在 `data\bot.db` 400 条启用知识、40 条可评估客户样本下，baseline hybrid Recall@5=0.975、MRR=0.9437；planned-hybrid 持平；planned-hybrid+rerank Recall@5=0.95、MRR=0.9375，说明当前不应直接热启 rerank，应继续以 shadow compare 收集差异。

## E-20260709-009：LangChain AI 应用层 P2d Agent Eval 分组统计

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-09
- evidence_type: local/p2d-agent-eval-report-metadata
- file: `D:\Project\YunxiBakeBot\app\service\agents\evaluation.py`; `D:\Project\YunxiBakeBot\tests\service\agents\test_evaluation.py`; `D:\Project\YunxiBakeBot\reports\agent-eval\latest.json`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\service\agents\test_evaluation.py tests\scripts\test_agent_eval_scripts.py -q --no-cov`; `python scripts\report_agent_eval.py --latest --json-out reports\agent-eval\latest.json`; JSON 抽查 `agent_totals`、顶层 `case_groups` 和每个 agent 的 `case_groups`
- result: pass
- related_logbook: 2026-07-09 - feat(eval): 增加 P2d Agent Eval 分组统计
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: 本轮只登记 eval 报告结构和分组统计，不包含真实客户原文、订单明细、手机号、地址、open_id 或密钥；`reports\agent-eval\latest.json` 位于 gitignored reports 目录。
- summary: P2d 为 Agent Eval JSON 增加作品集友好的统计字段：顶层 `agent_totals` 显示 customer 41 项、employee 62 项均通过；顶层 `case_groups` 汇总客户商品咨询、库存、配送、退款售后、转人工、知识未命中、员工 planner 和 capability contracts 等覆盖面；每个 agent 也单独输出 `case_groups`，后续 README/作品集可直接引用，无需人工二次统计。

## E-20260709-008：LangChain AI 应用层 P2c 员工助手 eval 样本扩容

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-09
- evidence_type: local/p2c-employee-eval-fixture-expansion
- file: `D:\Project\YunxiBakeBot\scripts\wecom_employee_agent_probe_cases.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_agent_eval_scripts.py`; `D:\Project\YunxiBakeBot\reports\agent-eval\latest.json`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python scripts\check_wecom_employee_agent_plans.py --json`; `python scripts\eval_employee_agent.py --summary`; `python scripts\report_agent_eval.py --latest --json-out reports\agent-eval\latest.json`; `python -m pytest tests\scripts\test_agent_eval_scripts.py::test_employee_eval_result_includes_planner_and_contracts -q --no-cov`
- result: pass
- related_logbook: 2026-07-09 - feat(eval): 扩充员工助手 P2c 离线 eval 样本
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: 新增样本为脱敏、合成化员工问法和结构化 planner 断言，不包含真实客户原文、订单号、手机号、地址、open_id 或密钥；`reports\agent-eval\latest.json` 位于 gitignored reports 目录。
- summary: P2c 将员工助手离线 eval 从 49 项提升到 62 项，其中 planner 探针从 48 条提升到 61 条；双机器人聚合 eval 提升到 `passed total=103 failed=0`。新增样本覆盖交易成功、已关闭、待收货、待发货、上午/下午约送、商品销量、精确订单详情、客户复购、退款规则、客户线索和 unsupported；不改线上 planner、工具执行或确定性 finalizer。

## E-20260709-007：LangChain AI 应用层 P2b 客户 eval 样本扩容

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-09
- evidence_type: local/p2b-customer-eval-fixture-expansion
- file: `D:\Project\YunxiBakeBot\tests\fixtures\customer_rag_golden_cases.json`; `D:\Project\YunxiBakeBot\scripts\check_customer_rag_golden_cases.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_customer_rag_golden_cases.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_agent_eval_scripts.py`; `D:\Project\YunxiBakeBot\reports\agent-eval\latest.json`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\scripts\test_check_customer_rag_golden_cases.py tests\scripts\test_agent_eval_scripts.py::test_customer_eval_result_uses_golden_cases -q --no-cov`; `python scripts\check_customer_rag_golden_cases.py --summary`; `python scripts\eval_customer_agent.py --summary`; `python scripts\report_agent_eval.py --agent customer --summary`; `python scripts\report_agent_eval.py --latest --json-out reports\agent-eval\latest.json`; `python scripts\report_retrieval_eval_matrix.py --db data\bot.db --fixture tests\fixtures\customer_rag_golden_cases.json --k 5`
- result: pass
- related_logbook: 2026-07-09 - feat(eval): 扩充客户机器人 P2b 脱敏 eval 样本
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: fixture 使用脱敏、合成化客户问法和治理断言，不包含真实客户原文、订单号、手机号、地址、open_id 或密钥；`reports\agent-eval\latest.json` 位于 gitignored reports 目录。
- summary: P2b 将客户 RAG golden cases 从 8 条业务样本扩充到 40 条业务样本，新增 `inventory` 与 `knowledge_no_match` required groups。客户 eval 当前 `passed total=41 failed=0`，双机器人聚合 eval 当前 `passed total=90 failed=0`。RAG 检索矩阵在 400 条启用知识、40 条客户标注样本下可跑通，best=hybrid，Recall@5=0.975，MRR=0.9437；这比旧小样本 1.0 更接近真实回归基线。

## E-20260709-006：LangChain AI 应用层 P2a eval runner 参数与 JSON 归档

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-09
- evidence_type: local/p2a-agent-eval-runner
- file: `D:\Project\YunxiBakeBot\app\service\agents\evaluation.py`; `D:\Project\YunxiBakeBot\scripts\eval_customer_agent.py`; `D:\Project\YunxiBakeBot\scripts\eval_employee_agent.py`; `D:\Project\YunxiBakeBot\scripts\report_agent_eval.py`; `D:\Project\YunxiBakeBot\tests\service\agents\test_evaluation.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_agent_eval_scripts.py`; `D:\Project\YunxiBakeBot\reports\agent-eval\latest.json`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\service\agents\test_evaluation.py tests\scripts\test_agent_eval_scripts.py -q --no-cov`; `python -m ruff check app\service\agents\evaluation.py scripts\eval_customer_agent.py scripts\eval_employee_agent.py scripts\report_agent_eval.py tests\service\agents\test_evaluation.py tests\scripts\test_agent_eval_scripts.py`; `python -m ruff format --check app\service\agents\evaluation.py scripts\eval_customer_agent.py scripts\eval_employee_agent.py scripts\report_agent_eval.py tests\service\agents\test_evaluation.py tests\scripts\test_agent_eval_scripts.py`; `python scripts\eval_customer_agent.py --summary`; `python scripts\eval_employee_agent.py --summary`; `python scripts\report_agent_eval.py --latest --json-out reports\agent-eval\latest.json`; `python scripts\report_agent_eval.py --agent customer --case-id customer-product-001 --summary`; `python scripts\report_agent_eval.py --agent employee --case-id employee.capability_contracts --json`
- result: pass
- related_logbook: 2026-07-09 - feat(eval): 完成 P2a eval runner 参数与 JSON 归档
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: 本轮只登记离线 eval case id、断言名、分组、工具名、报告摘要和 gitignored JSON 路径；不包含真实客户原文、订单明细、手机号、地址、open_id 或密钥。`reports\agent-eval\latest.json` 位于 gitignored reports 目录。
- summary: P2a 为客户、员工和双机器人聚合 eval runner 增加 `--case-id`、`--fail-fast`、`--json-out`，并为聚合报告增加 `--agent customer|employee|all`。`reports\agent-eval\latest.json` 归档结果为 `passed total=58 failed=0 pass_rate=1.0`，case filter 可将客户或员工报告收敛到单 case，后续 P2b/P2c 扩真实业务样本时可快速定位失败 case 与断言。

## E-20260709-005：LangChain AI 应用层 P1d 本地 trace probe 闭环

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-09
- evidence_type: local/p1d-agent-trace-probe
- file: `D:\Project\YunxiBakeBot\scripts\probe_agent_traces.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_probe_agent_traces.py`; `D:\Project\YunxiBakeBot\reports\agent-traces\agent-traces-20260709-224837.json`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\scripts\test_probe_agent_traces.py tests\scripts\test_report_agent_traces.py -q --no-cov`; `python -m ruff check scripts\probe_agent_traces.py tests\scripts\test_probe_agent_traces.py scripts\report_agent_traces.py tests\scripts\test_report_agent_traces.py`; `python -m ruff format --check scripts\probe_agent_traces.py tests\scripts\test_probe_agent_traces.py scripts\report_agent_traces.py tests\scripts\test_report_agent_traces.py`; `python scripts\probe_agent_traces.py`; `python scripts\report_agent_traces.py --latest --summary`; `python scripts\report_agent_traces.py --latest --json`
- result: pass
- related_logbook: 2026-07-09 - feat(observability): 完成 P1d 本地 trace probe 闭环
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: probe 使用受控 fake 依赖，不访问真实数据库、不调用外部 LLM、不发送企微消息；输出 JSON 位于 gitignored reports 目录，只包含节点名、模型名、耗时、工具数量、知识 ID 等结构化元数据，不包含真实客户原文、订单明细、手机号、地址或 open_id。
- summary: P1d 新增本地双机器人 trace probe，使用 `answer_with_trace()` 生成 customer 与 employee 两条 `AgentTraceRun` 并写入 `reports\agent-traces\agent-traces-20260709-224837.json`。`scripts\report_agent_traces.py --latest --summary` 返回 `agent_traces status=ok total_runs=2 agents=2`，JSON 汇总显示 customer 4 个节点、employee 7 个节点。P1 本地 trace 报告、显式导出、节点字段和 latest 报告闭环已具备。

## E-20260709-004：LangChain AI 应用层 P1c graph 节点 trace 字段补齐

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-09
- evidence_type: local/p1c-agent-trace-fields
- file: `D:\Project\YunxiBakeBot\app\service\agents\customer\model.py`; `D:\Project\YunxiBakeBot\app\service\chat_context.py`; `D:\Project\YunxiBakeBot\app\service\agents\customer\nodes.py`; `D:\Project\YunxiBakeBot\app\service\agents\employee\nodes.py`; `D:\Project\YunxiBakeBot\tests\service\agents\test_customer_model.py`; `D:\Project\YunxiBakeBot\tests\service\agents\test_customer_graph.py`; `D:\Project\YunxiBakeBot\tests\service\agents\test_employee_graph.py`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\service\agents\test_customer_model.py tests\service\agents\test_customer_graph.py tests\service\agents\test_employee_graph.py tests\service\agents\test_trace_report.py tests\service\test_chat_refactor.py -q --no-cov`; `python -m ruff check app\service\agents\customer\model.py app\service\chat_context.py app\service\agents\customer\nodes.py app\service\agents\employee\nodes.py tests\service\agents\test_customer_model.py tests\service\agents\test_customer_graph.py tests\service\agents\test_employee_graph.py`; `python -m ruff format --check app\service\agents\customer\model.py app\service\chat_context.py app\service\agents\customer\nodes.py app\service\agents\employee\nodes.py tests\service\agents\test_customer_model.py tests\service\agents\test_customer_graph.py tests\service\agents\test_employee_graph.py`
- result: pass
- related_logbook: 2026-07-09 - feat(observability): 补齐 P1c graph 节点 trace 字段
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: 本轮只登记结构化 trace 字段和验证命令；trace 字段记录模型名、耗时、工具名、工具数量、知识 ID、命中数量、fallback reason 和 final status，不包含用户消息、历史、客户画像、知识正文、工具结果明文、手机号、地址或 open_id。
- summary: P1c 补齐客户与员工 graph 节点 trace 字段。客户侧模型结果显式携带 `model_name`，load/model/tool 节点记录 RAG 命中、模型、耗时、工具数量和 fallback reason；员工侧工具选择、工具执行和确定性 finalizer 记录工具字段与 final status。字段只包含可观测结构化元数据，不扩大 LangSmith 外发或业务表写入边界。

## E-20260709-003：LangChain AI 应用层 P1b graph 显式 trace 导出

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-09
- evidence_type: local/p1b-agent-trace-export
- file: `D:\Project\YunxiBakeBot\app\service\agents\customer\service.py`; `D:\Project\YunxiBakeBot\app\service\agents\employee\service.py`; `D:\Project\YunxiBakeBot\app\service\agents\trace_report.py`; `D:\Project\YunxiBakeBot\tests\service\agents\test_customer_graph.py`; `D:\Project\YunxiBakeBot\tests\service\agents\test_employee_graph.py`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\service\agents\test_customer_graph.py tests\service\agents\test_employee_graph.py tests\service\agents\test_trace_report.py tests\scripts\test_report_agent_traces.py tests\service\agents\test_observability.py -q --no-cov`; `python -m ruff check app\service\agents\customer\service.py app\service\agents\employee\service.py app\service\agents\trace_report.py app\service\agents\observability.py scripts\report_agent_traces.py tests\service\agents\test_customer_graph.py tests\service\agents\test_employee_graph.py tests\service\agents\test_trace_report.py tests\scripts\test_report_agent_traces.py tests\service\agents\test_observability.py`; `python -m ruff format --check app\service\agents\customer\service.py app\service\agents\employee\service.py app\service\agents\trace_report.py app\service\agents\observability.py scripts\report_agent_traces.py tests\service\agents\test_customer_graph.py tests\service\agents\test_employee_graph.py tests\service\agents\test_trace_report.py tests\scripts\test_report_agent_traces.py tests\service\agents\test_observability.py`
- result: pass
- related_logbook: 2026-07-09 - feat(observability): 完成 P1b graph 显式 trace 导出
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: 本轮只登记 graph service 显式 trace 导出代码和测试命令；`AgentTraceRun.to_dict()` 通过统一脱敏函数过滤敏感字段，不登记真实客户原文、订单明细、手机号、地址或 open_id。
- summary: P1b 为客户机器人和员工助手 graph service 增加 `answer_with_trace()`，在保留原 `answer()` 字符串返回行为的同时显式暴露可序列化 `AgentTraceRun`。本切片不默认写 `reports\agent-traces\`，避免生产热路径每条消息产生文件；后续显式探针、eval 或结构化日志可调用该入口导出 trace JSON，再交给 `scripts\report_agent_traces.py` 汇总。

## E-20260709-002：LangChain AI 应用层 P1a 本地 Agent trace 报告

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-09
- evidence_type: local/p1a-agent-trace-report
- file: `D:\Project\YunxiBakeBot\app\service\agents\observability.py`; `D:\Project\YunxiBakeBot\app\service\agents\trace_report.py`; `D:\Project\YunxiBakeBot\scripts\report_agent_traces.py`; `D:\Project\YunxiBakeBot\tests\service\agents\test_observability.py`; `D:\Project\YunxiBakeBot\tests\service\agents\test_trace_report.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_report_agent_traces.py`; `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\service\agents\test_observability.py tests\service\agents\test_trace_report.py tests\scripts\test_report_agent_traces.py -q --no-cov`; `python -m ruff check app\service\agents\observability.py app\service\agents\trace_report.py scripts\report_agent_traces.py tests\service\agents\test_observability.py tests\service\agents\test_trace_report.py tests\scripts\test_report_agent_traces.py`; `python -m ruff format --check app\service\agents\observability.py app\service\agents\trace_report.py scripts\report_agent_traces.py tests\service\agents\test_observability.py tests\service\agents\test_trace_report.py tests\scripts\test_report_agent_traces.py`; `python scripts\report_agent_traces.py --latest --summary`
- result: pass
- related_logbook: 2026-07-09 - feat(observability): 完成 P1a 本地 Agent trace 报告切片
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: 本轮只登记代码路径、测试命令和脚本摘要；新增报告器默认过滤 open_id、手机号、地址、token、密钥、消息原文、历史记录、客户画像和工具结果，不包含真实客户原文或订单明细。
- summary: P1a 建立本地 Agent trace 报告闭环，新增只读聚合模块和 CLI，可从指定 JSON 或 `reports\agent-traces\` 最新 JSON 输出双机器人节点级摘要；当前未改 graph 热路径、未写业务表、未打开 LangSmith 外发。无 trace JSON 时脚本返回 `agent_traces status=no_traces total_runs=0 agents=0`，为 P1b 接入真实运行 trace 落盘预留稳定入口。

## E-20260709-001：LangChain AI 应用层 P0 生产验证闭环

- trace_id: 20260709-langchain-ai-layer-production-enhancement
- generated_at: 2026-07-09
- evidence_type: production/p0-langchain-ai-layer
- file: `D:\Project\YunxiBakeBot\docs\architecture\langchain-ai-layer-production-enhancement-plan.md`; `D:\Project\YunxiBakeBot\reports\wecom-employee-agent\langchain-prod-callback-20260709-2210.json`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `git push origin master`; `git push server master`; remote `systemctl restart yunxibakebot`; `curl.exe -sS https://yunxifood.cn/health`; `curl.exe -sS https://yunxifood.cn/ready`; `python scripts\check_wecom_employee_agent_callback.py --base-url https://yunxifood.cn --json --output reports\wecom-employee-agent\langchain-prod-callback-20260709-2210.json`; `python -m pytest tests\scripts\test_check_wecom_employee_agent_callback.py tests\scripts\test_check_wecom_employee_agent_plans.py tests\service\test_wecom_employee_agent.py -q --no-cov`; `python scripts\check_wecom_employee_agent_plans.py --json`
- result: pass
- related_logbook: 2026-07-09 - fix(verification): 生产 callback 探针适配实时库存变化并完成 P0 验证
- related_adr: 0003-langchain-ai-layer-boundary
- contains_sensitive_data: no
- retention_note: callback 报告位于 gitignored reports 目录，仅记录脱敏预览、探针名称、状态码和语义检查结果；不记录企微 token、AES key、密文、签名、手机号、完整订单号或完整地址。
- summary: LangChain AI 应用层接管成果已同步到生产 0.85.2，`/health` 与 `/ready` 均通过，员工助手生产 callback 探针 48/48 通过。首次探针失败暴露商品库存语义验收硬编码实时库存数字的问题，已改为动态库存治理口径：高库存商品只要求返回库存事实和安全下一步，零库存或已下架商品分别允许“暂无可售库存并建议替代款”或“未命中且不得当作缺货结论”的安全结果。

## E-20260707-004：GitHub 参考计划双仓执行交接快照

- trace_id: 20260707-github-reference-execution-handoff
- generated_at: 2026-07-07
- evidence_type: local/harness-handoff
- file: `D:\Project\YunxiBakeBot\reports\harness\handoff-github-reference-execution-20260706-175041.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\docs\harness-engineering\core\evidence-index.md`
- command: `python scripts\harness_snapshot.py --trace-id 20260707-github-reference-execution-handoff --goal "GitHub 参考计划双仓执行收口，保持客户热路径/员工助手/MiniApp 边界" --status blocked_external --output "reports\harness\handoff-github-reference-execution-{timestamp}.md"`; Platform `python scripts\check_project.py --skip-tests`; Platform `git diff --check`; MiniApp `npm run check:page-api-coverage`; MiniApp `npm run check:observability-contract`; MiniApp `npm run check:miniprogram-ci-readiness`; MiniApp `git diff --check`
- result: pass
- related_logbook: 2026-07-07 - chore(harness): 归档 GitHub 参考计划双仓执行交接快照
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记双仓文件状态、命令结论、报告路径和外部阻塞说明；不包含客户原文、订单明细、密钥、上传私钥或个人敏感信息。
- summary: 归档 GitHub 参考计划阶段 0-6 双仓执行状态。Platform 侧七类业务合约通过，MiniApp 页面 API 覆盖、可观测和 miniprogram-ci 准备合约通过命令门槛；当前剩余不是代码边界问题，而是微信开发者工具 `islogin=false` / `需要重新登录 (code 10)` 导致按钮触达扫描和预览二维码无法刷新，以及真实 miniprogram-ci 上传所需仓库外私钥、依赖、机器人号、版本号、说明、体验版二维码和真机/支付/审核证据缺失。交接快照明确不引入 LangChain / LangGraph，不改客户热路径、不改员工助手主链路、不让 MiniApp 沉淀业务真相。

## E-20260707-003：GitHub 参考计划全量回归缺口修复

- trace_id: 20260707-github-reference-full-suite-regression
- generated_at: 2026-07-07
- evidence_type: local/full-suite-regression
- file: `D:\Project\YunxiBakeBot\scripts\rebuild_embeddings.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_rebuild_embeddings.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_wecom_employee_agent_callback.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\scripts\test_rebuild_embeddings.py tests\scripts\test_check_wecom_employee_agent_callback.py::test_run_callback_checks_covers_employee_queries -q --no-cov`; `python -m ruff check scripts\rebuild_embeddings.py tests\scripts\test_rebuild_embeddings.py tests\scripts\test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check scripts\rebuild_embeddings.py tests\scripts\test_rebuild_embeddings.py tests\scripts\test_check_wecom_employee_agent_callback.py`; `python -m pytest tests/ -q`; `python scripts\check_project.py --skip-tests`; `cd web/admin; npm run typecheck`; `cd web/admin; npm run build:production`; architecture scans `rg "from app\.repository" app\api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app\service -g "*.py"`, `rg "from app\.(service|repository|api)" app\models -g "*.py"`; `python scripts\check_mistake_ledger.py`; `python scripts\check_evidence_index.py --summary`; `git diff --check`
- result: pass
- related_logbook: 2026-07-07 - fix(verification): 修复 GitHub 参考计划执行后的全量回归缺口
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记本地测试、脚本和静态扫描命令结论；不包含客户原文、订单数据、密钥或个人敏感信息。
- summary: 全量后端测试暴露向量重建旧表夹具缺 v015 知识治理字段、企微员工助手 callback 假客户端未覆盖新增探针语义两类缺口。已让 `scripts/rebuild_embeddings.py` 在读取知识前同时检查必需表和必需字段，旧库缺字段时按 schema not ready 处理；测试夹具补齐当前治理字段并新增旧表缺字段回归；callback 假客户端补齐“明天预定订单”和“同步失败有哪些”回复。聚焦回归、Ruff、全量 `python -m pytest tests/ -q`、统一质量门禁、后台 `npm run typecheck`、后台 `npm run build:production`、架构扫描、mistake ledger、evidence index 和 diff 空白检查均通过。

## E-20260707-002：GitHub 参考实施计划静态门禁

- trace_id: 20260707-github-reference-plan-contract
- generated_at: 2026-07-07
- evidence_type: local/github-reference-plan-contract
- file: `D:\Project\YunxiBakeBot\docs\architecture\github-reference-benchmark-and-implementation-plan.md`; `D:\Project\YunxiBakeBot\scripts\check_github_reference_implementation_plan.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_github_reference_implementation_plan.py`; `D:\Project\YunxiBakeBot\scripts\check_project.py`; `D:\Project\YunxiBakeBot\scripts\preflight_production.py`; `D:\Project\YunxiBakeBot\scripts\check_preflight_business_contracts.py`; `D:\Project\YunxiBakeBot\docs\README.md`; `D:\Project\YunxiBakeBot\docs\harness-engineering\core\verification-matrix.md`; `D:\Project\YunxiBakeBot\项目进度与配置清单.md`; `D:\Project\YunxiBakeBot\reports\preflight-github-reference-plan-contract-20260707-012412.json`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python scripts\check_github_reference_implementation_plan.py --summary`; `python -m pytest tests\scripts\test_check_github_reference_implementation_plan.py tests\scripts\test_check_project.py tests\scripts\test_check_preflight_business_contracts.py tests\scripts\test_preflight_production.py -q --no-cov`; `python -m ruff check scripts\check_github_reference_implementation_plan.py tests\scripts\test_check_github_reference_implementation_plan.py scripts\check_project.py scripts\preflight_production.py scripts\check_preflight_business_contracts.py tests\scripts\test_check_project.py tests\scripts\test_preflight_production.py tests\scripts\test_check_preflight_business_contracts.py`; `python -m ruff format --check scripts\check_github_reference_implementation_plan.py tests\scripts\test_check_github_reference_implementation_plan.py scripts\check_project.py scripts\preflight_production.py scripts\check_preflight_business_contracts.py tests\scripts\test_check_project.py tests\scripts\test_preflight_production.py tests\scripts\test_check_preflight_business_contracts.py`; `python scripts\check_project.py --skip-tests`; `python scripts\preflight_production.py --json --output "reports\preflight-github-reference-plan-contract-{timestamp}.json"`; `python scripts\check_preflight_business_contracts.py "reports\preflight-github-reference-plan-contract-20260707-012412.json" --summary`; `python scripts\check_evidence_index.py --summary`; `git diff --check`
- result: pass
- related_logbook: 2026-07-07 - chore(architecture): 新增 GitHub 参考实施计划静态门禁
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记主计划、静态检查脚本、测试、本地命令结论和 gitignored preflight 报告路径；不记录客户原文、订单数据、密钥或个人敏感信息。
- summary: 新增 GitHub 参考实施计划静态门禁，冻结阶段状态、客户热路径和员工事实回复不迁移、MiniApp 不沉淀业务真相、LangGraph 仅限可选离线固定流程等边界。新增 `scripts/check_github_reference_implementation_plan.py --summary`，并作为第七类业务合约接入统一质量门禁、生产预检和预检证据复核；本片未引入 LangChain / LangGraph，未改客户机器人热路径，未改员工助手 planner、工具调用或确定性回复。实际预检报告 `reports\preflight-github-reference-plan-contract-20260707-012412.json` 因既有 `handoff_staff_userid_ready` 环境配置缺口整体失败，但业务合约复核通过，`preflight_business_contracts status=passed total=8 failed=0`。

## E-20260707-001：MiniApp 页面 API 覆盖合约静态门禁

- trace_id: 20260707-miniapp-page-api-coverage-contract
- generated_at: 2026-07-07
- evidence_type: local/miniapp-page-api-contract
- file: `D:\Project\YunxiBakeBot\docs\architecture\miniapp-page-api-coverage-contract.md`; `D:\Project\YunxiBakeBot\scripts\check_miniapp_page_api_contract.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_miniapp_page_api_contract.py`; `D:\Project\YunxiBakeBot\scripts\check_project.py`; `D:\Project\YunxiBakeBot\scripts\preflight_production.py`; `D:\Project\YunxiBakeBot\scripts\check_preflight_business_contracts.py`; `D:\Project\YunxiBakeBot\reports\preflight-miniapp-contract-20260707-001659.json`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python scripts\check_miniapp_page_api_contract.py --summary`; `python -m pytest tests\scripts\test_check_miniapp_page_api_contract.py tests\scripts\test_check_project.py tests\scripts\test_check_preflight_business_contracts.py tests\scripts\test_preflight_production.py -q --no-cov`; `python -m ruff check scripts\check_miniapp_page_api_contract.py tests\scripts\test_check_miniapp_page_api_contract.py scripts\check_project.py scripts\preflight_production.py scripts\check_preflight_business_contracts.py tests\scripts\test_check_project.py tests\scripts\test_preflight_production.py tests\scripts\test_check_preflight_business_contracts.py`; `python -m ruff format --check scripts\check_miniapp_page_api_contract.py tests\scripts\test_check_miniapp_page_api_contract.py scripts\check_project.py scripts\preflight_production.py scripts\check_preflight_business_contracts.py tests\scripts\test_check_project.py tests\scripts\test_preflight_production.py tests\scripts\test_check_preflight_business_contracts.py`; `python scripts\check_project.py --skip-tests`; `python scripts\preflight_production.py --json --output "reports\preflight-miniapp-contract-{timestamp}.json"`; `python scripts\check_preflight_business_contracts.py "reports\preflight-miniapp-contract-20260707-001659.json" --summary`
- result: pass
- related_logbook: 2026-07-07 - chore(miniapp): 新增页面 API 覆盖合约静态门禁
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记 MiniApp 页面 API 覆盖合约、静态检查脚本、测试和命令结论；预检 JSON 位于 gitignored reports 目录，不在索引中记录客户数据、订单数据、密钥或个人敏感信息。
- summary: 新增 MiniApp 页面 API 覆盖合约，冻结首页、商品、详情、购物车、结算、政策、地址、订单、客户群登记、客服和会员中心等页面依赖的 Platform API，并明确会员权益、积分、储值余额、优惠券、配送费、满减和活动价必须先回 Platform 补 API 契约。新增 `scripts/check_miniapp_page_api_contract.py --summary`，并作为第六类业务合约接入统一质量门禁和生产预检。实际预检报告 `reports\preflight-miniapp-contract-20260707-001659.json` 因既有 `handoff_staff_userid_ready` 环境配置缺口整体失败，但业务合约复核通过，`preflight_business_contracts status=passed total=7 failed=0`。

## E-20260706-004：客户机器人可观测合约静态门禁

- trace_id: 20260706-customer-observability-contract
- generated_at: 2026-07-06
- evidence_type: local/customer-observability-contract
- file: `D:\Project\YunxiBakeBot\docs\architecture\customer-observability-contract.md`; `D:\Project\YunxiBakeBot\scripts\check_customer_observability_contract.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_customer_observability_contract.py`; `D:\Project\YunxiBakeBot\scripts\check_project.py`; `D:\Project\YunxiBakeBot\scripts\preflight_production.py`; `D:\Project\YunxiBakeBot\scripts\check_preflight_business_contracts.py`; `D:\Project\YunxiBakeBot\reports\preflight-observability-contract-20260707-000652.json`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python scripts\check_customer_observability_contract.py --summary`; `python -m pytest tests\scripts\test_check_customer_observability_contract.py tests\scripts\test_check_project.py tests\scripts\test_check_preflight_business_contracts.py tests\scripts\test_preflight_production.py -q --no-cov`; `python -m ruff check scripts\check_customer_observability_contract.py tests\scripts\test_check_customer_observability_contract.py scripts\check_project.py scripts\preflight_production.py scripts\check_preflight_business_contracts.py tests\scripts\test_check_project.py tests\scripts\test_preflight_production.py tests\scripts\test_check_preflight_business_contracts.py`; `python -m ruff format --check scripts\check_customer_observability_contract.py tests\scripts\test_check_customer_observability_contract.py scripts\check_project.py scripts\preflight_production.py scripts\check_preflight_business_contracts.py tests\scripts\test_check_project.py tests\scripts\test_preflight_production.py tests\scripts\test_check_preflight_business_contracts.py`; `python scripts\check_project.py --skip-tests`; `python scripts\preflight_production.py --json --output "reports\preflight-observability-contract-{timestamp}.json"`; `python scripts\check_preflight_business_contracts.py "reports\preflight-observability-contract-20260707-000652.json" --summary`
- result: pass
- related_logbook: 2026-07-06 - chore(observability): 新增客户机器人可观测合约静态门禁
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记客户机器人可观测合约、静态检查脚本、测试和命令结论；预检 JSON 位于 gitignored reports 目录，不在索引中记录客户原文、订单数据、密钥或个人敏感信息。
- summary: 新增客户机器人可观测合约，冻结知识命中、无资料兜底、转人工、工具成功、上下文压力等指标，以及 trace、渠道、机器人类型、意图、转人工原因、兜底原因等事件字段。新增 `scripts/check_customer_observability_contract.py --summary`，并作为第五类业务合约接入统一质量门禁和生产预检。实际预检报告 `reports\preflight-observability-contract-20260707-000652.json` 因既有 `handoff_staff_userid_ready` 环境配置缺口整体失败，但业务合约复核通过，`preflight_business_contracts status=passed total=6 failed=0`。

## E-20260706-003：客户长期记忆治理计划静态门禁

- trace_id: 20260706-customer-memory-governance-plan
- generated_at: 2026-07-06
- evidence_type: local/customer-memory-governance-contract
- file: `D:\Project\YunxiBakeBot\docs\architecture\customer-memory-governance-plan.md`; `D:\Project\YunxiBakeBot\scripts\check_customer_memory_governance_plan.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_customer_memory_governance_plan.py`; `D:\Project\YunxiBakeBot\scripts\check_project.py`; `D:\Project\YunxiBakeBot\scripts\preflight_production.py`; `D:\Project\YunxiBakeBot\scripts\check_preflight_business_contracts.py`; `D:\Project\YunxiBakeBot\reports\preflight-memory-contract-20260706-235559.json`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python scripts\check_customer_memory_governance_plan.py --summary`; `python -m pytest tests\scripts\test_check_customer_memory_governance_plan.py tests\scripts\test_check_project.py tests\scripts\test_check_preflight_business_contracts.py tests\scripts\test_preflight_production.py -q --no-cov`; `python -m ruff check scripts\check_customer_memory_governance_plan.py tests\scripts\test_check_customer_memory_governance_plan.py scripts\check_project.py scripts\preflight_production.py scripts\check_preflight_business_contracts.py tests\scripts\test_check_project.py tests\scripts\test_preflight_production.py tests\scripts\test_check_preflight_business_contracts.py`; `python -m ruff format --check scripts\check_customer_memory_governance_plan.py tests\scripts\test_check_customer_memory_governance_plan.py scripts\check_project.py scripts\preflight_production.py scripts\check_preflight_business_contracts.py tests\scripts\test_check_project.py tests\scripts\test_preflight_production.py tests\scripts\test_check_preflight_business_contracts.py`; `python scripts\check_project.py --skip-tests`; `python scripts\preflight_production.py --json --output "reports\preflight-memory-contract-{timestamp}.json"`; `python scripts\check_preflight_business_contracts.py "reports\preflight-memory-contract-20260706-235559.json" --summary`; `python scripts\check_evidence_index.py --summary`; architecture scans `rg "from app\.repository" app\api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app\service -g "*.py"`, `rg "from app\.(service|repository|api)" app\models -g "*.py"`; `git diff --check`
- result: pass
- related_logbook: 2026-07-06 - chore(memory): 新增客户长期记忆治理静态门禁
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记长期记忆治理计划、静态检查脚本、测试和命令结论；不包含客户画像内容、会话原文、订单数据或敏感个人信息。
- summary: 新增客户长期记忆治理计划，冻结 `customer_profiles` 与 `conversation_summaries` 边界，要求长期画像只作为可审计服务提示，必须具备来源证据、置信度、状态、撤销、过期和会话摘要隔离边界。新增 `scripts/check_customer_memory_governance_plan.py --summary`，并接入统一质量门禁和生产预检业务合约明细；本片不改热路径、不改 `MemoryAgent` 写入策略、不改 `customer_profiles` 表结构。实际预检报告 `reports\preflight-memory-contract-20260706-235559.json` 因既有 `handoff_staff_userid_ready` 环境配置缺口整体失败，但业务合约复核通过，`preflight_business_contracts status=passed total=5 failed=0`。

## E-20260706-002：Harness 证据索引结构门禁

- trace_id: 20260706-evidence-index-guard
- generated_at: 2026-07-06
- evidence_type: local/harness-evidence-index-guard
- file: `D:\Project\YunxiBakeBot\scripts\check_evidence_index.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_evidence_index.py`; `D:\Project\YunxiBakeBot\docs\harness-engineering\core\evidence-index.md`; `D:\Project\YunxiBakeBot\.pre-commit-config.yaml`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python scripts\check_evidence_index.py --summary`; `python -m pytest tests\scripts\test_check_evidence_index.py tests\scripts\test_check_mistake_ledger.py tests\scripts\test_harness_snapshot.py -q --no-cov`; `python -m ruff check scripts\check_evidence_index.py tests\scripts\test_check_evidence_index.py`; `python -m ruff format --check scripts\check_evidence_index.py tests\scripts\test_check_evidence_index.py`; `python scripts\check_mistake_ledger.py`; `python scripts\check_file_sizes.py`; `python scripts\check_project.py --skip-tests`; `pre-commit run check-evidence-index --all-files`; architecture scans `rg "from app\.repository" app\api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app\service -g "*.py"`, `rg "from app\.(service|repository|api)" app\models -g "*.py"`; `python scripts\check_text_encoding.py`; `git diff --check`
- result: pass
- related_logbook: 2026-07-06 - chore(harness): 新增证据索引结构门禁
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记本地结构校验命令、脚本、测试和文档路径；不读取或记录 reports 下的敏感业务内容。
- summary: 新增只读脚本校验 Harness evidence index 的必填字段、结果枚举、敏感数据标记、重复 ID 和预检业务合约证据引用；历史重复证据 ID 已重编号为未占用编号，避免后续按 evidence id 追溯时歧义。脚本已接入 pre-commit `check-evidence-index`。

## E-20260706-001：预检业务合约证据复核

- trace_id: 20260706-preflight-contract-evidence-check
- generated_at: 2026-07-06
- evidence_type: local/preflight-business-contract-evidence
- file: `D:\Project\YunxiBakeBot\scripts\check_preflight_business_contracts.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_preflight_business_contracts.py`; `D:\Project\YunxiBakeBot\reports\preflight-contract-check-20260706-232901.json`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\scripts\test_check_preflight_business_contracts.py -q --no-cov`; `python -m ruff check scripts\check_preflight_business_contracts.py tests\scripts\test_check_preflight_business_contracts.py`; `python -m ruff format --check scripts\check_preflight_business_contracts.py tests\scripts\test_check_preflight_business_contracts.py`; `python scripts\preflight_production.py --json --output "reports\preflight-contract-check-{timestamp}.json"`; `python scripts\check_preflight_business_contracts.py "reports\preflight-contract-check-20260706-232901.json" --summary`
- result: pass
- related_logbook: 2026-07-06 - chore(preflight): 新增预检业务合约证据复核脚本
- related_adr: none
- contains_sensitive_data: no
- retention_note: 预检报告位于 gitignored `reports/`，索引只记录路径和业务合约校验结果，不记录密钥、客户数据或订单明细。
- summary: 新增只读脚本校验已保存的 preflight JSON 是否包含 `business_contracts.static_checks`，且员工助手能力合约、客户 RAG golden cases、知识治理计划三类状态均为 passed。实际本地预检报告因既有 `handoff_staff_userid_ready` 环境配置缺口整体失败，但业务合约证据复核通过，`preflight_business_contracts status=passed total=4 failed=0`。

## E-20260705-001：企微员工助手确定性直出重构

- trace_id: 20260704-wecom-employee-agent-deterministic-reply
- generated_at: 2026-07-05
- evidence_type: local-and-production/wecom-employee-agent-deterministic-reply
- file: `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_service.py`; `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_reply_guard.py`; `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_order_list_guard.py`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_ops_format.py`; `D:\Project\YunxiBakeBot\tests\service\test_wecom_employee_agent.py`; `D:\Project\YunxiBakeBot\tests\service\test_wecom_employee_privacy_format.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/service/test_wecom_employee_privacy_format.py -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/api/test_wecom_intelligent_bot_plugin_api.py -o addopts="" --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m pytest tests/ -q`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; `pre-commit run --all-files`
- result: pass
- related_logbook: 2026-07-05 - refactor(wecom): 员工助手回复链路改为确定性直出
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记本地验证命令、重构文件清单和生产报告路径；回调报告由脚本脱敏，不记录企微 Token、AES key 或密文。
- summary: 员工助手员工可见回复移除回复期 LLM 润色和两个旧 guard 文件，统一由确定性工具结果和模板生成后经过 `clean_plain_text_reply()` 返回；LLM 仅保留在结构化规划兜底阶段。本地员工助手相关 91 条测试、45/45 规划探针和全量测试通过，覆盖率 79.08%。生产已同步到 `0.74.32`，`/health` 返回 `status=ok`，`/ready` 返回 `status=ready` 且企微智能机器人回调配置检查通过；45 问加密回调探针报告 `D:\Project\YunxiBakeBot\reports\wecom-employee-agent\callback-20260705-151936.json` 显示 `status=passed,total=45,failed=0,app_version=0.74.32`。

## E-20260704-041：企微员工助手商品无库存和未命中回复口径

- trace_id: 20260704-wecom-employee-agent-product-stockout-miss
- generated_at: 2026-07-04
- evidence_type: local/wecom-employee-agent-product-stockout-miss
- file: `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_reply_guard.py`; `D:\Project\YunxiBakeBot\scripts\wecom_employee_agent_probe_cases.py`; `D:\Project\YunxiBakeBot\tests\service\test_wecom_employee_agent.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_wecom_employee_agent_callback.py`; `D:\Project\YunxiBakeBot\tests\api\test_wecom_intelligent_bot_plugin_api.py`; `D:\Project\YunxiBakeBot\VERSION`; `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py::test_employee_agent_polish_rejects_no_stock_replacement_hallucination tests/service/test_wecom_employee_agent.py::test_employee_agent_polish_keeps_product_miss_guardrail tests/service/test_wecom_employee_agent.py::test_preserve_tool_facts_rejects_product_miss_guardrail_loss tests/service/test_wecom_employee_agent.py::test_preserve_tool_facts_rejects_no_stock_replacement_hallucination tests/scripts/test_check_wecom_employee_agent_callback.py::test_run_callback_checks_covers_employee_queries tests/scripts/test_check_wecom_employee_agent_callback.py::test_evaluate_reply_rejects_no_stock_replacement_hallucination tests/scripts/test_check_wecom_employee_agent_callback.py::test_evaluate_reply_rejects_missing_product_guardrail_loss tests/api/test_wecom_intelligent_bot_plugin_api.py::test_product_lookup_no_stock_is_actionable tests/api/test_wecom_intelligent_bot_plugin_api.py::test_product_lookup_miss_is_not_stockout -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/api/test_wecom_intelligent_bot_plugin_api.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m ruff check app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/api/test_wecom_intelligent_bot_plugin_api.py`; `python -m ruff format --check app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/api/test_wecom_intelligent_bot_plugin_api.py`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 守住商品无库存与未命中回复口径
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记本地验证命令和商品回复口径结论，不包含企微 Token、AES key、密文、客户数据或订单明细。
- summary: 员工助手商品回复事实保真层新增两个守卫：商品未命中时，LLM 润色不能丢掉“未命中不等于缺货”的保护语；0 库存商品只允许建议同品类或相近价位替代，不能编造具体替代品名。首次生产复查暴露“如北海道吐司 / 原味手撕包”仍会漏过，已把“如 + 具体替代品”纳入同一守卫，并把对应具体品名加入共享探针禁用词。共享探针新增 `no-stock-product` 与 `missing-product`，规划和回调验收样本扩展到 45 条。本地聚焦回归 9 条、补漏聚焦回归 3 条、员工助手和企微插件相关测试、45/45 规划探针、Ruff、文件体量、项目红线、架构扫描、编码检查、mistake ledger 和 diff 空白检查均通过；生产同步待执行。

## E-20260704-040：企微员工助手商品高库存下一步动作

- trace_id: 20260704-wecom-employee-agent-product-stock-action
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-product-stock-action
- file: `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_product_action.py`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_tools.py`; `D:\Project\YunxiBakeBot\scripts\wecom_employee_agent_probe_cases.py`; `D:\Project\YunxiBakeBot\tests\service\test_wecom_employee_agent.py`; `D:\Project\YunxiBakeBot\tests\api\test_wecom_intelligent_bot_plugin_api.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_wecom_employee_agent_callback.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py::test_product_next_action_uses_stock_context tests/service/test_wecom_employee_agent.py::test_employee_agent_high_stock_product_reply_has_no_low_stock_hint tests/api/test_wecom_intelligent_bot_plugin_api.py::test_product_lookup_returns_stock_for_valid_key tests/scripts/test_check_wecom_employee_agent_callback.py::test_evaluate_reply_rejects_high_stock_low_stock_hint -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/api/test_wecom_intelligent_bot_plugin_api.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m ruff check app/service/wecom/intelligent_bot_tools.py app/service/wecom/intelligent_bot_product_action.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/api/test_wecom_intelligent_bot_plugin_api.py`; `python -m ruff format --check app/service/wecom/intelligent_bot_tools.py app/service/wecom/intelligent_bot_product_action.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/api/test_wecom_intelligent_bot_plugin_api.py`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production decoded product probes for `casual-inventory`, `casual-product-stock`, `order-product-inventory`, `product-stock-customer-reply`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 商品高库存不提示低库存
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记本地验证命令和商品库存口径结论，不包含订单明细、客户数据、企微密钥或完整回调密文。
- summary: 商品查询工具的下一步动作从固定低库存提示改为按命中商品库存动态生成。未命中、无库存、低库存、高库存分别输出不同员工动作建议；当前明确要求 `库存 72` 的高库存商品探针禁止出现“低库存”。生产 `0.74.27 / 786b738a3` 已通过 `/health`、`/ready` 和 43/43 加密回调探针；商品完整回复抽查 `casual-inventory`、`casual-product-stock`、`order-product-inventory`、`product-stock-customer-reply` 均保留 `库存72`，且未出现“低库存”误导提示。

## E-20260704-039：企微员工助手普通订单列表结构保真

- trace_id: 20260704-wecom-employee-agent-order-list-shape
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-order-list-shape
- file: `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_order_list_guard.py`; `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_reply_guard.py`; `D:\Project\YunxiBakeBot\scripts\wecom_employee_agent_probe_cases.py`; `D:\Project\YunxiBakeBot\tests\service\test_wecom_employee_agent.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_wecom_employee_agent_callback.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py::test_preserve_tool_facts_rejects_order_list_status_compression tests/service/test_wecom_employee_agent.py::test_preserve_tool_facts_rejects_order_list_logistics_compression tests/service/test_wecom_employee_agent.py::test_preserve_tool_facts_rejects_missing_logistics_heading_only tests/service/test_wecom_employee_agent.py::test_employee_agent_polish_preserves_pending_order_list_shape tests/scripts/test_check_wecom_employee_agent_callback.py::test_evaluate_reply_rejects_compressed_pending_list -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m ruff check app/service/wecom/employee_agent_reply_guard.py app/service/wecom/employee_agent_order_list_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/wecom/employee_agent_reply_guard.py app/service/wecom/employee_agent_order_list_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production decoded order-list probes for `pending-shipment-list`, `casual-pending-shipment`, `missing-logistics-list`, `casual-missing-logistics`, `tomorrow-pending-orders`, `weekend-pending-orders`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 保留普通订单列表结构
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记本地验证命令和普通订单列表结构守卫结论，不包含订单明细、客户数据、企微密钥或完整回调密文。
- summary: 普通订单列表新增行级结构保真守卫。确定性结果中多条订单行若包含尾号、状态、金额和物流标记，LLM 润色必须保留同等数量级的行级字段，否则回退确定性工具结果；物流标记计数使用非重叠匹配，避免 `暂无物流` 与 `无物流` 子串双计数。待发货和无物流探针也升级为必须出现尾号、物流和状态词。生产 `0.74.26 / 8b669d8e8` 已通过 `/health`、`/ready` 和 43/43 加密回调探针；普通订单列表解密抽查 `pending-shipment-list`、`casual-pending-shipment`、`missing-logistics-list`、`casual-missing-logistics`、`tomorrow-pending-orders`、`weekend-pending-orders` 均保留 `尾号 / 待发货或待收货 / 金额 / 暂无物流` 行级字段。

## E-20260704-038：企微员工助手履约风险列表结构保真

- trace_id: 20260704-wecom-employee-agent-fulfillment-list-shape
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-fulfillment-list-shape
- file: `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_delivery_format.py`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_order_format.py`; `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_reply_guard.py`; `D:\Project\YunxiBakeBot\scripts\wecom_employee_agent_probe_cases.py`; `D:\Project\YunxiBakeBot\tests\service\test_wecom_employee_agent.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_wecom_employee_agent_callback.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py::test_build_order_list_tool_result_labels_fulfillment_risk_order tests/service/test_wecom_employee_agent.py::test_preserve_tool_facts_rejects_fulfillment_order_list_compression tests/service/test_wecom_employee_agent.py::test_employee_agent_polish_preserves_fulfillment_order_list_shape -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m ruff check app/service/wecom/intelligent_bot_order_format.py app/service/wecom/intelligent_bot_delivery_format.py app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/wecom/intelligent_bot_order_format.py app/service/wecom/intelligent_bot_delivery_format.py app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production decoded fulfillment probes for `fulfillment-risk-list`, `casual-fulfillment-pressure`, `today-action-items`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-fulfillment-list-121b133.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-fulfillment-list-121b133.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 保留履约风险订单列表结构
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记本地验证命令和履约风险列表结构守卫结论，不包含订单明细、客户数据、企微密钥或完整回调密文。
- summary: 履约风险订单列表标题明确按约送时间升序展示，下一步动作提示优先处理已过约送时间或暂无物流订单；LLM 润色若压缩多单列表并丢失尾号、约送、物流、待发货/待收货状态，或减少尾号数量，会回退确定性工具结果。生产 `0.74.24 / 121b1331a` 已通过 `/health`、`/ready` 和 43/43 加密回调探针；`fulfillment-risk-list`、`casual-fulfillment-pressure`、`today-action-items` 解密抽查均保留 `尾号 / 约送 / 物流`，且履约风险列表按约送时间展示。本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-037：企微员工助手已过约送时间履约风险标记

- trace_id: 20260704-wecom-employee-agent-overdue-fulfillment-marker
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-overdue-fulfillment-marker
- file: `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_order_format.py`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_order_insights.py`; `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_reply_guard.py`; `D:\Project\YunxiBakeBot\scripts\wecom_employee_agent_probe_cases.py`; `D:\Project\YunxiBakeBot\tests\service\test_wecom_employee_agent.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py::test_employee_delivery_time_text_marks_overdue_delivery tests/service/test_wecom_employee_agent.py::test_preserve_tool_facts_rejects_overdue_delivery_detour tests/service/test_wecom_employee_agent.py::test_employee_agent_polish_rejects_overdue_delivery_detour -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m ruff check app/service/wecom/intelligent_bot_order_format.py app/service/wecom/intelligent_bot_order_insights.py app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py`; `python -m ruff format --check app/service/wecom/intelligent_bot_order_format.py app/service/wecom/intelligent_bot_order_insights.py app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production decoded fulfillment probes for `fulfillment-risk-list`, `casual-fulfillment-pressure`, `today-action-items`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-overdue-fulfillment-cae499c.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-overdue-fulfillment-cae499c.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 标记已过约送时间的履约风险单
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记本地验证命令和员工助手回复口径守卫结论，不包含订单明细、客户数据或企微密钥。
- summary: 订单行会对已过约送时间追加明确标记，LLM 润色若把逾期风险改写为未来截止表达会回退确定性工具结果；43 问探针已加入“需在 / 前完成 / 前安排”禁用词。生产 `0.74.23 / cae499c82` 已通过 `/health`、`/ready`、43 问加密回调探针和履约风险完整回复抽查。

## E-20260704-036：企微员工助手履约日期和销量备货口径守卫

- trace_id: 20260704-wecom-employee-agent-delivery-date-scope
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-delivery-date-and-stocking-scope
- file: `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_reply_guard.py`; `D:\Project\YunxiBakeBot\scripts\wecom_employee_agent_probe_cases.py`; `D:\Project\YunxiBakeBot\tests\service\test_wecom_employee_agent.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py::test_preserve_tool_facts_rejects_relative_delivery_date_distortion tests/service/test_wecom_employee_agent.py::test_employee_agent_polish_rejects_relative_delivery_date_distortion -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py::test_preserve_tool_facts_rejects_top_products_stocking_advice tests/service/test_wecom_employee_agent.py::test_employee_agent_polish_rejects_top_products_stocking_advice -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m ruff check app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py`; `python -m ruff format --check app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-delivery-date-scope-6bc3ec5.bundle"`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-top-product-stocking-3f80aa0.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-delivery-date-scope-6bc3ec5.bundle`; cleanup `rm /opt/yunxibakebot/wecom-top-product-stocking-3f80aa0.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 守住履约日期和销量备货口径
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记命令、版本、状态码和脱敏预览结论；不记录企微 Token、AES key、密文、完整订单号、手机号或完整地址。
- summary: 员工助手回复事实保真层新增绝对约送日期守卫：工具结果出现 `约送 YYYY-MM-DD` 时，润色不能凭空改写成“明天 / 后天 / 周末 / 下周”等相对日期。同步 `0.74.20 / 6bc3ec5a5` 后生产 43 问首次验收发现 `this-week-top-products` 仍被润色为“优先备货”，补充将销量排行备货建议守卫扩展到所有销量排行工具结果。本地聚焦回归 4 条、员工助手相关 79 条测试、43 问规划探针、Ruff、文件体量、项目红线、架构扫描、编码检查、mistake ledger 和 diff 空白检查均通过；已重新同步生产 `0.74.21 / 3f80aa025`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过，`this-week-top-products` 不再出现“优先备货”，履约风险类未再出现错误相对日期漂移；本轮两个同步 bundle 均已按明确单文件路径清理。

## E-20260704-035：企微员工助手无物流关闭退款口径守卫

- trace_id: 20260704-wecom-employee-agent-missing-logistics-scope
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-missing-logistics-scope
- file: `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_reply_guard.py`; `D:\Project\YunxiBakeBot\scripts\wecom_employee_agent_probe_cases.py`; `D:\Project\YunxiBakeBot\tests\service\test_wecom_employee_agent.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py::test_preserve_tool_facts_rejects_missing_logistics_exclusion_distortion -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py::test_employee_agent_polish_rejects_missing_logistics_exclusion_distortion -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m ruff check app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py`; `python -m ruff format --check app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-missing-logistics-scope-3adede1.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-missing-logistics-scope-3adede1.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 守住无物流订单的关闭退款口径
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记命令、版本、状态码和脱敏预览结论；不记录企微 Token、AES key、密文、完整订单号、手机号或完整地址。
- summary: 员工助手无物流列表回复新增范围口径守卫。确定性结果为“暂无物流 / 无物流”但没有明确排除关闭或退款单时，LLM 润色若凭空声明“已剔除 / 不含已关闭 / 不含退款 / 剔除已关闭 / 剔除退款”会回退确定性工具结果。无物流探针样本同步加入禁用词。本地聚焦回归 2 条、员工助手相关 75 条测试、43 问规划探针、Ruff、文件体量、项目红线、架构扫描、编码检查、mistake ledger 和 diff 空白检查均通过；已同步生产 `0.74.19 / 3adede196`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过，`missing-logistics-list` 和 `casual-missing-logistics` 生产预览均未出现“已剔除 / 不含已关闭 / 不含退款”；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-034：企微员工助手销量并列爆款判断收紧

- trace_id: 20260704-wecom-employee-agent-top-products-tie
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-top-products-tie
- file: `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_top_products_format.py`; `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_order_format.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_reply_guard.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py::test_build_top_products_tool_result_marks_low_sample_tie tests/service/test_wecom_employee_agent.py::test_preserve_tool_facts_rejects_top_products_tie_distortion tests/service/test_wecom_employee_agent.py::test_employee_agent_polish_keeps_top_products_tie_caution -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m ruff check app/service/wecom/intelligent_bot_order_format.py app/service/wecom/intelligent_bot_top_products_format.py app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py`; `python -m ruff format --check app/service/wecom/intelligent_bot_order_format.py app/service/wecom/intelligent_bot_top_products_format.py app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-top-products-tie-4c38fad.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-top-products-tie-4c38fad.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 收紧销量并列时的爆款判断
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令、版本和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 销量排行工具结果新增第一名并列提示，低样本并列不再判断单一爆款；LLM 润色若把并列结果改写为“销量第一 / 当前爆款 / 优先备货”会回退确定性结果；43 问探针禁止销量排行类回复只凭排行给出“优先备货”。本地聚焦回归 3 条通过，员工助手相关 73 条测试通过，43 问规划探针通过，Ruff、文件体量、项目红线、架构扫描、编码检查、mistake ledger 和 diff 空白检查均通过；已同步生产 `0.74.18 / 4c38fadcb`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过，`casual-top-product` 生产预览已不再出现“优先备货”；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-033：企微员工助手 Markdown 引用符清理

- trace_id: 20260704-wecom-employee-agent-blockquote-cleanup
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-blockquote-cleanup
- file: `D:/Project/YunxiBakeBot/app/service/chat_reply.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_callback_semantics.py`; `D:/Project/YunxiBakeBot/tests/service/test_chat_refactor.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_chat_refactor.py::test_postprocess_reply_removes_markdown_marks tests/scripts/test_check_wecom_employee_agent_callback.py::test_evaluate_reply_rejects_markdown_decorations tests/scripts/test_check_wecom_employee_agent_callback.py::test_evaluate_reply_rejects_markdown_blockquote -q --no-cov`; `python -m pytest tests/service/test_chat_refactor.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m ruff check app/service/chat_reply.py scripts/wecom_employee_agent_callback_semantics.py tests/service/test_chat_refactor.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/chat_reply.py scripts/wecom_employee_agent_callback_semantics.py tests/service/test_chat_refactor.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-blockquote-cleanup-d562e5d.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-blockquote-cleanup-d562e5d.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 清理员工助手 Markdown 引用符
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令、版本和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手回复统一纯文本清理新增行首 `>` blockquote 引用符清理，并把 callback 语义验收升级为拒绝 `>` 引用符。聚焦回归 3 条通过，员工助手相关 90 条测试通过，43 问规划探针通过，Ruff、文件体量、项目红线、架构扫描、编码检查、mistake ledger 和 diff 空白检查均通过；已同步生产 `0.74.17 / d562e5d0d`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过，`refund-order-customer-reply` 生产预览已无 `>` blockquote 引用符；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-032：企微员工助手订单混合问法客户回复话术

- trace_id: 20260704-wecom-employee-agent-order-customer-reply
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-order-customer-reply
- file: `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_mixed_reply.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_reply_guard.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py::test_employee_agent_multi_tool_combines_order_and_knowledge tests/service/test_wecom_employee_agent.py::test_employee_agent_polish_keeps_customer_reply tests/service/test_wecom_employee_agent.py::test_employee_agent_polish_drops_private_marker tests/scripts/test_check_wecom_employee_agent_callback.py::test_evaluate_reply_rejects_generic_customer_lookup_empty_text -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m pytest tests/service/test_wecom_employee_agent_file_size.py -q --no-cov`; `python -m ruff check app/service/wecom/employee_agent_mixed_reply.py app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/wecom/employee_agent_mixed_reply.py app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-order-customer-reply-712ec05.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-order-customer-reply-712ec05.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 补强订单混合问法客户回复话术
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 订单+知识库混合问法中，员工问“怎么跟客户说 / 怎么回复客户”时不再只返回订单列表；多工具整理层会在订单工具结果后追加“给客户可复制回复”，退款/售后和未发货场景分别生成确定性话术。回复守卫要求 LLM 润色保留“客户 / 回复”，否则回退确定性结果。43 问探针同步强化 `pending-shipment-customer-reply` 和 `refund-order-customer-reply`，要求同时包含“客户 / 回复”。本地相关测试、43 问规划、Ruff、文件体量、项目红线、架构扫描、编码检查、mistake ledger 和 diff 空白检查均通过；已同步生产 `0.74.16 / 712ec0533`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-031：企微员工助手客户线索查询归一与脱敏

- trace_id: 20260704-wecom-employee-agent-ops-empty-readable
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-customer-lookup-query-cleanup
- file: `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_ops_format.py`; `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_ops_tools.py`; `D:/Project/YunxiBakeBot/tests/api/test_wecom_intelligent_bot_plugin_api.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/api/test_wecom_intelligent_bot_plugin_api.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/service/test_wecom_employee_agent.py -q --no-cov`; `python -m ruff check app/service/wecom/intelligent_bot_ops_format.py app/service/wecom/intelligent_bot_ops_tools.py tests/api/test_wecom_intelligent_bot_plugin_api.py`; `python -m ruff format --check app/service/wecom/intelligent_bot_ops_format.py app/service/wecom/intelligent_bot_ops_tools.py tests/api/test_wecom_intelligent_bot_plugin_api.py`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-customer-empty-query-9addc9f.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-customer-empty-query-9addc9f.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 优化客户线索和客户群空结果回复
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 客户线索查询从员工自然问法中清理“查一下 / 地址线索 / 地址”等口语噪声，把有效姓名、手机号或地址关键词交给后端查询；工具 payload 与员工回复只展示脱敏后的查询预览，避免手机号等敏感查询回显。本地 API/callback/plans/service 相关 88 条测试通过，43 问规划通过，Ruff、文件体量、项目红线、架构扫描、编码检查、mistake ledger 和 diff 空白检查均通过；已同步生产 `0.74.15 / 9addc9fc5`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过，`customer-lookup` 预览已只展示 `张三` 线索结果，不再回显整句查询；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-030：企微员工助手离线复盘摘要可读性

- trace_id: 20260704-wecom-employee-agent-offline-review-readable
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-offline-review-readable
- file: `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_ops_format.py`; `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_status_tools.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_intelligent_bot_ops_format.py`; `D:/Project/YunxiBakeBot/tests/api/test_wecom_intelligent_bot_plugin_api.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_intelligent_bot_ops_format.py tests/api/test_wecom_intelligent_bot_plugin_api.py::test_offline_review_summary_returns_latest_run tests/api/test_wecom_intelligent_bot_plugin_api.py::test_offline_review_summary_hides_raw_skipped_reason tests/scripts/test_check_wecom_employee_agent_callback.py::test_evaluate_reply_rejects_raw_offline_review_skip_marker -q --no-cov`; `python -m pytest tests/service/test_wecom_intelligent_bot_ops_format.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/api/test_wecom_intelligent_bot_plugin_api.py -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py -q --no-cov`; `python -m ruff check app/service/wecom/intelligent_bot_ops_format.py app/service/wecom/intelligent_bot_status_tools.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_intelligent_bot_ops_format.py tests/api/test_wecom_intelligent_bot_plugin_api.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/wecom/intelligent_bot_ops_format.py app/service/wecom/intelligent_bot_status_tools.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_intelligent_bot_ops_format.py tests/api/test_wecom_intelligent_bot_plugin_api.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-offline-review-readable-e27090c.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-offline-review-readable-e27090c.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 优化离线复盘摘要员工可读性
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 离线复盘摘要原先会把 `outside_night_window` 和 `skippedReason` 这类内部调度字段拼到员工回复中。本轮在格式层新增中文跳过原因映射和统一下一步动作，单工具调试字段继续保留，但员工可见 `result` 与 `nextAction` 不再暴露内部字段。探针样本新增离线复盘禁用词，callback 语义检查补拒绝裸跳过字段回归。本地相关测试、员工 Agent 46 条测试、43 问规划、Ruff、文件体量、项目红线、架构扫描、编码检查、mistake ledger 和 diff 空白检查均通过；已同步生产 `0.74.13 / e27090cb1`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过，`offline-review-summary` 预览为“当前不在夜间复盘窗口，最近一轮没有执行...”，未出现内部字段；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-029：企微员工助手待人工摘要 UMP 标记清理

- trace_id: 20260704-wecom-employee-agent-handoff-ump-cleanup
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-handoff-ump-cleanup
- file: `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_ops_format.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_intelligent_bot_ops_format.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_intelligent_bot_ops_format.py tests/scripts/test_check_wecom_employee_agent_callback.py::test_evaluate_reply_rejects_ump_marker_in_handoff_summary -q --no-cov`; `python -m pytest tests/service/test_wecom_intelligent_bot_ops_format.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/api/test_wecom_intelligent_bot_plugin_api.py -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py -q --no-cov`; `python -m ruff check app/service/wecom/intelligent_bot_ops_format.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_intelligent_bot_ops_format.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/wecom/intelligent_bot_ops_format.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_intelligent_bot_ops_format.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-handoff-ump-dangling-db81764.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-handoff-ump-dangling-db81764.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 清理待人工摘要 UMP 标记
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 待人工摘要会话预览中出现 `[UMP: type=card&id=...]` 商品卡片协议标记；生产首次同步后进一步发现历史摘要可能保存缺少右中括号的残缺 `[UMP: ...` 尾部。现复用既有 `parse_ump_tags()` 清完整标记，并新增残缺 UMP 尾部清理；同时 43 问探针的待人工样本禁止 `UMP / type=card / %E5%` 残留，避免语义验收漏过机器协议噪声。本地相关测试、员工 Agent 46 条测试、43 问规划、Ruff、文件体量、项目红线、架构扫描、编码检查、mistake ledger 和 diff 空白检查均通过；已同步生产 `0.74.11 / db8176469`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过，`handoff-pending` 与 `casual-handoff-pending` 预览均不再出现 UMP 协议噪声；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-028：企微员工助手运营状态可读性

- trace_id: 20260704-wecom-employee-agent-ops-readable
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-ops-readable
- file: `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_ops_format.py`; `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_status_tools.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_intelligent_bot_ops_format.py`; `D:/Project/YunxiBakeBot/tests/api/test_wecom_intelligent_bot_plugin_api.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_intelligent_bot_ops_format.py tests/api/test_wecom_intelligent_bot_plugin_api.py::test_handoff_pending_returns_pending_transfers tests/api/test_wecom_intelligent_bot_plugin_api.py::test_ops_summary_returns_observability_counts -q --no-cov`; `python -m ruff check app/service/wecom/intelligent_bot_ops_format.py app/service/wecom/intelligent_bot_status_tools.py tests/service/test_wecom_intelligent_bot_ops_format.py tests/api/test_wecom_intelligent_bot_plugin_api.py`; `python -m ruff format --check app/service/wecom/intelligent_bot_ops_format.py app/service/wecom/intelligent_bot_status_tools.py tests/service/test_wecom_intelligent_bot_ops_format.py tests/api/test_wecom_intelligent_bot_plugin_api.py`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/api/test_wecom_intelligent_bot_plugin_api.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-ops-readable-91ab70c.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-ops-readable-91ab70c.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 优化员工助手运营状态可读性
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 运营状态和待人工回复从机器字段展示收口为员工可读动作摘要：`attention` 转为“系统需要关注”，观察台计数只展示有问题的类别并提示先看 Webhook 失败或内容回写历史；待人工列表继续只展示工单尾号，同时增加已脱敏的会话摘要预览。本地相关测试、员工 Agent 80 条测试、43 问规划、Ruff、文件体量、项目红线、架构扫描、编码检查、mistake ledger 和 diff 空白检查均通过；已同步生产 `0.74.9 / 91ab70cc9`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过，`ops-status` 与 `casual-ops-status` 均返回“系统需要关注...”中文动作摘要；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-027：企微员工助手纯文本回复清理

- trace_id: 20260704-wecom-employee-agent-plain-text-reply
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-plain-text-reply
- file: `D:/Project/YunxiBakeBot/app/service/chat_reply.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_service.py`; `D:/Project/YunxiBakeBot/scripts/check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_callback_semantics.py`; `D:/Project/YunxiBakeBot/tests/service/test_chat_refactor.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_chat_refactor.py::test_postprocess_reply_removes_markdown_marks tests/service/test_wecom_employee_agent.py::test_employee_agent_reply_removes_markdown_from_polish tests/scripts/test_check_wecom_employee_agent_callback.py::test_evaluate_reply_rejects_markdown_decorations -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python scripts/check_file_sizes.py`; `python -m ruff check app/service/chat_reply.py app/service/wecom/employee_agent_service.py scripts/check_wecom_employee_agent_callback.py scripts/wecom_employee_agent_callback_semantics.py tests/service/test_chat_refactor.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/chat_reply.py app/service/wecom/employee_agent_service.py scripts/check_wecom_employee_agent_callback.py scripts/wecom_employee_agent_callback_semantics.py tests/service/test_chat_refactor.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-plain-text-a4c9f8d.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-plain-text-a4c9f8d.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 清理员工助手 Markdown 装饰
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 生产回调探针预览暴露 `**尾号...**`、`**优先级...**` 等 Markdown 装饰残留。员工助手最终回复现统一复用 `clean_plain_text_reply()`，覆盖确定性回复、知识/运营跳过润色回复和 LLM 润色回复；回调验收新增全局纯文本规则，出现 `**`、`__` 或反引号即判定语义失败。本地相关测试、43 问规划、Ruff、文件体量、项目红线、架构扫描、编码检查、mistake ledger 和 diff 空白检查均通过；已同步生产 `0.74.7 / a4c9f8d0e`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过，`fulfillment-risk-list`、`tomorrow-pending-orders`、`today-action-items`、`casual-order-attention`、`top-products` 和 `casual-top-product` 的回复预览均不再出现 `**` 或反引号；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-026：企微员工助手空订单查询范围保真

- trace_id: 20260704-wecom-employee-agent-empty-order-scope
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-empty-order-scope
- file: `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_order_empty_format.py`; `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_order_format.py`; `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_order_lookup.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_reply_guard.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_intelligent_bot_order_lookup.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python scripts/check_file_sizes.py`; `python -m pytest tests/service/test_wecom_intelligent_bot_order_lookup.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m pytest tests/service/test_wecom_employee_agent_file_size.py -q --no-cov`; `python -m ruff check app/service/wecom/intelligent_bot_order_empty_format.py app/service/wecom/intelligent_bot_order_format.py app/service/wecom/intelligent_bot_order_lookup.py app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/wecom/intelligent_bot_order_empty_format.py app/service/wecom/intelligent_bot_order_format.py app/service/wecom/intelligent_bot_order_lookup.py app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python scripts/check_project.py --skip-tests`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-empty-order-scope-c70aff4.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-empty-order-scope-c70aff4.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 保留员工助手空订单查询范围
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 订单动态查询为空时，员工助手会基于 `OrderQueryPlan` 的约送日期、约送时间段、状态、无物流、履约风险和商品关键词生成具体范围说明；LLM 润色若引入“换商品名 / 时间范围再查 / 日期需确认”等泛化绕路话术，会回退确定性工具结果。空结果范围 helper 已拆入独立文件，避免继续扩大订单格式文件。本地文件体量、相关测试、43 问规划、Ruff、项目红线、架构扫描、编码检查、mistake ledger 和 diff 空白检查均通过；已同步生产 `0.74.6 / c70aff42`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过，`evening-pending-orders` 返回约送日期 2026-07-04、时间 18:00-23:59 的具体空结果范围，未出现“换商品名 / 时间范围再查”；`after-tomorrow-pending-orders` 与 `next-monday-pending-orders` 也通过空结果泛化绕路禁用词检查；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-025：企微员工助手商品话术无命中兜底

- trace_id: 20260704-wecom-employee-agent-product-knowledge-miss
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-product-knowledge-miss
- file: `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_mixed_reply.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_service.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m ruff check app/service/wecom/employee_agent_mixed_reply.py app/service/wecom/employee_agent_service.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/wecom/employee_agent_mixed_reply.py app/service/wecom/employee_agent_service.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-product-knowledge-miss-a455817.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-product-knowledge-miss-a455817.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 优化员工助手商品话术无命中兜底
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 商品实时数据 + 知识库话术组合问法在知识库无命中时，不再把“未找到匹配知识。”直接拼给员工；新增多工具回复整理，基于实时库存生成员工可执行建议，并保留纯知识问法的无命中提示。共享探针已禁止商品+话术样本出现“未找到匹配知识”。本地相关测试 63 条通过，规划探针 43/43 通过；已同步生产 `0.74.5 / a4558172`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过，`product-stock-recommend-replacement` 和 `product-stock-customer-reply` 均返回基于库存的员工建议，未裸露“未找到匹配知识”；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-024：企微员工助手配送知识兜底增强

- trace_id: 20260704-wecom-employee-agent-delivery-knowledge
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-delivery-knowledge
- file: `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_knowledge_format.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_intelligent_bot_knowledge_reply.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/docs/harness-engineering/core/evidence-index.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_intelligent_bot_knowledge_reply.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py -q --no-cov`; `python -m pytest tests/scripts/test_check_wecom_employee_agent_callback.py::test_run_callback_checks_covers_employee_queries -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py::test_employee_agent_knowledge_reply_skips_llm_polish -q --no-cov`; `python -m pytest tests/service/test_wecom_intelligent_bot_knowledge_reply.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/service/test_wecom_employee_agent.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m ruff check app/service/wecom/intelligent_bot_knowledge_format.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_intelligent_bot_knowledge_reply.py`; `python -m ruff format --check app/service/wecom/intelligent_bot_knowledge_format.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_intelligent_bot_knowledge_reply.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; `git diff --check`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-delivery-knowledge-f0aabff.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-delivery-knowledge-f0aabff.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 增强员工助手配送知识兜底
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手知识类问法 `明天能配送吗` 在知识库无命中时，从弱提示“知识库没有命中”升级为员工可复制的保守话术：以门店实际排期为准，不承诺一定准时送达，先收集客户期望配送时间、地址区域和联系方式，急单、指定准确送达或疑似超区需求转人工确认。共享探针强化 `delivery-knowledge`，要求回复包含配送和排期/确认/人工/可配送时段等动作语义。本地相关测试 60 条通过，规划探针 43/43 通过；已同步生产 `0.74.4 / f0aabffa`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过，`delivery-knowledge` 返回可复制配送话术，未再出现“知识库没有命中”弱兜底；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-023：企微员工助手无物流标记保真

- trace_id: 20260704-wecom-employee-agent-missing-logistics-guard
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-missing-logistics-guard
- file: `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_reply_guard.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/docs/harness-engineering/core/evidence-index.md`
- command: production failed probe `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn` on `0.74.1 / bd278093b` returned 42/43, failed `missing-logistics-list`; `python -m pytest tests/service/test_wecom_employee_agent.py -q --no-cov`; `python -m pytest tests/scripts/test_check_wecom_employee_agent_callback.py -q --no-cov`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m ruff check app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py`; `python -m ruff format --check app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_text_encoding.py`; `python scripts/check_mistake_ledger.py`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `git diff --check`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-missing-logistics-00a99a3.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-missing-logistics-00a99a3.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 保留员工助手无物流标记
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 生产回调探针显示 `missing-logistics-list` 的确定性结果含“暂无物流”，但 LLM 润色概括成普通“未发货”列表，丢失员工真正要看的物流状态。补丁在回复守卫中要求确定性结果含“暂无物流/无物流”时，润色结果必须保留“物流”，否则回退确定性结果；同时将两个无物流回调样本升级为必须包含“物流”。本地相关测试 58 条通过，规划探针 43/43 通过；已同步生产 `0.74.3 / 00a99a3f5`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过，`missing-logistics-list` 回复保留“暂无物流”，`casual-missing-logistics` 回复保留“物流”；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-022：企微员工助手发货压力口径一致性

- trace_id: 20260704-wecom-employee-agent-fulfillment-pressure
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-fulfillment-pressure
- file: `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_order_format.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_reply_guard.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_intelligent_bot_order_lookup.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/scripts/test_check_wecom_employee_agent_callback.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/repository/test_youzan_repo.py tests/service/test_wecom_employee_agent_file_size.py tests/service/test_wecom_product_filter.py -q --no-cov`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`; `python -m ruff check app/service/wecom/intelligent_bot_order_format.py app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/wecom/intelligent_bot_order_format.py app/service/wecom/employee_agent_reply_guard.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/scripts/test_check_wecom_employee_agent_callback.py`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `git diff --check`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-fulfillment-pressure-686aa43.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-fulfillment-pressure-686aa43.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 统一员工助手发货压力口径
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手“今天发货压力大不大”类履约风险列表问法复用今日经营待办的压力阈值，确定性结果补充“发货压力：偏高/中等/低”和待处理/履约风险计数；回复守卫要求润色结果保留同一压力等级，避免把 5 单偏高场景说成“压力不大”。共享探针强化 `casual-fulfillment-pressure`，禁止“压力不大”逃过验收。本地相关测试 97 条通过，规划探针 43/43 通过；已同步生产 `0.74.1 / 686aa43c1`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过，`casual-fulfillment-pressure` 回复为“发货压力偏高”；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-021：企微员工助手今日经营待办洞察

- trace_id: 20260704-wecom-employee-agent-action-insights
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-action-insights
- file: `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_order_insights.py`; `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_order_format.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_privacy_format.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/repository/test_youzan_repo.py tests/service/test_wecom_employee_agent_file_size.py tests/service/test_wecom_product_filter.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`; `python -m ruff check app/service/wecom/intelligent_bot_order_insights.py app/service/wecom/intelligent_bot_order_format.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_privacy_format.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/wecom/intelligent_bot_order_insights.py app/service/wecom/intelligent_bot_order_format.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_privacy_format.py tests/scripts/test_check_wecom_employee_agent_callback.py`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `git diff --check`; production failed probe `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn` on `0.72.1 / e46a84aab` returned 42/43, failed `today-action-items`; fix verification `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/repository/test_youzan_repo.py tests/service/test_wecom_employee_agent_file_size.py tests/service/test_wecom_product_filter.py -q --no-cov`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`; `python -m ruff check app/service/wecom/employee_agent_reply_guard.py tests/service/test_wecom_employee_agent.py`; `python -m ruff format --check app/service/wecom/employee_agent_reply_guard.py tests/service/test_wecom_employee_agent.py`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-action-insights-e46a84a.bundle"`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-action-insight-guard-0d9e9b4.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-action-insights-e46a84a.bundle`; cleanup `rm /opt/yunxibakebot/wecom-action-insight-guard-0d9e9b4.bundle`
- result: pass
- related_logbook: 2026-07-04 - feat(wecom): 增强员工助手今日经营待办洞察
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手 `action_items` 订单结果从字段汇总升级为确定性经营洞察：回复包含今日订单量和金额、发货压力、待处理/履约风险/退款/无物流计数、优先级标题和下一步动作。仍复用既有订单动态查询结果，不新增 SQL、不改变企微回调入口。共享探针强化“今天有什么要盯的 / 今天订单有没有需要注意的”必须包含“优先级”和“压力”；本地相关测试 92 条通过，规划探针 43/43 通过。首次同步生产 `0.72.1 / e46a84aab` 后 `/health` 与 `/ready` 通过，但回调探针 42/43，`today-action-items` 因 LLM 润色删掉“压力”失败；已补 `preserve_tool_facts` 经营洞察标记守卫，本地相关测试 94 条通过，规划探针 43/43 通过。已同步生产 `0.74.0 / 0d9e9b47e`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过；`today-action-items` 与 `casual-order-attention` 均保留“优先级 / 压力”经营洞察标记；本轮两个同步 bundle 已按明确单文件路径清理。

## E-20260704-020：企微员工助手润色回复隐私回退

- trace_id: 20260704-wecom-employee-agent-privacy-polish-guard
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-privacy-polish-guard
- file: `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_reply_guard.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/repository/test_youzan_repo.py tests/service/test_wecom_employee_agent_file_size.py tests/service/test_wecom_product_filter.py -q --no-cov`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`; `python -m ruff check app/service/wecom/employee_agent_reply_guard.py tests/service/test_wecom_employee_agent.py`; `python -m ruff format --check app/service/wecom/employee_agent_reply_guard.py tests/service/test_wecom_employee_agent.py`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `git diff --check`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-privacy-polish-1053f6b.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-privacy-polish-1053f6b.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 员工助手润色回复隐私回退
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 生产 43 项员工助手回调探针中，旧混合问法“还有哪些没发货，怎么跟客户说”被 LLM 润色引入“完整订单号”提示，确定性工具结果本身安全。补丁在回复守卫中检测润色结果是否新增手机号、完整订单号、完整地址、买家 ID 或英文私有字段名，命中则回退确定性回复。本地相关测试 90 条通过，规划探针 43/43 通过；已同步生产 `0.72.0 / 1053f6be5`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过，旧混合问法已通过线上语义和隐私检查；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-019：企微员工助手更宽自然时间问法

- trace_id: 20260704-wecom-employee-agent-wider-date-phrases
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-wider-date-phrases
- file: `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_date.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_date_calendar.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_keywords.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_stop_words.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_query.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent_file_size.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/repository/test_youzan_repo.py tests/service/test_wecom_employee_agent_file_size.py tests/service/test_wecom_product_filter.py -q --no-cov`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`; `python -m ruff check <touched-python-files>`; `python -m ruff format --check <touched-python-files>`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `git diff --check`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-wider-dates-5d4b3e8.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-wider-dates-5d4b3e8.bundle`
- result: pass
- related_logbook: 2026-07-04 - feat(wecom): 支持员工助手更宽自然时间问法
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和计划字段；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手订单日期解析新增“本月/这个月/当月”“上周/上星期”“周五/星期五”“下周一/下星期一”等自然时间表达，继续生成 `date_from/date_to/date_field` 结构化计划，不生成 SQL。共享探针从 39 项扩展到 43 项，新增“本月销售额怎么样”“上周退款多少”“下周一有哪些待处理订单”“周五椰椰凤梨卖了几单”；本地规划 43/43 通过，相关测试 88 条通过；已同步生产 `0.72.0 / 1053f6be5`，`/health` ok，`/ready` ready，43/43 端到端加密回调探针通过；新增四条自然时间问法均通过线上语义和隐私检查；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-018：企微员工助手自然日期订单问法

- trace_id: 20260704-wecom-employee-agent-natural-dates
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-natural-dates
- file: `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_date.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_keywords.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/repository/test_youzan_repo.py tests/service/test_wecom_employee_agent_file_size.py tests/service/test_wecom_product_filter.py -q --no-cov`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`; `python -m ruff check app/service/wecom/employee_agent_order_date.py app/service/wecom/employee_agent_order_keywords.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/wecom/employee_agent_order_date.py app/service/wecom/employee_agent_order_keywords.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-natural-dates-734a74e.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-natural-dates-734a74e.bundle`
- result: pass
- related_logbook: 2026-07-04 - feat(wecom): 支持员工助手自然日期订单问法
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和计划字段；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手订单日期解析新增“后天”“周末/本周末/这个周末”和具体月日表达，继续生成 `date_from/date_to/date_field` 结构化计划，不生成 SQL。共享探针从 36 项扩展到 39 项，覆盖“后天有哪些待处理订单”“周末有哪些待处理订单”“7月5日椰椰凤梨卖了几单”；本地规划 39/39 通过，相关测试 84 条通过；已同步生产 `0.70.8 / 734a74e60`，`/health` ok，`/ready` ready，39/39 端到端加密回调探针通过；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-017：企微员工助手按约送日期查询订单

- trace_id: 20260704-wecom-employee-agent-date-field
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-date-field
- file: `D:/Project/YunxiBakeBot/app/models/employee_agent.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_date.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_query.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_llm_plan.py`; `D:/Project/YunxiBakeBot/app/repository/youzan_order_repo.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/scripts/check_wecom_employee_agent_plans.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/repository/test_youzan_repo.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/repository/test_youzan_repo.py tests/service/test_wecom_employee_agent_file_size.py tests/service/test_wecom_product_filter.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`; `python -m ruff check app/models/employee_agent.py app/repository/youzan_order_repo.py app/service/wecom/employee_agent_order_date.py app/service/wecom/employee_agent_order_query.py app/service/wecom/employee_agent_order_keywords.py app/service/wecom/employee_agent_llm_plan.py scripts/wecom_employee_agent_probe_cases.py scripts/check_wecom_employee_agent_plans.py tests/service/test_wecom_employee_agent.py tests/repository/test_youzan_repo.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/models/employee_agent.py app/repository/youzan_order_repo.py app/service/wecom/employee_agent_order_date.py app/service/wecom/employee_agent_order_query.py app/service/wecom/employee_agent_order_keywords.py app/service/wecom/employee_agent_llm_plan.py scripts/wecom_employee_agent_probe_cases.py scripts/check_wecom_employee_agent_plans.py tests/service/test_wecom_employee_agent.py tests/repository/test_youzan_repo.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-date-field-d4058b3.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-date-field-d4058b3.bundle`
- result: pass
- related_logbook: 2026-07-04 - feat(wecom): 支持员工助手按约送日期查询订单
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和计划字段；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手新增 `date_field` 计划字段，用于区分经营统计的下单/支付日期和履约问法的约送日期。“明天有哪些待处理订单”会生成 `date_from/date_to=明天`、`date_field=delivery_time`、待处理状态；repository 仅通过白名单表达式在 `ORDER_TIME_EXPR` 与 `DELIVERY_TIME_EXPR` 间切换，仍为参数化 SQL。共享探针从 35 项扩到 36 项，本地规划 36/36 通过；已同步生产 `0.70.6 / d4058b3e6`，`/health` ok，`/ready` ready，36/36 端到端加密回调探针通过；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-016：企微员工助手配送时间段订单查询

- trace_id: 20260704-wecom-employee-agent-delivery-window
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-delivery-window
- file: `D:/Project/YunxiBakeBot/app/models/employee_agent.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_delivery_time.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_date.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_query.py`; `D:/Project/YunxiBakeBot/app/repository/youzan_order_repo.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/scripts/check_wecom_employee_agent_plans.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/repository/test_youzan_repo.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/repository/test_youzan_repo.py tests/service/test_wecom_employee_agent_file_size.py tests/service/test_wecom_product_filter.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`; `python -m ruff check app/models/employee_agent.py app/repository/youzan_order_repo.py app/service/wecom/employee_agent_order_delivery_time.py app/service/wecom/employee_agent_order_date.py app/service/wecom/employee_agent_order_query.py app/service/wecom/employee_agent_order_keywords.py app/service/wecom/employee_agent_llm_plan.py app/service/wecom/employee_agent_non_order_plan.py scripts/wecom_employee_agent_probe_cases.py scripts/check_wecom_employee_agent_plans.py tests/service/test_wecom_employee_agent.py tests/repository/test_youzan_repo.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_agent_file_size.py`; `python -m ruff format --check app/models/employee_agent.py app/repository/youzan_order_repo.py app/service/wecom/employee_agent_order_delivery_time.py app/service/wecom/employee_agent_order_date.py app/service/wecom/employee_agent_order_query.py app/service/wecom/employee_agent_order_keywords.py app/service/wecom/employee_agent_llm_plan.py app/service/wecom/employee_agent_non_order_plan.py scripts/wecom_employee_agent_probe_cases.py scripts/check_wecom_employee_agent_plans.py tests/service/test_wecom_employee_agent.py tests/repository/test_youzan_repo.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_agent_file_size.py`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-delivery-window-18b6aac.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-delivery-window-18b6aac.bundle`
- result: pass
- related_logbook: 2026-07-04 - feat(wecom): 支持员工助手配送时间段订单查询
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和计划字段；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手新增配送时间段查询计划，支持“晚上还有哪些待处理订单”这类口语问法。规划层输出 `delivery_time_start=18:00`、`delivery_time_end=23:59` 和待处理状态，仓储层以白名单字段和参数化 SQL 过滤 `delivery_time`，不让模型生成 SQL。共享探针从 34 项扩到 35 项，本地规划 35/35 通过；已同步生产 `0.70.4 / 18b6aacfd`，`/health` ok，`/ready` ready，35/35 端到端加密回调探针通过；本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-015：企微员工助手润色回复库存数值保真

- trace_id: 20260704-wecom-employee-agent-reply-fact-guard
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-reply-fact-guard
- file: `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_reply_guard.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_service.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_text_encoding.py`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-product-knowledge-bcaaa61.bundle"`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-revenue-hint-987f370.bundle"`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-reply-guard-3aee20c.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-product-knowledge-bcaaa61.bundle`; cleanup `rm /opt/yunxibakebot/wecom-revenue-hint-987f370.bundle`; cleanup `rm /opt/yunxibakebot/wecom-reply-guard-3aee20c.bundle`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 员工助手润色回复保留商品库存数值
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 生产复跑 34 项员工助手回调探针时，商品+知识替代推荐回复偶发丢失库存数字，说明 LLM 润色需要事实保真兜底。补丁新增回复守卫：确定性工具结果含库存数值而润色结果缺失时，回退确定性回复。已同步生产 `0.70.2 / 3aee20c15`，`/health` ok，`/ready` ready，34/34 端到端加密回调探针通过；本轮三个同步 bundle 已按明确单文件路径清理。

## E-20260704-014：企微员工助手经营汇总下一步提示收紧

- trace_id: 20260704-wecom-employee-agent-revenue-summary-hint
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-revenue-summary-hint
- file: `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_order_format.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_privacy_format.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_privacy_format.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python scripts/check_project.py --skip-tests`; `python scripts/check_file_sizes.py`; `python scripts/check_text_encoding.py`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 收紧员工助手经营汇总下一步提示
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令和探针名称；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 生产 34 项员工助手回调探针中，商品+知识混合新增样本已通过；旧经营汇总样本“今天营业额多少”因订单统计 `next_action` 带后台核对兜底，被 LLM 润色为绕路提示。补丁收紧成功统计结果的下一步提示，只保留尾号追问详情，避免经营汇总类回答退回后台核对。已随 `0.70.2 / 3aee20c15` 生产复跑确认 34/34 通过。

## E-20260704-013：企微员工助手商品数据加话术混合问法

- trace_id: 20260704-wecom-employee-agent-product-knowledge
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-product-knowledge
- file: `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_non_order_plan.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_product_query.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_plan.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_capabilities.py`; `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_product_filter.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_product_filter.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/reports/harness/handoff-20260704-wecom-employee-agent-product-knowledge.md`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/repository/test_youzan_repo.py tests/service/test_wecom_employee_agent_file_size.py tests/service/test_wecom_product_filter.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`; `python -m ruff check app/service/wecom/employee_agent_non_order_plan.py app/service/wecom/employee_agent_order_plan.py app/service/wecom/employee_agent_product_query.py app/service/wecom/employee_agent_capabilities.py app/service/wecom/intelligent_bot_product_filter.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/service/test_wecom_product_filter.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/wecom/employee_agent_non_order_plan.py app/service/wecom/employee_agent_order_plan.py app/service/wecom/employee_agent_product_query.py app/service/wecom/employee_agent_capabilities.py app/service/wecom/intelligent_bot_product_filter.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/service/test_wecom_product_filter.py tests/scripts/test_check_wecom_employee_agent_callback.py`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`
- result: pass
- related_logbook: 2026-07-04 - feat(wecom): 支持员工助手商品数据加话术混合问法
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令、探针名称和计划字段；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手新增商品实时数据 + 知识库回复组合规划，覆盖“伯牙绝弦库存不够怎么推荐替代”“伯牙绝弦没货怎么跟客户说”等商品经营问法。规划层新增非订单模块，商品+知识分支优先于客户线索/运营类工具，避免“客户”关键词误路由。商品过滤清理替代推荐和对客回复噪声词，仍能命中真实商品。共享探针从 32 项扩到 34 项，本地规划 34/34 通过；已随 `0.70.2 / 3aee20c15` 生产复跑确认 34/34 通过。

## E-20260704-012：企微员工助手订单数据加话术混合问法

- trace_id: 20260704-wecom-employee-agent-order-knowledge
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-order-knowledge
- file: `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_capabilities.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_keywords.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_predicates.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_query.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_plan.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_service.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/repository/test_youzan_repo.py tests/service/test_wecom_employee_agent_file_size.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python scripts/check_file_sizes.py`; `python scripts/check_project.py --skip-tests`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-order-knowledge-7d7cc21.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-order-knowledge-7d7cc21.bundle`
- result: pass
- related_logbook: 2026-07-04 - feat(wecom): 支持员工助手订单数据加话术混合问法
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令、探针名称和计划字段；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手 `MULTI_TOOL` 新增订单动态查询 + 知识库回复组合能力，覆盖“还有哪些没发货，怎么跟客户说”“今天有退款订单，怎么回复客户”等混合问法。纯规则问法仍走知识库，数据问法仍保留订单查询计划；话术短语已从订单 keyword 中清理，避免误过滤商品或订单。共享探针从 30 项扩到 32 项，本地规划 32/32 通过。已同步生产 `0.69.15 / 7d7cc21`，`/health` ok，`/ready` ready，32/32 端到端加密回调探针通过；新增两条订单+话术生产回复均通过语义和隐私检查。本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-011：企微员工助手今日经营待办概览

- trace_id: 20260704-wecom-employee-agent-action-items
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-action-items
- file: `D:/Project/YunxiBakeBot/app/models/employee_agent.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_capabilities.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_keywords.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_predicates.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_query.py`; `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_order_action_items.py`; `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_order_lookup.py`; `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_order_format.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_intelligent_bot_order_lookup.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_privacy_format.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/repository/test_youzan_repo.py tests/service/test_wecom_employee_agent_file_size.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python scripts/check_file_sizes.py`; `python -m ruff check app/models/employee_agent.py app/service/wecom/employee_agent_capabilities.py app/service/wecom/employee_agent_order_keywords.py app/service/wecom/employee_agent_order_predicates.py app/service/wecom/employee_agent_order_query.py app/service/wecom/intelligent_bot_order_action_items.py app/service/wecom/intelligent_bot_order_lookup.py app/service/wecom/intelligent_bot_order_format.py tests/service/test_wecom_employee_agent.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/service/test_wecom_employee_privacy_format.py tests/scripts/test_check_wecom_employee_agent_callback.py scripts/wecom_employee_agent_probe_cases.py`; `python -m ruff format --check app/models/employee_agent.py app/service/wecom/employee_agent_capabilities.py app/service/wecom/employee_agent_order_keywords.py app/service/wecom/employee_agent_order_predicates.py app/service/wecom/employee_agent_order_query.py app/service/wecom/intelligent_bot_order_action_items.py app/service/wecom/intelligent_bot_order_lookup.py app/service/wecom/intelligent_bot_order_format.py tests/service/test_wecom_employee_agent.py tests/service/test_wecom_intelligent_bot_order_lookup.py tests/service/test_wecom_employee_privacy_format.py tests/scripts/test_check_wecom_employee_agent_callback.py scripts/wecom_employee_agent_probe_cases.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`; architecture scans `rg "from app\.repository" app/api -g "*.py"`, `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`, `rg "from app\.(service|repository|api)" app/models -g "*.py"`; production `git rev-parse --short HEAD && cat VERSION && systemctl is-active yunxibakebot`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; cleanup `Remove-Item "D:\Project\YunxiBakeBot\reports\wecom-action-items-f4fdad4.bundle"`; cleanup `rm /opt/yunxibakebot/wecom-action-items-f4fdad4.bundle`
- result: pass
- related_logbook: 2026-07-04 - feat(wecom): 支持员工助手今日经营待办概览
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令、探针名称和计划字段；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手新增 `action_items` 订单计划类型，用于“今天有什么要盯的”“今天订单有没有需要注意的”等自由问法。service 层组合既有白名单查询计划输出今日订单总览、待处理、履约风险、退款/售后和无物流提醒，repository 层不新增 SQL 形态且仍参数化执行。共享探针从 28 项扩到 30 项，本地规划 30/30 通过。已同步生产 `0.69.14 / f4fdad4`，`/health` ok，`/ready` ready，30/30 端到端加密回调探针通过；新增两条 action_items 生产回复均为员工可读待办概览且通过隐私检查。本轮同步 bundle 已按明确单文件路径清理。

## E-20260704-010：企微员工助手履约风险问法

- trace_id: 20260704-wecom-employee-agent-fulfillment-risk
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-fulfillment-risk
- file: `D:/Project/YunxiBakeBot/app/models/employee_agent.py`; `D:/Project/YunxiBakeBot/app/repository/youzan_order_repo.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_capabilities.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_keywords.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_predicates.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_query.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_llm_plan.py`; `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_order_format.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/scripts/check_wecom_employee_agent_plans.py`; `D:/Project/YunxiBakeBot/tests/repository/test_youzan_repo.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_privacy_format.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/repository/test_youzan_repo.py tests/service/test_wecom_employee_agent_file_size.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; local `Invoke-RestMethod http://127.0.0.1:7001/health`; local `Invoke-RestMethod http://127.0.0.1:7001/ready`; local `python scripts/check_wecom_employee_agent_callback.py --json --base-url http://127.0.0.1:7001`; `python -m ruff check app/models/employee_agent.py app/repository/youzan_order_repo.py app/service/wecom/employee_agent_capabilities.py app/service/wecom/employee_agent_llm_plan.py app/service/wecom/employee_agent_order_constants.py app/service/wecom/employee_agent_order_keywords.py app/service/wecom/employee_agent_order_predicates.py app/service/wecom/employee_agent_order_query.py app/service/wecom/intelligent_bot_order_format.py scripts/check_wecom_employee_agent_plans.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/repository/test_youzan_repo.py tests/service/test_wecom_employee_agent_file_size.py`; `python -m ruff format --check app/models/employee_agent.py app/repository/youzan_order_repo.py app/service/wecom/employee_agent_capabilities.py app/service/wecom/employee_agent_llm_plan.py app/service/wecom/employee_agent_order_constants.py app/service/wecom/employee_agent_order_keywords.py app/service/wecom/employee_agent_order_predicates.py app/service/wecom/employee_agent_order_query.py app/service/wecom/intelligent_bot_order_format.py scripts/check_wecom_employee_agent_plans.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/repository/test_youzan_repo.py tests/service/test_wecom_employee_agent_file_size.py`; `python scripts/check_project.py --skip-tests`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`
- result: pass
- related_logbook: 2026-07-04 - feat(wecom): 支持员工助手履约风险问法
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令、探针名称和计划字段；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手订单动态查询新增 `needs_fulfillment_risk` 查询计划字段，仓库层白名单筛选待发货/待收货且有约送时间的订单，并按 `delivery_time` 升序给员工展示优先处理顺序。共享探针从 26 项扩到 28 项，本地 28/28 规划通过；新增履约风险回调样本在本地通过。本地回调整体 21/28，失败的 7 个旧样本依赖生产商品/订单数据，不能作为本轮行为失败结论。已同步生产 `0.69.12 / 5d3a376`，`/health`、`/ready` 和 28/28 回调探针通过，生产“哪些单快超时了”返回待履约订单尾号、状态、约送时间和物流提示。

## E-20260704-009：企微员工助手退款订单数据问法

- trace_id: 20260704-wecom-employee-agent-refund-query
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-refund-query
- file: `D:/Project/YunxiBakeBot/app/models/employee_agent.py`; `D:/Project/YunxiBakeBot/app/repository/youzan_order_repo.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_capabilities.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_constants.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_plan.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_query.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_llm_plan.py`; `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_order_format.py`; `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_order_lookup.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/scripts/check_wecom_employee_agent_plans.py`; `D:/Project/YunxiBakeBot/tests/repository/test_youzan_repo.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_privacy_format.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/repository/test_youzan_repo.py tests/service/test_wecom_employee_agent_file_size.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; pre-production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn` on production `0.69.10`; `python -m ruff check app/models/employee_agent.py app/service/wecom/employee_agent_capabilities.py app/service/wecom/employee_agent_order_constants.py app/service/wecom/employee_agent_order_query.py app/service/wecom/employee_agent_order_plan.py app/service/wecom/employee_agent_llm_plan.py app/service/wecom/intelligent_bot_order_format.py app/service/wecom/intelligent_bot_order_lookup.py app/repository/youzan_order_repo.py scripts/check_wecom_employee_agent_plans.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/repository/test_youzan_repo.py`; `python -m ruff format --check app/models/employee_agent.py app/service/wecom/employee_agent_capabilities.py app/service/wecom/employee_agent_order_constants.py app/service/wecom/employee_agent_order_query.py app/service/wecom/employee_agent_order_plan.py app/service/wecom/employee_agent_llm_plan.py app/service/wecom/intelligent_bot_order_format.py app/service/wecom/intelligent_bot_order_lookup.py app/repository/youzan_order_repo.py scripts/check_wecom_employee_agent_plans.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/repository/test_youzan_repo.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`
- result: pass
- related_logbook: 2026-07-04 - feat(wecom): 支持员工助手退款订单数据问法
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令、探针名称和计划字段；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手订单动态查询新增 `needs_refund` 查询计划字段，仓库层白名单执行 `refund_state != 0`，用于“今天有退款订单吗”“本周退款多少”等经营异常数据问法；“退款规则/话术/政策”仍走知识库。共享探针从 24 项扩到 26 项，本地 26/26 规划通过；用新探针打旧生产 `0.69.10` 时 `this-week-refund-summary` 按预期失败，旧版本误路由到知识库。已同步生产 `0.69.11 / 31e64dd`，`/health`、`/ready` 和 26/26 回调探针通过，生产“本周退款多少”返回退款订单数、金额和状态分布。

## E-20260704-008：企微员工助手订单经营金额问法

- trace_id: 20260704-wecom-employee-agent-revenue-summary
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-revenue-summary
- file: `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_capabilities.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_constants.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_query.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_agent_file_size.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; pre-production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn` on production `0.69.9`; `python -m ruff check app/service/wecom/employee_agent_capabilities.py app/service/wecom/employee_agent_order_constants.py app/service/wecom/employee_agent_order_query.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/service/test_wecom_employee_agent_file_size.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/wecom/employee_agent_capabilities.py app/service/wecom/employee_agent_order_constants.py app/service/wecom/employee_agent_order_query.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/service/test_wecom_employee_agent_file_size.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`
- result: pass
- related_logbook: 2026-07-04 - feat(wecom): 支持员工助手订单经营金额问法
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令、探针名称和计划字段；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手订单能力新增“营业额、销售额、收入、流水、成交额、卖了多少钱”等经营金额关键词，金额类问法统一规划为订单 summary，复用现有 `summarize_orders()` 白名单参数化统计。共享探针新增 `today-revenue-summary` 与 `this-week-revenue-summary`，规划验收从 22 项扩展到 24 项，本地 24/24 通过；金额类语义规则同步拦截“未找到/暂无销售额/后台订单页”类兜底伪成功。用新探针打旧生产 `0.69.9` 时 `today-revenue-summary` 与 `this-week-revenue-summary` 按预期失败，旧版本分别误路由到观察台状态或返回无数据兜底。已同步生产 `0.69.10 / 5bed12a`，`/health`、`/ready` 和 24/24 回调探针通过，生产金额问法返回真实订单金额汇总。

## E-20260704-007：企微员工助手订单相对时间范围

- trace_id: 20260704-wecom-employee-agent-relative-date
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-relative-date
- file: `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_date.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_query.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_constants.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent_file_size.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`; `D:/Project/YunxiBakeBot/项目进度与配置清单.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_agent_file_size.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; pre-production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn` on production `0.69.8`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; `python -m ruff check app/service/wecom/employee_agent_order_constants.py app/service/wecom/employee_agent_order_date.py app/service/wecom/employee_agent_order_query.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/service/test_wecom_employee_agent_file_size.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/wecom/employee_agent_order_constants.py app/service/wecom/employee_agent_order_date.py app/service/wecom/employee_agent_order_query.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_employee_agent.py tests/service/test_wecom_employee_agent_file_size.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`
- result: pass
- related_logbook: 2026-07-04 - feat(wecom): 扩展员工助手订单相对时间范围
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令、探针名称和计划字段；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手订单计划新增最近/近 N 天、近一周/最近一周、本周/这周/本星期时间范围解析，并清理时间表达避免“3天”残留为商品关键词。共享探针新增 `recent-days-product-order-summary` 与 `this-week-top-products`，规划验收从 20 项扩展到 22 项，本地 22/22 通过；用新探针打旧生产 `0.69.8` 时 `this-week-top-products` 按预期失败，证明旧生产尚未支持本周范围。同步生产 `0.69.9 / 4bf0659` 后，`/health` ok，`/ready` ready，22/22 回调探针通过。

## E-20260704-006：企微员工助手商品库存问法匹配收紧

- trace_id: 20260704-wecom-employee-agent-product-keyword
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-product-keyword
- file: `D:/Project/YunxiBakeBot/app/service/wecom/intelligent_bot_product_filter.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_service.py`; `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_product_filter.py`; `D:/Project/YunxiBakeBot/tests/service/test_wecom_employee_agent.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`
- command: `python -m pytest tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_product_filter.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py -q --no-cov`; pre-production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; `python -m ruff check app/service/wecom/employee_agent_service.py app/service/wecom/intelligent_bot_product_filter.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_product_filter.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py`; `python -m ruff format --check app/service/wecom/employee_agent_service.py app/service/wecom/intelligent_bot_product_filter.py scripts/wecom_employee_agent_probe_cases.py tests/service/test_wecom_product_filter.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/scripts/test_check_wecom_employee_agent_plans.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 收紧员工助手商品库存问法匹配
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令、失败探针名称和语义规则；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 生产 `0.69.5` 在收紧后的探针下暴露 `order-product-inventory` 与 `casual-product-stock` 两个库存问法失败，原因是商品工具把员工口语整句作为商品查询，导致“伯牙绝弦”未稳定匹配。业务代码已改为清理商品问法噪声词，并在多工具计划中优先使用订单计划抽出的商品 keyword；生产 `0.69.6` 已恢复 20/20 回调通过，脚本语义增强用 `required_all_terms` 确认库存问法同时包含“库存”和真实库存数字。

## E-20260704-005：企微员工助手 20 项口语自由问法验收

- trace_id: 20260704-wecom-employee-agent-casual-probes
- generated_at: 2026-07-04
- evidence_type: local-and-production/wecom-employee-agent-casual-probes
- file: `D:/Project/YunxiBakeBot/scripts/wecom_employee_agent_probe_cases.py`; `D:/Project/YunxiBakeBot/scripts/check_wecom_employee_agent_plans.py`; `D:/Project/YunxiBakeBot/scripts/check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_capabilities.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_query.py`; `D:/Project/YunxiBakeBot/app/service/wecom/employee_agent_order_constants.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_plans.py`; `D:/Project/YunxiBakeBot/tests/scripts/test_check_wecom_employee_agent_callback.py`; `D:/Project/YunxiBakeBot/LOGBOOK.md`
- command: `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m pytest tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_agent.py tests/service/test_wecom_employee_agent_file_size.py -q --no-cov`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; `python -m ruff check app/service/wecom/employee_agent_capabilities.py app/service/wecom/employee_agent_order_constants.py app/service/wecom/employee_agent_order_query.py scripts/wecom_employee_agent_probe_cases.py scripts/check_wecom_employee_agent_plans.py scripts/check_wecom_employee_agent_callback.py scripts/wecom_employee_agent_callback_semantics.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/wecom/employee_agent_capabilities.py app/service/wecom/employee_agent_order_constants.py app/service/wecom/employee_agent_order_query.py scripts/wecom_employee_agent_probe_cases.py scripts/check_wecom_employee_agent_plans.py scripts/check_wecom_employee_agent_callback.py scripts/wecom_employee_agent_callback_semantics.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`
- result: pass
- related_logbook: 2026-07-04 - test(wecom): 扩展员工助手口语自由问法验收
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏命令、探针名称和语义验收结论；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 员工助手规划与端到端回调探针从 13 项扩展到 20 项，并将问法、计划期望、语义必需词和隐私禁止词收口到共享探针样本。新增覆盖“今天单量咋样”“发货还有没处理的吗”“哪些单子还没出物流”“今天卖爆的是哪个”“后台现在稳不稳”“有没有需要人接的”等口语表达。本地规划验收 20/20 通过；使用本地扩展脚本打生产回调入口 20/20 通过。待本轮提交同步后复验生产版本、健康检查和 20/20 回调探针。

## E-20260704-004：企微员工助手订单规划文件体量收口

- trace_id: 20260704-wecom-employee-agent-order-plan-split
- generated_at: 2026-07-04
- evidence_type: production/wecom-employee-agent-order-plan-refactor
- file: `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_order_plan.py`; `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_order_query.py`; `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_order_constants.py`; `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_llm_plan.py`; `D:\Project\YunxiBakeBot\tests\service\test_wecom_employee_agent_file_size.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/service/test_wecom_employee_agent_file_size.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; `python -m ruff check app/service/wecom/employee_agent_order_constants.py app/service/wecom/employee_agent_order_plan.py app/service/wecom/employee_agent_order_query.py app/service/wecom/employee_agent_llm_plan.py tests/service/test_wecom_employee_agent_file_size.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py`; `python -m ruff format --check app/service/wecom/employee_agent_order_constants.py app/service/wecom/employee_agent_order_plan.py app/service/wecom/employee_agent_order_query.py app/service/wecom/employee_agent_llm_plan.py tests/service/test_wecom_employee_agent_file_size.py tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `git rev-parse --short HEAD`; production `cat VERSION`; production `git diff --name-only | wc -l`; bundle cleanup checks
- result: pass
- related_logbook: 2026-07-04 - refactor(wecom): 拆分员工助手订单规划文件
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记文件体量、测试命令和脱敏探针结论；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: `employee_agent_order_plan.py` 从 253 行拆到 114 行；新增 `employee_agent_order_query.py` 120 行和 `employee_agent_order_constants.py` 51 行，职责分别为查询计划解析和常量口径。新增文件体量回归测试锁定三份订单规划文件不超过 150 行警戒线。员工助手规划探针 13/13 通过；生产已同步到 `0.69.4 / b539cd537`，`/health` ok，`/ready` ready，回调探针 13/13 通过，证明重构未改变员工入口行为；本地和生产临时 bundle 均已按明确路径清理。

## E-20260704-003：企微员工助手待人工工单尾号展示收口

- trace_id: 20260704-wecom-employee-agent-handoff-privacy
- generated_at: 2026-07-04
- evidence_type: production/wecom-employee-agent-handoff-privacy
- file: `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_ops_format.py`; `D:\Project\YunxiBakeBot\scripts\check_wecom_employee_agent_callback.py`; `D:\Project\YunxiBakeBot\tests\service\test_wecom_employee_privacy_format.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_wecom_employee_agent_callback.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`; production `/opt/yunxibakebot`
- command: pre-production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; `python -m pytest tests/service/test_wecom_employee_privacy_format.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_agent.py -q --no-cov`; `python -m ruff check app/service/wecom/intelligent_bot_ops_format.py scripts/check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check app/service/wecom/intelligent_bot_ops_format.py scripts/check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_privacy_format.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`; production `Invoke-RestMethod https://yunxifood.cn/health`; production `Invoke-RestMethod https://yunxifood.cn/ready`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `git rev-parse --short HEAD`; production `cat VERSION`; production `git diff --name-only | wc -l`; bundle cleanup checks
- result: pass
- related_logbook: 2026-07-04 - fix(wecom): 待人工列表隐藏完整工单 UUID
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏后的命令、失败项名称和展示规则；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址、完整订单号或完整内部 UUID。
- summary: 同步前生产 `0.69.0` 的 13 项回调验收按预期失败 1/13，失败项 `handoff-pending` 暴露完整内部 UUID；本轮改为待人工列表只展示 `工单尾号 <后5位>`，并把完整 UUID 加入回调探针隐私泄漏规则。生产已同步到 `0.69.3 / c833fb172`，`/health` ok，`/ready` ready，13 项回调验收 13/13 通过，`handoff-pending` 只返回工单尾号；本地和生产临时 bundle 均已按明确路径清理。

## E-20260704-002：企微员工助手 13 项回调生产语义验收

- trace_id: 20260704-wecom-employee-agent-ops-expansion
- generated_at: 2026-07-04
- evidence_type: production/wecom-employee-agent-ops-callback-acceptance
- file: `D:\Project\YunxiBakeBot\scripts\wecom_employee_agent_callback_semantics.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`; production `/opt/yunxibakebot`
- command: `python -m pytest tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_agent.py -q --no-cov`; `python -m ruff check scripts/wecom_employee_agent_callback_semantics.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `python -m ruff format --check scripts/wecom_employee_agent_callback_semantics.py tests/scripts/test_check_wecom_employee_agent_callback.py`; `Invoke-RestMethod https://yunxifood.cn/health`; `Invoke-RestMethod https://yunxifood.cn/ready`; `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`
- result: pass
- related_logbook: 2026-07-04 - test(wecom): 对齐员工助手 13 项回调语义规则
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录脱敏命令和语义验收结论；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址或完整订单号。
- summary: 生产 `0.67.3` 已通过员工助手 13 项端到端加密回调验收；语义规则允许正确的“观察台状态”和“活动批次不存在”口径，同时继续禁止群活动问法被带偏到库存、小程序商品、退款或后台订单工作流。

## E-20260704-001：企微员工助手运营类工具接入 Agent

- trace_id: 20260704-wecom-employee-agent-ops-expansion
- generated_at: 2026-07-04
- evidence_type: local/wecom-employee-agent-ops-expansion
- file: `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_capabilities.py`; `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_ops_plan.py`; `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_order_plan.py`; `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_service.py`; `D:\Project\YunxiBakeBot\scripts\check_wecom_employee_agent_plans.py`; `D:\Project\YunxiBakeBot\scripts\check_wecom_employee_agent_callback.py`; `D:\Project\YunxiBakeBot\scripts\wecom_employee_agent_callback_semantics.py`; `D:\Project\YunxiBakeBot\tests\service\test_wecom_employee_agent.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_wecom_employee_agent_plans.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_wecom_employee_agent_callback.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests/service/test_wecom_employee_agent.py tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_check_wecom_employee_agent_callback.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m ruff check ...`; `python -m ruff format --check ...`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; `python scripts/check_text_encoding.py`; pre-production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`
- result: pass
- related_logbook: 2026-07-04 - feat(wecom): 员工助手接入客户线索、群活动和离线复盘
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录脱敏测试命令、脚本结果和能力范围；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址或完整订单号。
- summary: 员工助手 API 模式自然语言入口新增复用既有只读 `customer_lookup`、`group_campaign_summary`、`offline_review_summary` 工具，规划探针扩展为 13/13。未同步生产前，端到端回调语义验收正确抓到旧生产 `group-campaign-summary` 和 `offline-review-summary` 语义带偏，作为同步后复验基线。

## E-20260703-008：企微员工助手语义回调生产复验

- trace_id: 20260703-wecom-employee-agent-semantic-acceptance
- generated_at: 2026-07-03
- evidence_type: production/wecom-employee-agent-semantic-callback-acceptance
- file: `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\项目进度与配置清单.md`; `D:\Project\YunxiBakeBot\scripts\check_wecom_employee_agent_callback.py`; production `/opt/yunxibakebot`
- command: `Test-Path "D:\Project\YunxiBakeBot\reports\wecom-employee-agent-semantic-466f4d4.bundle"`; production `test -f /opt/yunxibakebot/wecom-employee-agent-semantic-466f4d4.bundle`; production `systemctl is-active yunxibakebot`; production `git rev-parse --short HEAD`; production `cat VERSION`; production `git diff --name-only | wc -l`; `Invoke-RestMethod https://yunxifood.cn/health`; `Invoke-RestMethod https://yunxifood.cn/ready`; `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`
- result: pass
- related_logbook: 2026-07-03 - docs(wecom): 记录员工助手语义回调生产复验
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记生产版本、运行状态、临时包清理和脱敏回调验收结论；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址或完整订单号。
- summary: 生产已同步到 `0.67.2 / 466f4d43`，服务 active，`/health` ok，`/ready` ready，tracked dirty 为 `0`；本地和生产临时 bundle 均已按单文件路径清理。端到端员工助手回调语义验收 10/10 通过，`delivery-knowledge` 已返回配送规则兜底，不再被订单尾号排查话术污染。剩余事项是真实企微客户端或群内 10 个自由问法验收。

## E-20260703-007：企微员工助手知识问法语义验收

- trace_id: 20260703-wecom-employee-agent-semantic-acceptance
- generated_at: 2026-07-03
- evidence_type: local/wecom-employee-agent-semantic-acceptance
- file: `D:\Project\YunxiBakeBot\scripts\wecom_employee_agent_callback_semantics.py`; `D:\Project\YunxiBakeBot\scripts\check_wecom_employee_agent_callback.py`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_knowledge_format.py`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_tools.py`; `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_service.py`; `D:\Project\YunxiBakeBot\tests\service\test_wecom_intelligent_bot_knowledge_reply.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_agent.py tests/service/test_wecom_intelligent_bot_knowledge_reply.py tests/service/test_wecom_employee_privacy_format.py tests/scripts/test_check_wecom_employee_agent_plans.py -q --no-cov`; `python -m ruff check app/service/wecom/employee_agent_service.py app/service/wecom/intelligent_bot_tools.py app/service/wecom/intelligent_bot_knowledge_format.py scripts/check_wecom_employee_agent_callback.py scripts/wecom_employee_agent_callback_semantics.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_agent.py tests/service/test_wecom_intelligent_bot_knowledge_reply.py`; `python -m ruff format --check ...`; pre-production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`
- result: pass
- related_logbook: 2026-07-03 - fix(wecom): 收紧员工助手知识问法语义验收
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录语义验收规则、命令和脱敏结论；端到端报告不记录企微 Token、EncodingAESKey、密文、签名或客户隐私字段。
- summary: 端到端回调脚本新增 `semantic_safe`，把 10 个自由问法从“非空即可”升级为按问法检查必需/禁止语义词。未同步生产前脚本正确抓到 `delivery-knowledge` 被订单尾号话术污染；本地代码已改为知识类跳过 LLM 润色，并为配送类知识无命中提供规则类兜底。

## E-20260703-006：企微员工助手回调验收与隐私文案收紧

- trace_id: 20260703-wecom-employee-agent-callback-acceptance
- generated_at: 2026-07-03
- evidence_type: production/wecom-employee-agent-callback-acceptance
- file: `D:\Project\YunxiBakeBot\scripts\check_wecom_employee_agent_callback.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_check_wecom_employee_agent_callback.py`; `D:\Project\YunxiBakeBot\tests\service\test_wecom_employee_privacy_format.py`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_order_format.py`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_ops_format.py`; `D:\Project\YunxiBakeBot\app\service\wecom\employee_agent_service.py`; `D:\Project\YunxiBakeBot\docs\architecture\wecom-intelligent-bot-tools.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_agent.py tests/service/test_wecom_employee_privacy_format.py -q --no-cov`; `python -m pytest tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_wecom_intelligent_bot_smoke.py tests/scripts/test_check_wecom_intelligent_bot_contract.py tests/scripts/test_check_wecom_employee_agent_callback.py tests/service/test_wecom_employee_agent.py tests/service/test_wecom_employee_privacy_format.py tests/repository/test_youzan_repo.py -q --no-cov`; `python scripts/check_wecom_employee_agent_plans.py --json`; `python scripts/check_project.py --skip-tests`; `python scripts/check_mistake_ledger.py`; production `python scripts/check_wecom_employee_agent_callback.py --json --base-url https://yunxifood.cn`; production `/health`; production `/ready`; production `git diff --name-only | wc -l`
- result: pass
- related_logbook: 2026-07-03 - fix(wecom): 补齐员工助手回调验收与隐私文案
- related_adr: none
- contains_sensitive_data: no
- retention_note: 新增回调验收报告只记录问题名称、状态、回复预览和脱敏结论；不记录企微 Token、EncodingAESKey、密文、签名、手机号、完整地址或完整订单号。
- summary: 新增贴近真实企微 API 模式的员工助手端到端回调验收脚本，10 个自由问法会加密 POST 到 `/api/v1/wecom/intelligent-bot/callback` 并解密校验 `stream` 回复；本地测试锁定报告脱敏、隐私泄漏拦截、订单只用尾号和待人工不展示用户标识。首次生产探针发现“完整订单号”提示和买家 ID 展示风险，本轮已在格式层收紧并同步生产到 `0.67.1 / 0fe9fda`；生产回调验收 10/10 通过，tracked dirty 为 0。剩余事项是真实企微客户端群内验收。

## E-20260703-005：企微员工助手生产 git 工作区清理复核

- trace_id: 20260703-wecom-employee-agent-production-gate
- generated_at: 2026-07-03
- evidence_type: production/git-workspace-cleanup-verification
- file: `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\项目进度与配置清单.md`; production `/opt/yunxibakebot`
- command: production `git rev-parse --short HEAD`; production `git diff --name-only | wc -l`; production `git status --short | head -40`; `Invoke-RestMethod https://yunxifood.cn/health`; `Invoke-RestMethod https://yunxifood.cn/ready`; production `python3 scripts/check_wecom_employee_agent_plans.py --json`; production `python3 scripts/check_wecom_intelligent_bot_contract.py --json`
- result: pass
- related_logbook: 2026-07-03 - docs(wecom): 记录员工助手生产工作区清理证据
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录生产 HEAD、tracked dirty 数、未跟踪备份类别和脱敏验证结论；未记录 `.env`、企微密钥、请求头或客户隐私字段。
- summary: 生产已处于 `0.67.0 / 241ed517`，tracked dirty 数为 `0`；`git status --short` 仅剩历史 `.bak-wecom-*`、`.windsurf/workflows/sync-docs.md` 和 `backups/` 等未跟踪备份。复核后 `/health` ok、`/ready` ready，员工助手 10 个自由问法规划探针 10/10 通过，企微工具契约 4/4 通过。剩余事项仍是真实企微群内员工入口验收。

## E-20260703-004：企微员工助手 Agent 底座生产同步与规划验收

- trace_id: 20260703-wecom-employee-agent-production-gate
- generated_at: 2026-07-03
- evidence_type: production/wecom-employee-agent-foundation
- file: `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\docs\architecture\wecom-intelligent-bot-tools.md`; `D:\Project\YunxiBakeBot\scripts\check_wecom_employee_agent_plans.py`; production backup `/opt/yunxibakebot/backups/wecom-employee-agent-foundation-20260703-231225`
- command: `python scripts/check_wecom_employee_agent_plans.py --json`; `python -m pytest tests/scripts/test_check_wecom_employee_agent_plans.py tests/scripts/test_wecom_intelligent_bot_smoke.py tests/scripts/test_check_wecom_intelligent_bot_contract.py tests/service/test_wecom_employee_agent.py tests/repository/test_youzan_repo.py -q --no-cov`; `python scripts/check_project.py --skip-tests`; production `python3 scripts/check_wecom_employee_agent_plans.py --json`; production `python3 scripts/check_wecom_intelligent_bot_contract.py --json`; production `python3 scripts/wecom_intelligent_bot_smoke.py --json --base-url https://yunxifood.cn`; production `/health`; production `/ready`; production encrypted callback POST probe using runtime settings without printing secrets
- result: pass
- related_logbook: 2026-07-03 - feat(wecom): 固化员工助手自由问法规划验收
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录脱敏命令、备份目录和验证结论；未记录企微 Token、EncodingAESKey、插件 key、请求头或客户隐私字段。
- summary: 生产已同步员工助手 Agent 底座到 `0.67.0 / 20f690ec`，随后文档元数据同步到 `241ed517`。`/health` 为 ok，`/ready` 为 ready；企微工具 smoke 13/13 通过；自由问法规划探针 10/10 通过，并确认订单统计/待发货/缺物流/销量排行类计划不会带噪声 keyword；加密 callback POST 探针返回 200、签名校验通过、`msgtype=stream` 且内容非空。生产 git 工作区清理复核见 `E-20260703-005`；剩余事项是企微群内真实员工入口 10 个问法验收。

## E-20260703-002：企微智能机器人 API 模式 URL 回调本地验收

- trace_id: 20260703-wecom-aibot-url-callback
- generated_at: 2026-07-03
- evidence_type: local/wecom-intelligent-bot-url-callback
- file: `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\docs\architecture\wecom-intelligent-bot-tools.md`; `D:\Project\YunxiBakeBot\app\api\integrations\wecom_intelligent_bot.py`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_callback.py`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_dispatcher.py`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_messages.py`; `D:\Project\YunxiBakeBot\tests\api\test_wecom_intelligent_bot_callback_api.py`
- command: `python -m pytest tests/api/test_wecom_intelligent_bot_callback_api.py tests/api/test_wecom_intelligent_bot_plugin_api.py tests/service/test_wecom_intelligent_bot_tool_response_and_format.py tests/test_lifespan_routes_services.py tests/test_config.py tests/test_health_ready.py tests/scripts/test_preflight_production.py tests/scripts/test_smoke_test.py -q --no-cov`; `python -m ruff check app\api\integrations\wecom_intelligent_bot.py app\service\wecom\crypto.py app\service\wecom\intelligent_bot_callback.py app\service\wecom\intelligent_bot_dispatcher.py app\service\wecom\intelligent_bot_messages.py app\config.py app\readiness.py app\lifespan_routes.py app\lifespan_services.py scripts\preflight_production.py scripts\smoke_test.py tests\api\test_wecom_intelligent_bot_callback_api.py tests\api\test_wecom_intelligent_bot_plugin_api.py tests\test_lifespan_routes_services.py tests\test_health_ready.py`; `python scripts\check_project.py --skip-tests`; `python scripts\check_mistake_ledger.py`; `rg "from app\.repository" app\api -g "*.py"`; `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app\service -g "*.py"`; `rg "from app\.(service|repository|api)" app\models -g "*.py"`
- result: pass
- related_logbook: 2026-07-03 - feat(wecom): 切换智能机器人为 API 模式 URL 回调
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录本地验证命令和文件路径；未记录企微 Token、EncodingAESKey、插件 key 或客户隐私字段。
- summary: 本地已完成智能机器人 API 模式 URL 回调 GET 验证、POST 加密 JSON 消息解密与加密被动回复测试；普通模式工具路由仍通过。长连接草稿文件已移除，主入口固定为 `/api/v1/wecom/intelligent-bot/callback`。

## E-20260703-003：企微智能机器人 API 模式 URL 回调生产同步

- trace_id: 20260703-wecom-aibot-url-callback
- generated_at: 2026-07-03
- evidence_type: production/wecom-intelligent-bot-url-callback
- file: `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\docs\architecture\wecom-intelligent-bot-tools.md`; production backup `/opt/yunxibakebot/backups/wecom-aibot-url-callback-20260703-154519`
- command: `ssh root@47.94.102.250 "cd /opt/yunxibakebot && python3 -m compileall -q ..."`; `ssh root@47.94.102.250 "systemctl restart yunxibakebot && systemctl is-active yunxibakebot"`; `curl https://yunxifood.cn/health`; `curl https://yunxifood.cn/ready`; production encrypted GET/POST callback probe using runtime settings without printing secrets; `ssh root@47.94.102.250 "cd /opt/yunxibakebot && python3 scripts/wecom_intelligent_bot_smoke.py --json --base-url https://yunxifood.cn"`
- result: pass
- related_logbook: 2026-07-03 - feat(wecom): 切换智能机器人为 API 模式 URL 回调
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录脱敏命令、备份目录和验证结论；未记录企微 Token、EncodingAESKey、插件 key 或客户隐私字段。
- summary: 生产已同步智能机器人 API 模式 URL 回调入口 `/api/v1/wecom/intelligent-bot/callback`。首次重启因漏同步 `intelligent_bot_status_tools.py` 出现短暂 502，补同步后 `/health` 与 `/ready` 均恢复 200；生产加密 GET/POST 探针通过，普通模式工具 smoke 13/13 通过。

## E-20260703-001：企微智能机器人工具输出适配与商品匹配修复

- trace_id: 20260703-wecom-tool-result-not-visible
- generated_at: 2026-07-03
- evidence_type: production/wecom-intelligent-bot-result-adapter
- file: `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\docs\architecture\wecom-intelligent-bot-tools.md`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_plugin.py`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_tool_response.py`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_tool_format.py`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_product_filter.py`; `D:\Project\YunxiBakeBot\tests\service\test_wecom_intelligent_bot_tool_response_and_format.py`
- command: `python -m pytest tests/service/test_wecom_intelligent_bot_tool_response_and_format.py tests/api/test_wecom_intelligent_bot_plugin_api.py tests/scripts/test_wecom_intelligent_bot_smoke.py tests/scripts/test_check_wecom_intelligent_bot_contract.py -q --no-cov`; `python -m ruff check app/service/wecom/intelligent_bot_plugin.py app/service/wecom/intelligent_bot_tool_response.py app/service/wecom/intelligent_bot_tool_format.py app/service/wecom/intelligent_bot_product_filter.py scripts/check_wecom_intelligent_bot_contract.py tests/service/test_wecom_intelligent_bot_tool_response_and_format.py tests/api/test_wecom_intelligent_bot_plugin_api.py tests/scripts/test_check_wecom_intelligent_bot_contract.py`; `python scripts/check_project.py --skip-tests`; production `python3 scripts/check_wecom_intelligent_bot_contract.py`; production `python scripts/wecom_intelligent_bot_smoke.py --json --base-url https://yunxifood.cn`; production read-only probes for `ping` / `product-lookup` / `knowledge-answer`; production enhanced smoke with `result_present` contract
- result: pass
- related_logbook: 2026-07-03 - fix(wecom): 统一智能机器人工具输出并收紧商品匹配
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录脱敏命令、路径、备份目录和验证结论；未记录 `WECOM_BOT_PLUGIN_API_KEY`、`X-Yunxi-Bot-Key`、`Authorization` 或完整客户隐私字段。
- summary: 生产已同步统一 `result` / `resultText` 输出字段，企微后台可统一配置一个 String 输出参数；`product-lookup` 对具体商品无匹配时不再返回无关 fallback 商品。生产备份目录为 `/opt/yunxibakebot/backups/wecom-bot-result-adapter-20260703-125246`，增强 smoke 脚本备份目录为 `/opt/yunxibakebot/backups/wecom-smoke-result-contract-20260703-132901`；重启后服务 active，契约检查与完整 smoke 通过，10 个业务/连通工具均 `result_present=true`。

## E-20260702-001：企微智能机器人工具生产级验收

- trace_id: 20260702-wecom-bot-production-hardening
- generated_at: 2026-07-02
- evidence_type: production/wecom-intelligent-bot-acceptance
- file: `D:\Project\YunxiBakeBot\reports\harness\wecom-intelligent-bot-acceptance-20260703-011421.md`; `D:\Project\YunxiBakeBot\reports\wecom-intelligent-bot-contract-20260703-011421.json`; `D:\Project\YunxiBakeBot\reports\wecom-intelligent-bot-smoke-20260703-011240.json`; `D:\Project\YunxiBakeBot\docs\architecture\wecom-intelligent-bot-tools.md`
- command: `python scripts/check_wecom_intelligent_bot_contract.py --json --output "reports/wecom-intelligent-bot-contract-{timestamp}.json"`; `python scripts/wecom_intelligent_bot_smoke.py --json --base-url https://yunxifood.cn --output "reports/wecom-intelligent-bot-smoke-{timestamp}.json"`; production `python3 scripts/check_wecom_intelligent_bot_contract.py --json`; production `python3 scripts/wecom_intelligent_bot_smoke.py --json --base-url https://yunxifood.cn`; `/health`; `/ready`
- result: pass
- related_logbook: 2026-07-02 - harden(wecom): 完成企微智能机器人工具生产级验收
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记脱敏 JSON、命令和结论；报告不包含 `WECOM_BOT_PLUGIN_API_KEY`、`X-Yunxi-Bot-Key`、`Authorization` 或完整客户隐私字段。
- summary: 企微智能机器人 `ping` + 9 个只读业务工具已在生产域名完成冒烟，错误 key、缺 key 和 URL query key 均被拒绝；文档工具清单与 FastAPI 路由一致；`/ready` 已纳入插件 key 配置检查并返回 ready。


## E-20260623-003：并发压测按需 CI 编排

- trace_id: 20260623-load-test-ci-workflow
- generated_at: 2026-06-23
- evidence_type: ci/load-test-workflow
- file: `D:\Project\YunxiBakeBot\.github\workflows\load-test.yml`; `D:\Project\YunxiBakeBot\scripts\test_concurrent_100.py`; `D:\Project\YunxiBakeBot\scripts\prepare_load_test_fixture.py`; `D:\Project\YunxiBakeBot\项目进度与配置清单.md`
- command: `python -m compileall scripts\test_concurrent_100.py scripts\prepare_load_test_fixture.py`; `python scripts\test_concurrent_100.py --help`; `python scripts\prepare_load_test_fixture.py --help`; `python scripts\prepare_load_test_fixture.py --db-path data\load-test-fixture-check.db --orders 2 --products 2`; `python -m ruff check scripts\test_concurrent_100.py scripts\prepare_load_test_fixture.py`; `Select-String -Path .github\workflows\load-test.yml -Pattern "workflow_dispatch|phase_a_count|upload-artifact|test_concurrent_100.py"`
- result: pass
- related_logbook: 2026-06-23 - ci(load-test): 将并发压测纳入按需触发 CI
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记 workflow、脚本路径和本地静态验证命令；GitHub Actions 运行产物由 `load-test-evidence` artifact 保存 14 天
- summary: 新增独立 `Load Test` workflow，通过 `workflow_dispatch` 按需触发并发压测，准备隔离测试库、启动 FastAPI、运行 `scripts/test_concurrent_100.py` 并上传 `reports/load-test/`。压测脚本已支持并发路数和沉降等待时间参数化，有赞 Mock 模式下可复用 CI fixture；完整 LLM 对话循环仍要求仓库配置 `MIMO_API_KEY` secret。

## E-20260623-002：1 对 1 AI 自动回复生产验收

- trace_id: 20260623-wecom-1on1-production-acceptance
- generated_at: 2026-06-23
- evidence_type: production/1on1-acceptance
- file: `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBot\app\api\integrations\wecom.py`; `D:\Project\YunxiBakeBot\app\service\wecom\message_queue.py`; `D:\Project\YunxiBakeBot\app\models\session.py`
- command: `ssh root@47.94.102.250 "cd /opt/yunxibakebot && git rev-parse --short HEAD && systemctl is-active yunxibakebot"`; `ssh root@47.94.102.250 "journalctl -u yunxibakebot -n 200 --no-pager | grep -E 'wecom_1on1|企微|智能助手|已接入智能助手|handle_message|callback'"`; `ssh root@47.94.102.250 "journalctl -u yunxibakebot --since '2026-06-23 09:52:30' --until '2026-06-23 09:54:30' --no-pager | grep -F 'wmLgrYDAAArcuj-n_J5QqH2CThPYismA'"`; `ssh root@47.94.102.250 "journalctl -u yunxibakebot --since '2026-06-23 09:52:30' --until '2026-06-23 09:54:30' --no-pager | grep -E 'wecom_1on1|send_text|send_news|handle_message|智能助手|已接入智能助手|回复失败'"`
- result: pass
- related_logbook: 2026-06-23 - feat(wecom-1on1): 完成 1 对 1 AI 自动回复生产验收与留痕
- related_adr: none
- contains_sensitive_data: yes
- retention_note: 仅保留生产验收命令、结论和本地文件路径；测试用户 ID 与消息内容不进入索引正文
- summary: 生产机当前版本活跃，服务在线；真实 1 对 1 对话已触发自动回复链路，日志显示会话切换为智能助手并成功发送客服文本消息，满足 1 对 1 AI 自动回复的生产验收最小闭环。

## E-20260623-001：企微回调生产联调验证

- trace_id: 20260623-wecom-callback-production-joint-test
- generated_at: 2026-06-23
- evidence_type: production/callback-joint-test
- file: `D:\Project\YunxiBakeBot\LOGBOOK.md`; `D:\Project\YunxiBakeBotpppi\integrations\wecom.py`; `D:\Project\YunxiBakeBotpp\service\wecom\crypto.py`; `D:\Project\YunxiBakeBot\scripts\setup_wecom.sh`; `D:\Project\YunxiBakeBot\scripts\preflight_production.py`; `D:\Project\YunxiBakeBot\scripts\smoke_test.py`; `D:\Project\YunxiBakeBotppeadiness.py`
- command: `ssh root@47.94.102.250 "cd /opt/yunxibakebot && git rev-parse --short HEAD && systemctl is-active yunxibakebot"`; `ssh root@47.94.102.250 "cd /opt/yunxibakebot && grep -n '^WECOM_' .env | sed 's/=.*$/=<redacted>/'"`; `ssh root@47.94.102.250 "curl -s -o /dev/null -w '%{http_code} %{url_effective}\n' https://yunxifood.cn/health"`; `ssh root@47.94.102.250 "cd /opt/yunxibakebot && python3 -"`
- result: pass
- related_logbook: 2026-06-23 - feat(wecom): 完成企微回调生产联调与留痕
- related_adr: none
- contains_sensitive_data: yes
- retention_note: 仅保留联调命令、结果与文件路径；回调 token、AES key、corp id 等敏感值不写入索引正文
- summary: 生产机当前版本活跃、服务在线，`.env` 已具备企微回调必需配置；使用生产配置对 `https://yunxifood.cn/api/v1/wecom/callback` 进行真实 GET 验签和 POST 解密联调，GET 返回明文回显，POST 返回 200 空响应，说明企微回调生产联调已闭环。
# Evidence Index

本文件是 Harness 证据包索引。它不保存敏感报告内容，只记录证据文件的位置、用途、生成命令和验证结论，方便上线前后审计、复盘和交接。

______________________________________________________________________

## 证据目录

| 目录 | 用途 |
|---|---|
| `reports/harness/` | Harness 快照、交接、汇总索引 |
| `reports/preflight-*.json` | 生产同步前后预检报告 |
| `reports/smoke-*.json` | 冒烟测试报告 |
| `reports/migration-*.json` | 数据库迁移 dry-run / apply 报告 |
| `reports/baseline-seed-*.json` | 基础知识种子 dry-run / apply 报告 |
| `reports/rebuild-embeddings-*.json` | 向量重建 dry-run / apply 报告 |

______________________________________________________________________

## E-20260622-001：项目管理手册体系收口

- trace_id: 20260622-management-handbook-closure
- generated_at: 2026-06-22
- evidence_type: doc-sweep/harness
- file: `D:\Project\YunxiBakeBot\AGENTS.md`; `D:\Project\YunxiBakeBot\docs\AGENTS\commit-workflow.md`; `D:\Project\YunxiBakeBot\docs\AGENTS\quick-reference.md`; `D:\Project\YunxiBakeBot\docs\AGENTS\skill-reference.md`; `D:\Project\YunxiBakeBot\docs\harness-engineering\README.md`; `D:\Project\YunxiBakeBot\docs\harness-engineering\core\traceability-model.md`; `D:\Project\YunxiBakeBot\docs\harness-engineering\core\verification-matrix.md`; `D:\Project\YunxiBakeBot\docs\harness-engineering\core\agent-handoff-template.md`; `D:\Project\YunxiBakeBot\docs\harness-engineering\core\mistake-ledger.md`; `D:\Project\YunxiBakeBot\docs\harness-engineering\core\evidence-index.md`; `D:\Project\YunxiBakeBot\.windsurf\workflows\check.md`; `D:\Project\YunxiBakeBot\.windsurf\workflows\commit.md`; `D:\Project\YunxiBakeBot\.windsurf\workflows\design.md`; `D:\Project\YunxiBakeBot\.windsurf\workflows\review.md`; `D:\Project\YunxiBakeBot\.windsurf\workflows\sync-skills.md`; `D:\Project\YunxiBakeBot\.windsurf\workflows\update-knowledge.md`; `D:\Project\YunxiBakeBot\.agents\SKILL_AUDIT.md`
- command: `rg -n "YunxiBakeMiniApp|python -m pytest tests/ -q|systemctl restart yunxibakebot && systemctl is-active yunxibakebot|SKIP_LOGBOOK_CHECK|check_logbook|append_logbook|harness_snapshot|check_mistake_ledger|trace_id|evidence-index|agent-handoff-template|verification-matrix" AGENTS.md docs .windsurf .agents scripts -g "*.md" -g "*.py"`
- result: pass
- related_logbook: 2026-06-22 - docs(management): 完善项目管理体系与手册收口
- related_adr: 0001-traceable-memory-harness, 0002-platform-storefront-boundaries-and-instance-naming
- contains_sensitive_data: no
- retention_note: 仅登记管理手册收口的文件与命中结果，不复制任何业务数据或生产凭据
- summary: 项目管理主入口、提交/验证/交接/证据/防重犯流程、Skill 索引和 Harness 入口已对齐当前真实使用方式；旧的固定全量测试与强制重启语气已收缩为按验证矩阵和变更类型执行。

______________________________________________________________________

## E-20260621-005：后台静态入口 dist 路径修复

- trace_id: 20260621-admin-dist-path-after-api-move
- generated_at: 2026-06-21
- evidence_type: bugfix/regression/release
- file: `D:\Project\YunxiBakeBot\app\api\admin\frontend.py`; `D:\Project\YunxiBakeBot\tests\api\test_admin_frontend.py`; `D:\Project\YunxiBakeMiniApp\reports\domain-check\domain-check-20260621-013703.json`; `D:\Project\YunxiBakeMiniApp\reports\production-admin-check\production-admin-20260621-013702.json`
- command: Bot `python -m pytest tests\api\test_admin_frontend.py -q --tb=short --no-cov`; Bot `python -m compileall app\api\admin\frontend.py tests\api\test_admin_frontend.py`; Bot `python scripts\check_project.py --skip-tests`; Admin `npm run build:production`; production `systemctl restart yunxibakebot`; MiniApp `npm run check:production-domain`; MiniApp `npm run check:production-admin`; MiniApp `npm run check:production-miniapp-api`; MiniApp `npm run release:readiness`
- result: pass
- related_logbook: 2026-06-21 - fix(admin): 修复后台静态入口 dist 路径
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记路径修复和生产失败报告路径，不复制后台 HTML 或认证信息
- summary: 生产 `web/admin/dist/index.html` 已存在但 `/admin/` 仍返回未构建，根因为 API 目录迁移后 `frontend.py` 的项目根计算少退一层；已修正并补路径回归测试。生产已部署到 `1e40063 / 0.62.4`，域名、后台、MiniApp API 与 release readiness 均通过，最终 readiness 报告为 `D:\Project\YunxiBakeMiniApp\reports\release-readiness\readiness-20260621-094445.json`。

## E-20260621-004：生产后台构建入口修复

- trace_id: 20260621-admin-production-build-recovery
- generated_at: 2026-06-21
- evidence_type: bugfix/build/release
- file: `D:\Project\YunxiBakeBot\web\admin\src\services\assets.ts`; `D:\Project\YunxiBakeMiniApp\reports\domain-check\domain-check-20260621-012858.json`; `D:\Project\YunxiBakeMiniApp\reports\production-admin-check\production-admin-20260621-012902.json`; `D:\Project\YunxiBakeMiniApp\reports\release-readiness\readiness-20260621-093002.json`
- command: `ssh root@47.94.102.250 "systemctl restart yunxibakebot ..."`；MiniApp `npm run check:production-miniapp-api`; MiniApp `npm run release:readiness`; Admin `npm run build:production`; Admin `npm run check:decoration`; Admin `npm run check:products`; Admin `npm run check:shop-settings`
- result: partial-pass
- related_logbook: 2026-06-21 - fix(admin): 修复生产后台构建入口
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记生产检查报告路径和构建命令，不复制后台页面内容或认证信息
- summary: catalog 修复部署后生产商品 API 已通过；release readiness 剩余失败来自生产后台 `dist` 缺失。后台本机构建失败根因为 `assets.ts` 错用命名导入，已修复并通过 production build，待同步 `dist` 到生产后复测。

## E-20260621-003：小程序商品泛化分类兜底修复

- trace_id: 20260621-catalog-generic-category-guard
- generated_at: 2026-06-21
- evidence_type: bugfix/regression/release
- file: `D:\Project\YunxiBakeBot\app\service\catalog\serialization.py`; `D:\Project\YunxiBakeBot\tests\service\test_catalog.py`; `D:\Project\YunxiBakeBot\tests\api\test_miniapp_catalog_api.py`; `D:\Project\YunxiBakeMiniApp\reports\production-api-check\production-miniapp-api-20260621-012007.json`; `D:\Project\YunxiBakeMiniApp\reports\release-readiness\readiness-20260621-092107.json`
- command: Bot `python -m pytest tests\service\test_catalog.py tests\api\test_miniapp_catalog_api.py -q --tb=short --no-cov`; Bot `python -m compileall app\service\catalog tests\service\test_catalog.py tests\api\test_miniapp_catalog_api.py`; Bot `python scripts\check_project.py --skip-tests`; Bot `python scripts\check_file_sizes.py`; Bot `python scripts\check_mistake_ledger.py`; Bot `python -m ruff check app\service\catalog\serialization.py tests\service\test_catalog.py tests\api\test_miniapp_catalog_api.py`; MiniApp `npm run check:production-miniapp-api`; MiniApp `npm run release:readiness`
- result: partial-pass
- related_logbook: 2026-06-21 - fix(catalog): 阻止泛化标签穿透小程序商品分类
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记本地验证命令、生产门禁报告路径和失败摘要；不复制生产商品响应明细
- summary: Bot 本地 catalog service/API 回归、编译、红线、体量和 ruff 均通过；MiniApp 生产门禁仍为 21/22，因为生产环境尚未部署本轮后端分类兜底修复。

## E-20260621-002：P4 后双仓联动预检与残留口径收口

- trace_id: 20260621-post-p4-release-sweep
- generated_at: 2026-06-21
- evidence_type: release/doc-sweep/regression
- file: `D:\Project\YunxiBakeBot\docs\AGENTS\quick-reference.md`; `D:\Project\YunxiBakeBot\scripts\check_file_sizes.py`; `D:\Project\YunxiBakeMiniApp\scripts\release-readiness.mjs`; `D:\Project\YunxiBakeMiniApp\scripts\check-secret-hygiene.mjs`; `D:\Project\YunxiBakeMiniApp\reports\release-readiness\readiness-20260621-090556.json`
- command: `python scripts\preflight_production.py`; `python scripts\smoke_test.py`; MiniAPP `npm run check:secrets`; MiniAPP `npm run release:readiness`; Bot `python scripts\check_file_sizes.py`; Bot `python scripts\check_project.py --skip-tests`
- result: partial-pass
- related_logbook: 2026-06-21 - chore(release): 完成 P4 后双仓联动预检与残留口径收口
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记命令、报告路径和失败摘要；生产 API 响应片段不写入本索引
- summary: 双仓代码联动面正常，MiniApp release readiness 已修复到 21/22；唯一剩余失败为生产商品列表中 4 个商品仍返回 `categoryId/categoryName = "商品"`。Bot 本地 preflight/smoke 失败来自本地生产数据/配置缺口和服务未启动，不属于 API 目录收口回归。

## E-20260621-001：后端 API 目录统一收口

- trace_id: 20260621-api-directory-unification
- generated_at: 2026-06-21
- evidence_type: refactor/regression
- file: `D:\Project\YunxiBakeBot\app\api\admin\`; `D:\Project\YunxiBakeBot\app\api\channels\`; `D:\Project\YunxiBakeBot\app\api\integrations\`; `D:\Project\YunxiBakeBot\app\api\integrations\youzan_audit.py`; `D:\Project\YunxiBakeBot\scripts\check_project.py`; `D:\Project\YunxiBakeBot\tests\test_red_line_rules.py`
- command: `python -m compileall app\api app\lifespan_routes.py`; `python -m pytest tests\test_red_line_rules.py tests\test_lifespan_routes_services.py tests\api tests\service\youzan\test_webhook_retry.py -q --tb=short --no-cov`; `python scripts\check_project.py`
- result: pass
- related_logbook: 2026-06-21 - refactor(api): 统一后端 API 目录结构
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录目录收口、红线自测和 API 回归命令，不含业务数据
- summary: 后端主仓 API 真实实现已统一收口到 admin、channels/storefront、integrations；根目录历史 API 文件仅保留兼容入口，外部 HTTP 路径保持不变。

## E-20260617-046：生产后台浏览器只读导航 smoke

- trace_id: 20260617-production-admin-browser-smoke
- generated_at: 2026-06-17
- evidence_type: screenshot/command/release
- file: `D:\Project\YunxiBakeBot\reports\ui\production-admin-browser-smoke.png`; `D:\Project\YunxiBakeBot\reports\ui\production-admin-browser-smoke.json`; `D:\Project\YunxiBakeMiniApp\reports\release-readiness\readiness-20260617-131610.json`
- command: `npm run smoke:production-navigation` in `YunxiBakeBot\web\admin`; `npm run check:production-admin-browser`; `npm run release:readiness`
- result: pass
- related_logbook: 2026-06-17 - test(production): 生产后台浏览器只读导航 smoke
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留生产后台浏览器截图和 JSON 报告；token 仅通过环境变量临时注入，不写入报告
- summary: 生产后台登录后只读访问概览、装修、订单、地址、商品、转人工、店铺配置 7 个页面均渲染成功；小程序 release readiness 升级为 21/21 通过。

## E-20260620-002：有赞客户迁移交接与回滚 runbook

- trace_id: 20260620-customer-import-handoff
- generated_at: 2026-06-20
- evidence_type: handoff/runbook
- file: `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-import-handoff-and-rollback-runbook.md`; `D:\Project\YunxiBakeBot\docs\README.md`
- command: `Test-Path docs/architecture/youzan-customer-import-handoff-and-rollback-runbook.md`; `Select-String -Path docs/README.md -Pattern "youzan-customer-import-handoff-and-rollback-runbook"`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 统一客户迁移闭环为四段口径
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留 runbook 文档作为迁移后异常处理和证据留档入口
- summary: 客户迁移交接与回滚 runbook 已纳入文档入口索引。

## E-20260620-008：客户迁移四段闭环残留表述收口

- trace_id: 20260620-customer-doc-closure-residuals
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1.md`; `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1-schema-draft.md`; `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-migration-audit-checklist.md`; `D:\Project\YunxiBakeBot\docs\architecture\platform-miniapp-api-contract-v1.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `rg -n "下一步建议|后续建议|进入下一步 schema 或脚本设计" docs/architecture`; `Get-Content -LiteralPath "D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1.md" -Encoding UTF8 | Select-Object -Skip 468 -First 30`; `Get-Content -LiteralPath "D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1-schema-draft.md" -Encoding UTF8 | Select-Object -Skip 548 -First 20`; `Get-Content -LiteralPath "D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-migration-audit-checklist.md" -Encoding UTF8 | Select-Object -Skip 438 -First 25`; `Get-Content -LiteralPath "D:\Project\YunxiBakeBot\docs\architecture\platform-miniapp-api-contract-v1.md" -Encoding UTF8 | Select-Object -Skip 428 -First 15`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 收口客户迁移四段闭环残留表述
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留文档收口命令与结果，不含业务数据
- summary: 四份客户迁移相关文档的结尾口径已收口为当前入口，不再保留未来态“下一步”措辞。

## E-20260620-033：产品角色名与仓库路径名澄清

- trace_id: 20260620-name-clarification-role-vs-slug
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\README.md`; `D:\Project\YunxiBakeBot\docs\architecture\project-boundaries.md`; `D:\Project\YunxiBakeBot\docs\README.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `rg -n "仓库名|仓库 slug|历史过渡材料|命名约束|Storefront MiniApp" README.md docs/architecture/project-boundaries.md docs/README.md`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 澄清产品角色名与仓库路径名
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录命名澄清的文档命中结果，不含业务数据
- summary: 产品角色名、渠道角色名和仓库路径名的口径已重新压实，历史仓名只保留在路径和过渡引用里。

## E-20260620-010：MiniApp 过渡文档历史化

- trace_id: 20260620-miniapp-history-only
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\docs\architecture\miniapp-ai-handoff-plan.md`; `D:\Project\YunxiBakeBot\docs\architecture\miniapp-phase1-execution-checklist.md`
- command: `rg -n "历史过渡记录|历史任务边界|历史执行原则|历史推荐执行顺序|历史验收标准" docs/architecture/miniapp-ai-handoff-plan.md docs/architecture/miniapp-phase1-execution-checklist.md`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 降级 MiniApp 过渡文档为历史记录
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录历史化命中结果，不含业务数据
- summary: 两份 MiniApp 过渡文档已经降级为历史记录，不再作为当前实施蓝图。

## E-20260620-011：MiniApp 过渡文档行动语气再压缩

- trace_id: 20260620-miniapp-history-only
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\docs\architecture\miniapp-ai-handoff-plan.md`; `D:\Project\YunxiBakeBot\docs\architecture\miniapp-phase1-execution-checklist.md`
- command: `rg -n "摘录|历史过渡记录|历史示例要求摘录|历史验收标准摘录|当前实施蓝图" docs/architecture/miniapp-ai-handoff-plan.md docs/architecture/miniapp-phase1-execution-checklist.md`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 继续历史化 MiniApp 过渡文档的行动语气
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录过渡文档再压缩的命中结果，不含业务数据
- summary: 两份 MiniApp 过渡文档的章节标题已进一步压成“摘录”口径，历史索引味道更强。

## E-20260620-012：双仓路线图历史化

- trace_id: 20260620-two-repo-rollout-history
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\docs\architecture\two-repo-rollout-plan.md`
- command: `rg -n "历史摘录|历史目标|历史结论先行|历史三个阶段|当时原则|当时不要求|为什么当时不是先改 MiniApp|历史验收标准" docs/architecture/two-repo-rollout-plan.md`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 历史化双仓路线图
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录双仓路线图历史化命中结果，不含业务数据
- summary: 双仓路线图已压成历史摘录口径，不再像当前实施蓝图。

## E-20260620-013：双仓路线图历史行动语气再压缩

- trace_id: 20260620-two-repo-rollout-history
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\docs\architecture\two-repo-rollout-plan.md`
- command: `rg -n "历史摘录|历史目标|历史结论先行|历史三个阶段|当时原则|当时不要求|为什么当时不是先改 MiniApp|历史验收标准" docs/architecture/two-repo-rollout-plan.md`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 压缩双仓路线图的历史行动语气
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录双仓路线图再压缩命中结果，不含业务数据
- summary: 双仓路线图的历史行动语气已进一步压缩，读起来更像只读历史索引。

## E-20260620-014：docs 导航历史分层

- trace_id: 20260620-docs-history-layering
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\docs\README.md`
- command: `rg -n "当前设计与过渡方案|历史方案|只用于回顾过渡思路|只保留历史过渡记录|只作为历史参考" docs/README.md`
- result: pass
- related_logbook: 2026-06-20 - docs(readme): 历史化 docs 导航分层
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录 docs 导航历史分层命中结果，不含业务数据
- summary: docs 导航中历史材料已放入“历史方案”层，和当前权威口径分开。

## E-20260620-015：双仓路线图进入历史方案区

- trace_id: 20260620-docs-history-layering
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\docs\README.md`
- command: `rg -n "two-repo-rollout-plan.md|当前权威口径|历史方案" docs/README.md`
- result: pass
- related_logbook: 2026-06-20 - docs(readme): 将双仓路线图移入历史方案区
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录导航分层命中结果，不含业务数据
- summary: 双仓路线图已经从当前权威口径移入历史方案区，导航层不会再把它当当前实施依据。

## E-20260620-016：历史方案区路线图去重

- trace_id: 20260620-docs-history-dedup
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\docs\README.md`
- command: `rg -n "two-repo-rollout-plan.md" docs/README.md`
- result: pass
- related_logbook: 2026-06-20 - docs(readme): 去重历史方案区的路线图条目
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录历史方案区去重命中结果，不含业务数据
- summary: 历史方案区中的双仓路线图引用已去重，只保留一处。

## E-20260620-017：总入口历史材料分流

- trace_id: 20260620-entrypoints-history-redirect
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\README.md`; `D:\Project\YunxiBakeBot\docs\architecture\project-boundaries.md`
- command: `rg -n "历史方案区|历史过渡材料|当前实施蓝图|two-repo-rollout-plan|miniapp-phase1-execution-checklist|miniapp-ai-handoff-plan" README.md docs/architecture/project-boundaries.md`
- result: pass
- related_logbook: 2026-06-20 - docs(readme): 总入口改为历史方案区分流
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录总入口分流命中结果，不含业务数据
- summary: README 与边界文档已不再直接把读者送到历史路线图，历史材料统一从 docs 导航进入。

## E-20260620-018：当前权威入口与历史材料边界压紧

- trace_id: 20260620-entrypoints-current-authority-tightening
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\docs\README.md`; `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1.md`; `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1-schema-draft.md`; `D:\Project\YunxiBakeBot\docs\architecture\platform-miniapp-api-contract-v1.md`
- command: `rg -n "执行起点|四段闭环|历史方案|历史过渡|旧执行清单" docs/README.md docs/architecture/customer-master-v1.md docs/architecture/customer-master-v1-schema-draft.md docs/architecture/platform-miniapp-api-contract-v1.md`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 压紧当前入口与历史材料边界
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录入口边界收口命中结果，不含业务数据
- summary: 当前权威入口文档已统一强调执行起点与四段闭环，历史方案与背景材料只作为参考入口。

## E-20260620-019：逻辑总项目与双仓边界命名 ADR

- trace_id: 20260620-platform-storefront-boundaries-and-naming
- generated_at: 2026-06-20
- evidence_type: adr
- file: `D:\Project\YunxiBakeBot\docs\harness-engineering\adr\0002-platform-storefront-boundaries-and-instance-naming.md`; `D:\Project\YunxiBakeBot\docs\architecture\project-boundaries.md`; `D:\Project\YunxiBakeBot\docs\README.md`
- command: `Test-Path docs/harness-engineering/adr/0002-platform-storefront-boundaries-and-instance-naming.md`; `rg -n "ADR 0002|逻辑总项目|双仓边界|Yunxi 降级为实例名" docs/harness-engineering/adr/0002-platform-storefront-boundaries-and-instance-naming.md docs/architecture/project-boundaries.md docs/README.md`
- result: pass
- related_logbook: 2026-06-20 - adr(architecture): 固化逻辑总项目与双仓边界命名决策
- related_adr: 0002-platform-storefront-boundaries-and-instance-naming
- contains_sensitive_data: no
- retention_note: 仅记录 ADR 建立与入口挂载结果，不含业务数据
- summary: 双仓边界、逻辑总项目命名和 `Yunxi` 实例名定位已升级为长期决策记录，并挂到当前边界入口。

## E-20260620-020：可见脚本与部署展示名收口

- trace_id: 20260620-visible-naming-platform-surface
- generated_at: 2026-06-20
- evidence_type: doc-and-script-sweep
- file: `D:\Project\YunxiBakeBot\README.md`; `D:\Project\YunxiBakeBot\scripts\apply_migrations.py`; `D:\Project\YunxiBakeBot\scripts\preflight_production.py`; `D:\Project\YunxiBakeBot\scripts\rebuild_embeddings.py`; `D:\Project\YunxiBakeBot\scripts\seed_baseline_knowledge.py`
- command: `rg -n "Platform (database migration|production preflight|embedding rebuild|baseline knowledge seed)|Description=Bakery Commerce Platform - Platform Service" README.md scripts/apply_migrations.py scripts/preflight_production.py scripts/rebuild_embeddings.py scripts/seed_baseline_knowledge.py`; `python -m compileall scripts/apply_migrations.py scripts/preflight_production.py scripts/rebuild_embeddings.py scripts/seed_baseline_knowledge.py`
- result: pass
- related_logbook: 2026-06-20 - chore(naming): 收口可见脚本与部署展示名
- related_adr: 0002-platform-storefront-boundaries-and-instance-naming
- contains_sensitive_data: no
- retention_note: 仅记录展示口径与脚本标题收口结果，不含业务数据
- summary: 用户可见部署展示名和运维脚本标题已切换为 `Platform` 口径，仓库路径与服务标识保持不变。

## E-20260620-021：当前权威文档的代码仓路径语义收口

- trace_id: 20260620-current-docs-repo-path-wording
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1.md`; `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1-schema-draft.md`; `D:\Project\YunxiBakeBot\docs\architecture\platform-miniapp-api-contract-v1.md`; `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-migration-audit-checklist.md`; `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-import-handoff-and-rollback-runbook.md`; `D:\Project\YunxiBakeBot\docs\harness-engineering\README.md`; `D:\Project\YunxiBakeBot\docs\harness-engineering\core\traceability-model.md`
- command: `rg -n "代码仓路径|Platform 主仓|Storefront MiniApp 代码仓路径" docs/architecture/customer-master-v1.md docs/architecture/customer-master-v1-schema-draft.md docs/architecture/platform-miniapp-api-contract-v1.md docs/architecture/youzan-customer-migration-audit-checklist.md docs/architecture/youzan-customer-import-handoff-and-rollback-runbook.md docs/harness-engineering/README.md docs/harness-engineering/core/traceability-model.md`
- result: pass
- related_logbook: 2026-06-20 - docs(naming): 将当前权威文档中的仓库名改写为代码仓路径语义
- related_adr: 0002-platform-storefront-boundaries-and-instance-naming
- contains_sensitive_data: no
- retention_note: 仅记录当前权威文档的命名措辞收口结果，不含业务数据
- summary: 当前权威文档和 Harness 入口已把 `YunxiBakeBot` / `YunxiBakeMiniApp` 进一步明确为代码仓路径语义，而不是产品角色名。

## E-20260620-022：README 残留高可见仓库名示例收口

- trace_id: 20260620-readme-visible-repo-example-cleanup
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\README.md`; `D:\Project\YunxiBakeBot\scripts\enable_utf8_console.ps1`
- command: `rg -n "Platform \\(repo: YunxiBakeBot\\)|github.com/srafyhucl-cpu/yunxibakebot|Platform repo \\(YunxiBakeBot\\)" README.md scripts/enable_utf8_console.ps1`
- result: pass
- related_logbook: 2026-06-20 - docs(readme): 收口 README 残留高可见仓库名示例
- related_adr: 0002-platform-storefront-boundaries-and-instance-naming
- contains_sensitive_data: no
- retention_note: 仅记录 README 高可见示例收口结果，不含业务数据
- summary: README 的目录树根节点、仓库链接占位和 UTF-8 控制台脚本注释已改成更明确的 repo 语义或真实仓库地址。

## E-20260620-023：README 旧仓库占位链接清理

- trace_id: 20260620-readme-repo-link-placeholders
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\README.md`
- command: `rg -n "your-repo|your-username|original-repo|github.com/srafyhucl-cpu/yunxibakebot.git" README.md`
- result: pass
- related_logbook: 2026-06-20 - docs(readme): 清理 README 旧仓库占位链接
- related_adr: 0002-platform-storefront-boundaries-and-instance-naming
- contains_sensitive_data: no
- retention_note: 仅记录 README 仓库链接示例更新结果，不含业务数据
- summary: README 中快速开始、部署和 fork 场景的主仓地址已统一为真实仓库链接，fork 示例保留用户变量但不再使用旧占位仓名。

## E-20260620-024：README 失效脚本入口清理

- trace_id: 20260620-readme-stale-script-entrypoints
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\README.md`; `D:\Project\YunxiBakeBot\docs\AGENTS\quick-reference.md`; `D:\Project\YunxiBakeBot\docs\api-spec.md`
- command: `rg -n "init_db.py|seed_knowledge.py|sync_youzan_products.py|apply_migrations.py|seed_baseline_knowledge.py|sync_real_products_from_youzan.py" README.md docs/AGENTS/quick-reference.md docs/api-spec.md`; `Test-Path scripts/apply_migrations.py; Test-Path scripts/seed_baseline_knowledge.py; Test-Path scripts/sync_real_products_from_youzan.py`
- result: pass
- related_logbook: 2026-06-20 - docs(readme): 清理 README 中已失效的脚本入口
- related_adr: 0002-platform-storefront-boundaries-and-instance-naming
- contains_sensitive_data: no
- retention_note: 仅记录 README 与速查文档的脚本入口校正结果，不含业务数据
- summary: README、quick-reference 和 api-spec 中的旧脚本入口已替换为当前仓库真实存在的初始化、知识种子和商品同步脚本。

## E-20260620-025：quick reference 数据库初始化路径修正

- trace_id: 20260620-quick-reference-database-path
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\docs\AGENTS\quick-reference.md`
- command: `Test-Path app/database.py; Test-Path app/repository/database.py`; `rg -n "app/repository/database.py|app/database.py" docs/AGENTS/quick-reference.md`
- result: pass
- related_logbook: 2026-06-20 - docs(agents): 修正 quick reference 的数据库初始化路径
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录 quick reference 路径修正结果，不含业务数据
- summary: `docs/AGENTS/quick-reference.md` 中数据库初始化入口已从不存在的 `app/repository/database.py` 改成当前真实存在的 `app/database.py`。

## E-20260620-026：README 目录树过时模型文件修正

- trace_id: 20260620-readme-tree-stale-model
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\README.md`
- command: `Test-Path app/models/youzan_product.py; Test-Path app/models/order.py`; `rg -n "youzan_product.py|order.py" README.md`
- result: pass
- related_logbook: 2026-06-20 - docs(readme): 修正目录树中的过时模型文件示例
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录 README 目录树模型路径修正结果，不含业务数据
- summary: README 目录树已不再展示不存在的 `app/models/youzan_product.py`，改为当前真实存在的 `app/models/order.py`。

## E-20260620-009：产品角色名与仓库路径名澄清

- trace_id: 20260620-name-clarification-role-vs-slug
- generated_at: 2026-06-20
- evidence_type: doc-sweep
- file: `D:\Project\YunxiBakeBot\README.md`; `D:\Project\YunxiBakeBot\docs\architecture\project-boundaries.md`; `D:\Project\YunxiBakeBot\docs\README.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `rg -n "仓库名|仓库 slug|历史过渡材料|命名约束|Storefront MiniApp" README.md docs/architecture/project-boundaries.md docs/README.md`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 澄清产品角色名与仓库路径名
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录命名澄清的文档命中结果，不含业务数据
- summary: 产品角色名、渠道角色名和仓库路径名的口径已重新压实，历史仓名只保留在路径和过渡引用里。

## E-20260620-003：客户迁移闭环入口收束

- trace_id: 20260620-customer-master-next-steps; 20260620-root-readme-customer-links; 20260620-platform-miniapp-contract-customer-links; 20260620-miniapp-handoff-customer-links; 20260620-customer-import-boundary-links; 20260620-customer-master-schema-next-steps; 20260620-customer-audit-next-steps; 20260620-customer-loop-four-sections
- generated_at: 2026-06-20
- evidence_type: handoff/runbook/doc
- file: `D:\Project\YunxiBakeBot\README.md`; `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1.md`; `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1-schema-draft.md`; `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-migration-audit-checklist.md`; `D:\Project\YunxiBakeBot\docs\architecture\platform-miniapp-api-contract-v1.md`; `D:\Project\YunxiBakeBot\docs\architecture\miniapp-ai-handoff-plan.md`; `D:\Project\YunxiBakeBot\docs\architecture\miniapp-phase1-execution-checklist.md`; `D:\Project\YunxiBakeBot\docs\architecture\project-boundaries.md`; `D:\Project\YunxiBakeBot\docs\architecture\two-repo-rollout-plan.md`
- command: `Select-String -Path README.md,docs/architecture/customer-master-v1.md,docs/architecture/customer-master-v1-schema-draft.md,docs/architecture/youzan-customer-migration-audit-checklist.md,docs/architecture/platform-miniapp-api-contract-v1.md,docs/architecture/miniapp-ai-handoff-plan.md,docs/architecture/miniapp-phase1-execution-checklist.md,docs/architecture/project-boundaries.md,docs/architecture/two-repo-rollout-plan.md -Pattern "youzan-customer-migration-audit-checklist|youzan-customer-formal-import-runbook|youzan-customer-import-handoff-and-rollback-runbook|verify_youzan_customer_import"`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 统一客户迁移闭环为四段口径; 2026-06-20 - docs(architecture): 更新 customer master v1 的后续入口; 2026-06-20 - docs(architecture): 更新 customer master schema 草案的实施建议; 2026-06-20 - docs(architecture): 更新客户迁移审计清单的后续入口; 2026-06-20 - docs(readme): 在根入口补齐客户迁移闭环; 2026-06-20 - docs(architecture): 补齐双仓 API 契约中的客户迁移权威入口; 2026-06-20 - docs(architecture): 收束 MiniApp 接力文档的客户迁移入口; 2026-06-20 - docs(architecture): 收束客户迁移入口到边界文档
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留客户迁移入口收束后的统一索引；仅记录文档入口与验证命令，不包含客户数据与执行报告正文。
- summary: 客户迁移闭环入口已经从 README、主档设计、schema 草案、审计清单、双仓 API 契约、MiniApp 历史接力文档和上层边界文档全部打通，并统一为审计、正式迁移、迁移后核对、交接/回滚四段口径，后续无论从产品、架构、接力还是执行入口进入，都能直接跳到同一套权威材料。

## E-20260620-004：客户迁移入口旧口径机械审计

- trace_id: 20260620-customer-entrypoint-regression-scan
- generated_at: 2026-06-20
- evidence_type: audit/doc
- file: `D:\Project\YunxiBakeBot\README.md`; `D:\Project\YunxiBakeBot\docs\README.md`; `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1.md`; `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1-schema-draft.md`; `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-migration-audit-checklist.md`; `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-formal-import-runbook.md`; `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-import-handoff-and-rollback-runbook.md`; `D:\Project\YunxiBakeBot\docs\architecture\platform-miniapp-api-contract-v1.md`; `D:\Project\YunxiBakeBot\docs\architecture\miniapp-ai-handoff-plan.md`; `D:\Project\YunxiBakeBot\docs\architecture\miniapp-phase1-execution-checklist.md`; `D:\Project\YunxiBakeBot\docs\architecture\project-boundaries.md`; `D:\Project\YunxiBakeBot\docs\architecture\two-repo-rollout-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `rg -n "三份当前权威入口|三份当前权威材料|三段当前权威材料" README.md docs/README.md docs/architecture`; `rg -n "待执行。|待执行\\.|待执行$" LOGBOOK.md`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 统一客户迁移闭环为四段口径
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录机械审计结果，不含业务数据和执行报告正文。
- summary: 活文档中已无客户迁移旧“三份/三段”口径，LOGBOOK 中也无“待执行”残留；客户迁移入口的四段闭环收口已进入稳定态。

## E-20260620-005：客户迁移闭环入口四段稳定态

- trace_id: 20260620-customer-loop-four-sections
- generated_at: 2026-06-20
- evidence_type: audit/doc
- file: `D:\Project\YunxiBakeBot\README.md`; `D:\Project\YunxiBakeBot\docs\README.md`; `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1.md`; `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1-schema-draft.md`; `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-migration-audit-checklist.md`; `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-formal-import-runbook.md`; `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-import-handoff-and-rollback-runbook.md`; `D:\Project\YunxiBakeBot\docs\architecture\platform-miniapp-api-contract-v1.md`; `D:\Project\YunxiBakeBot\docs\architecture\miniapp-ai-handoff-plan.md`; `D:\Project\YunxiBakeBot\docs\architecture\miniapp-phase1-execution-checklist.md`; `D:\Project\YunxiBakeBot\docs\architecture\project-boundaries.md`; `D:\Project\YunxiBakeBot\docs\architecture\two-repo-rollout-plan.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `rg -n "三份当前权威入口|三份当前权威材料|三段当前权威材料" README.md docs/README.md docs/architecture`; `rg -n "待执行。|待执行\\.|待执行$" LOGBOOK.md`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 统一客户迁移闭环为四段口径; 2026-06-20 - docs(architecture): 更新客户迁移审计清单的后续入口; 2026-06-20 - docs(architecture): 更新 customer master schema 草案的实施建议; 2026-06-20 - docs(architecture): 更新 customer master v1 的后续入口; 2026-06-20 - docs(readme): 在根入口补齐客户迁移闭环; 2026-06-20 - docs(architecture): 补齐双仓 API 契约中的客户迁移权威入口; 2026-06-20 - docs(architecture): 收束 MiniApp 接力文档的客户迁移入口; 2026-06-20 - docs(architecture): 收束客户迁移入口到边界文档; 2026-06-20 - docs(harness): record customer entrypoint regression scan
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录客户迁移入口四段稳定态的机械审计结果，不含客户数据与执行报告正文。
- summary: 客户迁移闭环入口已统一为审计、正式迁移、迁移后核对、交接/回滚四段口径，并且活文档与 LOGBOOK 中不再残留旧的三段/待执行表述；这套入口当前处于稳定态。

## E-20260620-006：MiniApp 接力文档建议项机械核对

- trace_id: 20260620-miniapp-ai-handoff-plan-regression-scan
- generated_at: 2026-06-20
- evidence_type: audit/doc
- file: `D:\Project\YunxiBakeBot\docs\architecture\miniapp-ai-handoff-plan.md`
- command: `rg -n "后续建议执行顺序|执行顺序|建议执行顺序" docs/architecture/miniapp-ai-handoff-plan.md`; `Get-Content -Path docs/architecture/miniapp-ai-handoff-plan.md -Encoding UTF8 | Select-Object -Skip 150 -First 120`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 统一客户迁移闭环为四段口径
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录 MiniApp 接力文档建议项机械核对结果，不含业务数据和执行报告正文。
- summary: `miniapp-ai-handoff-plan.md` 中“后续建议执行顺序”仅作为交付物项存在，没有独立残留的旧建议段落；MiniApp 接力文档本身无需继续改正文。

## E-20260620-007：客户迁移文档尾部扫尾确认

- trace_id: 20260620-customer-doc-tail-sweep
- generated_at: 2026-06-20
- evidence_type: audit/doc
- file: `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1.md`; `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1-schema-draft.md`; `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-migration-audit-checklist.md`
- command: `Get-Content -LiteralPath docs\architecture\customer-master-v1.md -Encoding UTF8 | Select-Object -Skip 460 -First 30`; `Get-Content -LiteralPath docs\architecture\customer-master-v1-schema-draft.md -Encoding UTF8 | Select-Object -Skip 545 -First 20`; `Get-Content -LiteralPath docs\architecture\youzan-customer-migration-audit-checklist.md -Encoding UTF8 | Select-Object -Skip 470 -First 20`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 统一 MiniApp 接力计划的交付物口径; 2026-06-20 - docs(architecture): 统一客户迁移闭环为四段口径; 2026-06-20 - docs(architecture): 更新客户迁移审计清单的后续入口; 2026-06-20 - docs(architecture): 更新 customer master schema 草案的实施建议; 2026-06-20 - docs(architecture): 更新 customer master v1 的后续入口
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅记录客户迁移文档尾部扫尾确认结果，不含客户数据和执行报告正文。
- summary: `customer-master-v1.md`、`customer-master-v1-schema-draft.md` 和 `youzan-customer-migration-audit-checklist.md` 的尾部建议均已指向当前闭环入口，没有再发现需要改成旧阶段的残留段落。

## E-20260617-045：生产后台 MVP 前端 dist 部署

- trace_id: 20260617-production-admin-frontend-check
- generated_at: 2026-06-17
- evidence_type: release/command/deploy
- file: `D:\Project\YunxiBakeMiniApp\reports\production-admin-check\production-admin-20260617-045345.json`; `D:\Project\YunxiBakeMiniApp\reports\production-admin-check\latest.json`; `D:\Project\YunxiBakeMiniApp\reports\release-readiness\readiness-20260617-125450.json`
- command: `npm run typecheck` and `npm run build` in `YunxiBakeBot\web\admin`; `npm run check:production-admin`; `npm run release:readiness`
- result: pass
- related_logbook: 2026-06-17 - deploy(production): 部署后台 MVP 前端 dist
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留生产后台前端检查和 readiness 报告；远程保留部署前 dist 备份目录，不包含密钥
- summary: 生产 `/admin/` 已切换到当前后台 MVP dist，包含装修、订单、地址、商品、转人工和店铺配置关键页面 chunk；小程序 release readiness 升级为 19/19 通过。

## E-20260617-044：生产小程序只读 API 切通

- trace_id: 20260617-production-miniapp-api-check
- generated_at: 2026-06-17
- evidence_type: release/command/deploy
- file: `D:\Project\YunxiBakeMiniApp\reports\production-api-check\production-miniapp-api-20260617-043836.json`; `D:\Project\YunxiBakeMiniApp\reports\production-api-check\latest.json`; `D:\Project\YunxiBakeMiniApp\reports\release-readiness\readiness-20260617-123907.json`
- command: `npm run check:production-miniapp-api`; `npm run release:readiness`; remote `systemctl restart/start yunxibakebot`
- result: pass
- related_logbook: 2026-06-17 - deploy(production): 切通小程序只读 API
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留生产只读 API 检查和 readiness 报告；远程保留同步前 app 备份目录，不包含密钥或证书私钥
- summary: 生产后端同步本地 MVP `app/` 代码后，小程序公开只读 API `/api/v1/miniapp/pages/home`、`/api/v1/miniapp/products`、`/api/v1/miniapp/shop-settings` 均返回 `code=0`；小程序 release readiness 升级为 18/18 通过。

## E-20260617-043：release readiness 纳入生产域名门槛

- trace_id: 20260617-release-readiness-gate
- generated_at: 2026-06-17
- evidence_type: release/command
- file: `D:\Project\YunxiBakeMiniApp\reports\release-readiness\readiness-20260617-112414.json`; `D:\Project\YunxiBakeMiniApp\reports\release-readiness\latest.json`; `D:\Project\YunxiBakeMiniApp\reports\domain-check\domain-check-20260617-032342.json`
- command: `npm run release:readiness` in `YunxiBakeMiniApp`
- result: pass
- related_logbook: 2026-06-17 - test(release): readiness 纳入生产域名门槛
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留 release readiness 与生产域名检查报告，不包含密钥或证书私钥
- summary: 小程序发布 readiness 已新增 `production domain HTTPS check`，当前 17/17 checks passed；生产 `yunxifood.cn` 连通性检查成为发布前固定门槛。

## E-20260617-042：yunxifood.cn 根入口与证书切通

- trace_id: 20260617-domain-switch-yunxifood
- generated_at: 2026-06-17
- evidence_type: command/doc
- file: `D:\Project\YunxiBakeMiniApp\reports\domain-check\domain-check-20260617-032041.json`; `D:\Project\YunxiBakeMiniApp\reports\domain-check\latest.json`; `D:\Project\YunxiBakeBot\scripts\yunxifood.cn.nginx.conf`; `D:\Project\YunxiBakeBot\docs\design\4-上线检查清单.md`
- command: `npm run check:production-domain` in `YunxiBakeMiniApp`; remote `nginx -t && systemctl reload nginx`; `curl https://yunxifood.cn/health`; `curl https://yunxifood.cn`
- result: pass
- related_logbook: 2026-06-17 - chore(release): 域名统一切换到 yunxifood.cn
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留生产域名检查 JSON 与 Nginx 模板，不包含密钥或证书私钥
- summary: `yunxifood.cn` 已启用正确证书并在根路径返回后台入口页，`/health` 返回 200，`/` 由 Nginx 精确重定向到 `/admin/`；后端发布文档与本地 Nginx 模板同步更新。

## E-20260617-041：域名统一切换到 yunxifood.cn

- trace_id: 20260617-domain-switch-yunxifood
- generated_at: 2026-06-17
- evidence_type: command/doc
- file: `D:\Project\YunxiBakeBot\docs\design\1-业务方案.md`; `D:\Project\YunxiBakeBot\docs\design\2-工作流设计.md`; `D:\Project\YunxiBakeBot\docs\design\3-技术架构.md`; `D:\Project\YunxiBakeBot\docs\design\4-上线检查清单.md`; `D:\Project\YunxiBakeBot\项目进度与配置清单.md`; `D:\Project\YunxiBakeBot\scripts\setup_wecom.sh`
- command: `rg -n "hclstudio\.cn|yunxifood\.cn" docs scripts 项目进度与配置清单.md LOGBOOK.md`
- result: pass
- related_logbook: 2026-06-17 - chore(release): 域名统一切换到 yunxifood.cn
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留文档变更和命令输出摘要；不包含密钥或证书内容
- summary: 后端发布文档、技术架构、有赞 webhook、管理后台子域、Nginx/certbot 示例与项目配置清单已统一到 `yunxifood.cn` / `admin.yunxifood.cn`；旧域名未在发布文档和脚本范围内残留。生产 HTTPS 与根入口已由 E-20260617-042 收口，微信公众平台和有赞云配置仍需复验。

## E-20260617-040：发布 readiness 总门槛

- trace_id: 20260617-release-readiness-gate
- generated_at: 2026-06-17
- evidence_type: release/command
- file: `D:\Project\YunxiBakeMiniApp\reports\release-readiness\readiness-20260617-092031.json`; `D:\Project\YunxiBakeMiniApp\reports\release-readiness\latest.json`; `D:\Project\YunxiBakeMiniApp\docs\release\manual-acceptance-checklist.md`
- command: `npm run release:readiness` in `YunxiBakeMiniApp`; `npm run check:addresses` in `web/admin`
- result: pass
- related_logbook: 2026-06-17 - test(release): 小程序发布 readiness 总门槛
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留 JSON readiness 报告；报告不包含密钥或 Token
- summary: 新增发布前总检查入口和手工验收清单，最终 15/15 checks passed；覆盖小程序配置、静态/类型检查、后台结构检查、后端目标测试、关键 smoke 截图证据和临时数据库残留扫描；本机未发现微信开发者工具 CLI，开发者工具/真机/支付/审核材料仍需按清单补证据。

## E-20260617-039：手机端轻量运营入口

- trace_id: 20260617-mobile-ops-admin
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\mobile-operations-smoke.png`
- command: `python -m py_compile web\admin\scripts\smoke_mobile_operations.py`; `npm run check:mobile-ops`; `npm run typecheck` in `web/admin`; `npm run smoke:mobile-ops`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 手机端轻量运营入口
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留 smoke 截图；临时 SQLite DB 按单文件规则清理，复查未发现 `mobile-operations-smoke.db*` 残留
- summary: 后台 Web 新增手机端轻量运营入口：统一导航配置、手机底栏高频入口、概览页手机运营快捷区，并通过移动视口 smoke 验证底栏可进入订单、商品、转人工、设置和概览。

## E-20260617-038：MVP 主链路巡检复跑

- trace_id: 20260617-mvp-main-flow-regression
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\decoration-product-picker-smoke.png`; `D:\Project\YunxiBakeBot\reports\ui\shop-settings-smoke.png`; `D:\Project\YunxiBakeBot\reports\ui\addresses-editing-smoke.png`; `D:\Project\YunxiBakeBot\reports\ui\orders-summary-smoke.png`; `D:\Project\YunxiBakeBot\reports\ui\orders-confirmation-smoke.png`; `D:\Project\YunxiBakeBot\reports\ui\products-active-toggle-smoke.png`; `D:\Project\YunxiBakeBot\reports\ui\transfers-queue-smoke.png`
- command: miniapp `npm run check:miniapp`; miniapp `npm run typecheck`; `npm run typecheck` in `web/admin`; `npm run check:decoration`; `npm run check:orders`; `npm run check:addresses`; `npm run check:products`; `npm run check:shop-settings`; `npm run smoke:decoration-product-picker`; `npm run smoke:shop-settings`; `npm run smoke:addresses-editing`; `npm run smoke:orders-summary`; `npm run smoke:orders-confirmation`; `npm run smoke:products-active-toggle`; `npm run smoke:transfers-queue`; backend API target pytest 40 passed; backend transfer pytest 15 passed
- result: pass
- related_logbook: 2026-06-17 - test(mvp): 主链路巡检复跑
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留 smoke 截图；临时 SQLite DB 按单文件规则清理，复查未发现 `.db/.db-wal/.db-shm` 残留
- summary: 当前 MVP 主链路巡检通过，覆盖后台装修发布到小程序 JSON、店铺运营配置、顾客地址编辑、订单看板、订单状态流转、商品上下架、转人工队列、小程序静态/类型检查和后端 API 目标测试。

## E-20260617-037：后台人工回复 API 与转人工 smoke 收口

- trace_id: 20260617-admin-human-reply-api
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\transfers-queue-smoke.png`
- command: `python -m pytest -o addopts="" tests/api/test_admin_transfer_api.py tests/service/test_miniapp_chat.py tests/api/test_miniapp_chat_api.py`; `python -m py_compile app\api\admin_transfer.py web\admin\scripts\smoke_transfers_queue.py tests\api\test_admin_transfer_api.py tests\service\test_miniapp_chat.py tests\api\test_miniapp_chat_api.py`; `npm run typecheck` in `web/admin`; `npm run smoke:transfers-queue`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 人工回复接口与转人工 smoke 收口
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留 smoke 截图；临时 SQLite DB 按单文件规则清理
- summary: 后台转人工详情回复输入改为原生 textarea；后台人工回复 API 路由测试覆盖写入调用、空内容拒绝和会话消息返回；转人工浏览器 smoke 继续稳定覆盖入队、详情和接单。

## E-20260617-036：小程序人工回复刷新体验验证

- trace_id: 20260617-miniapp-human-reply-refresh
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest -o addopts="" tests/service/test_miniapp_chat.py tests/api/test_miniapp_chat_api.py`; `python -m py_compile app\service\miniapp_chat.py tests\service\test_miniapp_chat.py tests\api\test_miniapp_chat_api.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 人工回复刷新体验
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告
- summary: 小程序客服页在转人工状态下新增等待提示、手动刷新和短轮询；后端服务测试证明后台人工回复以 `assistant` 写入后，小程序 `get_chat_payload` 能拉取展示。

## E-20260617-035：转人工队列浏览器 smoke

- trace_id: 20260617-transfers-queue-smoke
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\transfers-queue-smoke.png`
- command: `npm run smoke:transfers-queue`; `npm run typecheck` in `web/admin`; `python -m py_compile web\admin\scripts\smoke_transfers_queue.py`; `python -m pytest -o addopts="" tests/service/test_miniapp_chat.py tests/api/test_miniapp_chat_api.py tests/test_lifespan_routes_services.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 转人工队列浏览器 smoke
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留 smoke 截图；临时 SQLite DB 按单文件规则清理
- summary: 浏览器真实打开后台转人工页，验证小程序主动转人工 API 创建的待处理工单会出现在后台队列，详情抽屉可打开，后台可接单并更新为已接单。

## E-20260617-034：小程序客服主动转人工接口验证

- trace_id: 20260617-miniapp-chat-transfer
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest -o addopts="" tests/service/test_miniapp_chat.py tests/api/test_miniapp_chat_api.py tests/test_lifespan_routes_services.py`; `python -m py_compile app\api\miniapp_chat.py app\service\miniapp_chat.py app\lifespan_services.py tests\service\test_miniapp_chat.py tests\api\test_miniapp_chat_api.py tests\test_lifespan_routes_services.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 用户主动转人工客服
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告
- summary: 小程序主动转人工接口复用既有转人工工单和后台队列；目标后端测试 13 passed，后端编译和小程序静态/类型检查均通过。

## E-20260617-033：订单经营看板浏览器 smoke

- trace_id: 20260617-admin-order-summary-smoke
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\orders-summary-smoke.png`
- command: `npm run smoke:orders-summary`; `npm run check:orders`; `npm run typecheck` in `web/admin`; `python -m py_compile web\admin\scripts\smoke_orders_summary.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 订单经营看板浏览器 smoke
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留 smoke 截图；临时 SQLite DB 按单文件规则清理
- summary: 浏览器真实打开后台订单页，验证全量 summary 卡片显示 3 笔测试订单，点击履约中和已关闭看板卡片后表格按后端 `boardFilter` 口径刷新。

## E-20260617-032：订单经营看板全量汇总

- trace_id: 20260617-admin-order-summary
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest -o addopts="" tests/api/test_admin_order_api.py`; `python -m py_compile app\api\admin_orders.py app\repository\order_repo.py app\service\miniapp_order.py tests\api\test_admin_order_api.py`; `npm run check:orders`; `npm run typecheck` in `web/admin`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 订单经营看板全量汇总
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 后台订单新增 `GET /api/v1/admin/orders/summary` 全量聚合接口，订单列表支持 `boardFilter`，后台订单页看板读取后端 summary 并按同一口径加载列表。

## E-20260617-031：订单管理经营看板

- trace_id: 20260617-admin-order-board
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:orders`; `npm run typecheck` in `web/admin`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 订单管理经营看板
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 后台订单页新增当前页经营看板，集中配置全部、待支付、待确认、履约中、已完成、已关闭口径，运营可点击看板卡片切换当前订单表格视图。

## E-20260617-030：订单状态事件驱动真实时间线

- trace_id: 20260617-order-status-events-timeline
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest -o addopts="" tests/service/test_miniapp_order.py tests/api/test_miniapp_order_api.py tests/api/test_admin_order_api.py tests/test_lifespan_routes_services.py`; `python -m py_compile app\models\order.py app\repository\order_event_repo.py app\repository\order_repo.py app\service\miniapp_order.py app\service\miniapp_order_serialization.py app\api\admin_orders.py app\api\miniapp_orders.py app\lifespan_services.py app\main.py app\migrations\schema.py tests\service\test_miniapp_order.py tests\api\test_miniapp_order_api.py tests\api\test_admin_order_api.py tests\test_lifespan_routes_services.py`; `npm run check:orders`; `npm run typecheck` in `web/admin`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(order): 订单状态事件驱动真实时间线
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 新增 `order_events` 追加式订单状态事件表，创建订单、后台流转、用户取消、后台/超时关闭未支付都会追加事件；小程序订单详情和后台订单详情读取同一 `timeline` 字段展示真实节点时间。

## E-20260617-029：协议隐私售后统一配置

- trace_id: 20260617-shop-policy-config
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest -o addopts="" tests/api/test_shop_operations_api.py`; `python -m py_compile app\models\config.py app\service\shop_operations.py app\api\admin_config.py tests\api\test_shop_operations_api.py`; `npm run check:shop-settings`; `npm run typecheck` in `web/admin`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 协议隐私售后统一配置
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 店铺公开运营配置新增隐私政策、用户协议和售后说明标题/内容；后台店铺配置页可维护这些文案，小程序新增统一协议页，我的页可查看，checkout 提交前必须勾选同意用户协议和隐私政策。

## E-20260617-028：后台顾客地址操作审计

- trace_id: 20260617-admin-address-audit
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\addresses-editing-smoke.png`
- command: `python -m pytest -o addopts="" tests/api/test_admin_address_api.py tests/test_lifespan_routes_services.py`; `python -m py_compile app\api\admin_addresses.py app\service\miniapp_address.py app\repository\miniapp_address_audit_repo.py app\repository\miniapp_address_repo.py app\models\miniapp_address.py app\lifespan_services.py app\main.py tests\api\test_admin_address_api.py tests\test_lifespan_routes_services.py`; `npm run check:addresses`; `npm run typecheck` in `web/admin`; `npm run smoke:addresses-editing`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 顾客地址操作审计
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留浏览器成功截图和命令结论；临时 SQLite DB、WAL/SHM 已逐个清理；Chrome profile 目录按禁止递归删除规则未自动清理
- summary: 后台代顾客新增、编辑、设默认和删除小程序地址时写入 `miniapp_address_audit` 追加式审计，地址详情返回最近 5 条 `auditLogs`，后台详情抽屉展示“最近操作”；浏览器 smoke 覆盖新增、编辑、小程序地址读取和审计展示。

## E-20260617-027：我的页会员摘要配置驱动

- trace_id: 20260617-profile-member-config
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:miniapp`; `npm run typecheck` in `YunxiBakeMiniApp`; `npm run check:decoration`; `npm run typecheck` in `YunxiBakeBot\web\admin`; `python -m pytest -o addopts="" tests/service/test_shop_page_config.py tests/api/test_shop_page_config_api.py`; `python -m pytest` in `YunxiBakeBot`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 我的页会员摘要配置驱动
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 扩展 `memberSummary.props`，后台默认 profile 模板和装修编辑器可配置会员卡副标题、有效期、余额和权益卡数量；小程序我的页从装修配置读取这些字段并对旧配置兜底。

## E-20260617-026：小程序客服体验与后端测试补齐

- trace_id: 20260617-miniapp-chat-experience-tests
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:miniapp`; `npm run typecheck` in `YunxiBakeMiniApp`; `python -m pytest -o addopts="" tests/service/test_miniapp_chat.py tests/api/test_miniapp_chat_api.py`; `python -m pytest` in `YunxiBakeBot`
- result: pass
- related_logbook: 2026-06-17 - chore(miniapp): 补齐客服体验与后端测试
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 小程序客服页保留欢迎消息兜底、加载失败提示、发送中状态和错误提示样式；后端新增小程序客服 service/API 测试，覆盖发送消息、历史拉取、用户头隔离、demo 用户回退和空消息拒绝。

## E-20260617-025：未支付超时自动关闭

- trace_id: 20260617-miniapp-payment-timeout-scheduler
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_admin_order_api.py tests/service/test_miniapp_order.py tests/api/test_miniapp_order_api.py tests/repository/test_youzan_repo.py`; `python -m py_compile app\config.py app\repository\order_repo.py app\service\miniapp_order.py app\service\miniapp_payment.py app\service\miniapp_order_timeout.py app\api\admin_orders.py app\main.py tests\service\test_miniapp_order.py tests\api\test_admin_order_api.py`; architecture rg checks; `npm run check:orders`; `npm run typecheck` in `YunxiBakeBot\web\admin`; `npm run check:miniapp`; `npm run typecheck` in `YunxiBakeMiniApp`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 未支付超时自动关闭
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 后端新增未支付超时扫描器并在 lifespan 注册，后台可手动触发一次扫描；超过 30 分钟未支付订单会被关闭并释放真实商品库存，新订单和已支付订单不会被误关。

## E-20260617-024：订单支付状态 MVP 闭环

- trace_id: 20260617-miniapp-payment-state-mvp
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_admin_order_api.py tests/service/test_miniapp_order.py tests/api/test_miniapp_order_api.py tests/repository/test_youzan_repo.py`; `python -m py_compile app\service\miniapp_payment.py app\service\miniapp_order.py app\api\miniapp_orders.py app\api\admin_orders.py tests\api\test_admin_order_api.py tests\service\test_miniapp_order.py tests\api\test_miniapp_order_api.py`; architecture rg checks; `npm run check:orders`; `npm run typecheck` in `YunxiBakeBot\web\admin`; `npm run check:miniapp`; `npm run typecheck` in `YunxiBakeMiniApp`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 订单支付状态 MVP 闭环
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 订单序列化输出支付状态字段，小程序可模拟支付确认，后台订单管理可展示支付状态并人工关闭未支付订单释放库存；批量超时关闭仍保留 30 分钟规则，真实微信支付后续接入同一状态字段。

## E-20260617-023：订单预约时间后端准入校验

- trace_id: 20260617-miniapp-order-expect-time-guard
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_shop_operations_api.py tests/service/test_miniapp_order.py tests/api/test_miniapp_order_api.py tests/repository/test_youzan_repo.py`; `python -m py_compile app\service\business_hours.py app\service\shop_operations.py app\service\miniapp_order_schedule.py app\service\miniapp_order.py app\api\admin_config.py app\lifespan_services.py tests\api\test_shop_operations_api.py tests\service\test_miniapp_order.py tests\api\test_miniapp_order_api.py`; architecture rg checks; miniapp check/typecheck; admin typecheck
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 订单预约时间后端准入校验
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 后端创建小程序订单前校验 `expectTime` 格式和店铺 `businessHours`，非法预约时间返回 400 且不会先预占真实商品库存；营业时间解析、店铺运营配置读写和订单校验使用共享服务，后台配置 API 也会拒绝非法 `businessHours`。

## E-20260617-022：店铺营业时间格式校验

- trace_id: 20260617-admin-shop-business-hours-validation
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:shop-settings`; `npm run typecheck` in `web/admin`; `python -m pytest --no-cov tests/api/test_shop_operations_api.py`; `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 店铺营业时间格式校验
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 后台店铺配置页保存前校验 `businessHours` 格式，避免小程序 checkout 时间选择器收到不可解析配置；后台结构检查、类型检查、店铺配置 API 测试和小程序检查均通过。

## E-20260617-021：Checkout 时间选择联动后台营业时间

- trace_id: 20260617-miniapp-checkout-business-hours
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`; `npm run typecheck` in `web/admin`
- result: pass
- related_logbook: 2026-06-17 - chore(miniapp): Checkout 时间选择联动后台营业时间
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: checkout 时间 picker 的小时选项由小程序公开店铺配置 `businessHours` 生成，后台调整营业时间后小程序下单时段可同步收口。

## E-20260617-020：Checkout 期望时间升级为日期时间选择器

- trace_id: 20260617-miniapp-checkout-time-picker
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`; `python -m py_compile app\api\miniapp_orders.py app\service\miniapp_order.py tests\service\test_miniapp_order.py tests\api\test_miniapp_order_api.py`; `npm run typecheck` in `web/admin`
- result: pass
- related_logbook: 2026-06-17 - chore(miniapp): Checkout 期望时间升级为日期时间选择器
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: checkout 使用原生 picker 生成稳定格式期望时间，并抽出时间工具，后续可接后台营业时间配置；小程序和后台类型/静态检查通过。

## E-20260617-019：Checkout 增强表单校验与提示

- trace_id: 20260617-miniapp-checkout-form-validation
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`; `python -m py_compile app\api\miniapp_orders.py app\service\miniapp_order.py tests\service\test_miniapp_order.py tests\api\test_miniapp_order_api.py`; `npm run typecheck` in `web/admin`
- result: pass
- related_logbook: 2026-06-17 - chore(miniapp): Checkout 增强表单校验与提示
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: checkout 页面新增手机号、配送地址、期望时间的前置校验，并将错误稳定展示在页面内；小程序和后台类型/静态检查通过。

## E-20260617-018：Checkout 展示后端下单失败原因

- trace_id: 20260617-miniapp-checkout-error-feedback
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_miniapp_order_api.py tests/service/test_miniapp_order.py`; `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`; `npm run typecheck` in `web/admin`
- result: pass
- related_logbook: 2026-06-17 - chore(miniapp): Checkout 展示后端下单失败原因
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 后端订单 API/service 测试确认库存错误语义仍稳定；小程序 HTTP 层会保留后端 `detail/message`，checkout 页面将具体错误展示给用户并禁用重复提交。

## E-20260617-017：小程序用户取消订单并释放库存

- trace_id: 20260617-miniapp-order-user-cancel
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/service/test_miniapp_order.py tests/api/test_miniapp_order_api.py tests/repository/test_youzan_repo.py`; `python -m py_compile app\api\miniapp_orders.py app\service\miniapp_order.py tests\service\test_miniapp_order.py tests\api\test_miniapp_order_api.py`; architecture `rg` checks; `npm run typecheck` in `web/admin`; `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 小程序用户取消订单并释放库存
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 后端服务/API 测试覆盖用户取消自己的待确认/已确认订单并释放真实商品库存、制作中不可取消、不能取消他人订单；小程序订单详情页加入取消按钮，小程序和后台类型/静态检查通过。

## E-20260617-016：小程序真实商品库存预占与取消释放

- trace_id: 20260617-miniapp-order-stock-reservation
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/service/test_miniapp_order.py tests/api/test_miniapp_order_api.py tests/repository/test_youzan_repo.py`; `python -m py_compile app\repository\youzan_inventory_repo.py app\service\miniapp_order_inventory.py app\service\miniapp_order.py app\lifespan_services.py app\main.py tests\service\test_miniapp_order.py tests\api\test_miniapp_order_api.py`; architecture `rg` checks; `npm run typecheck` in `web/admin`; `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 小程序真实商品库存预占与取消释放
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 服务/API 测试覆盖真实商品下单扣减库存、取消订单释放库存、重复商品项合并后按总数量校验库存；架构扫描确认 API 不穿透仓储、service 不直连数据库；小程序和后台类型/静态检查通过。

## E-20260617-015：小程序下单真实商品库存校验

- trace_id: 20260617-miniapp-order-stock-guard
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/service/test_miniapp_order.py tests/api/test_miniapp_order_api.py tests/repository/test_youzan_repo.py`; `python -m py_compile app\repository\youzan_repo.py app\service\miniapp_order.py app\api\miniapp_orders.py tests\api\test_miniapp_order_api.py tests\service\test_miniapp_order.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`; admin `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 小程序下单接入真实商品库存校验
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论；本轮未创建临时 DB/截图产物
- summary: 小程序创建订单时，如果商品存在于后端商品宽表，则以宽表价格、库存和上下架状态为准；服务和 API 测试覆盖库存充足使用后端价格、库存不足返回 400、售罄拒绝、下架拒绝，并保留未入库 Mock/fallback 商品下单能力。

## E-20260617-014：小程序下单到后台完整履约 smoke

- trace_id: 20260617-admin-orders-confirmation-smoke
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\orders-confirmation-smoke.png`
- command: `npm run smoke:orders-confirmation`; `npm run check:orders`; backend admin `npm run typecheck`; `python -m pytest --no-cov tests/service/test_miniapp_order.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 小程序下单到后台完整履约 smoke 跑通
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留截图与命令结论；临时 SQLite DB 与失败调试截图已逐个删除
- summary: 通过小程序订单 API 创建测试订单，真实浏览器打开后台订单管理页并依次点击“确认订单、开始制作、配送中、完成”，小程序订单详情 API 每一步读取到 `confirmed`、`making`、`delivering`、`done`，最终后台订单详情抽屉显示已完成，证明用户下单、后台履约、用户侧状态读取这条 MVP 订单主链路可联通。

## E-20260617-013：后台商品上下架驱动小程序目录 smoke

- trace_id: 20260617-admin-products-active-toggle-smoke
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\products-active-toggle-smoke.png`
- command: `npm run smoke:products-active-toggle`; `npm run smoke:decoration-product-picker`; `npm run check:products`; `npm run check:decoration`; backend admin `npm run typecheck`; `python -m pytest --no-cov tests/api/test_admin_featured_catalog_api.py tests/api/test_miniapp_catalog_api.py tests/service/test_miniapp_catalog.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 商品上下架驱动小程序目录 smoke 跑通
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留截图与命令结论；临时 SQLite DB 与失败调试截图已逐个删除；既有 Chrome profile 目录按禁止递归删除规则未自动清理
- summary: 真实浏览器操作后台商品管理页，搜索测试商品 `smoke active cheesecake`，执行下架后小程序 `/api/v1/miniapp/products?ids=92017004` 不再返回该商品；再在已下架筛选中执行上架后，小程序商品接口恢复返回该商品。共享 smoke 工具同时回归通过装修商品选择器链路。

## E-20260617-012：后台装修商品选择器浏览器 smoke

- trace_id: 20260617-admin-decoration-product-picker-smoke
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\decoration-product-picker-smoke.png`
- command: `npm run smoke:decoration-product-picker` in `YunxiBakeBot\web\admin`; `npm run check:decoration`; backend admin `npm run typecheck`; `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 装修商品选择器浏览器 smoke 跑通
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留截图与命令结论；临时 SQLite DB 与失败调试截图已逐个删除；既有 Chrome profile 目录按禁止递归删除规则未自动清理
- summary: 真实浏览器通过后台装修页切换到商品页货架模块，打开商品选择器，搜索测试商品 `smoke picker strawberry cake`，执行保存草稿和发布；随后小程序 `/api/v1/miniapp/pages/products` published 配置读取到 `productIds=["91017003"]`，证明后台装修生产的 JSON 配置能驱动小程序端读取。

## E-20260617-011：后台装修自动化选择器结构验证

- trace_id: 20260617-admin-decoration-testids
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:decoration` and `npm run typecheck` in `YunxiBakeBot\web\admin`; `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py`; `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 装修页补稳定自动化选择器
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 店铺装修页关键操作点补充稳定 `data-testid`、`data-block-id` 和 `data-product-id`，覆盖页面选择、保存发布、模块卡片、已选商品区、选品弹窗、搜索和加入商品按钮；装修结构检查已纳入这些自动化选择器，便于后续 Playwright/CDP smoke 直接按稳定选择器执行。

## E-20260617-010：后台装修已选商品名称展示与商品链路验证

- trace_id: 20260617-admin-decoration-selected-product-titles
- generated_at: 2026-06-17
- evidence_type: command/api
- file: local command output (no persisted artifact)
- command: 使用本地临时 SQLite DB 启动后端 `127.0.0.1:7001` 和后台 Vite `127.0.0.1:5173`，种入 `smoke picker strawberry cake`，通过后台商品搜索 API 命中 `youzan_item_id=91017003`，再保存并发布 `products` 页面装修草稿，最后用小程序 `/api/v1/miniapp/pages/products` 校验 `productIds=["91017003"]`；随后运行 `npm run check:decoration`、后台 `npm run typecheck`、装修 API/service 测试、小程序静态检查和小程序 typecheck
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 装修商品货架已选商品显示名称
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论；临时 SQLite DB、一次性 Chrome CDP 调试脚本已逐个删除；Chrome 点击专项未形成通过截图证据
- summary: 店铺装修页商品货架已选区新增商品名称缓存和展示，选品列表加载或加入商品时复用后台商品列表数据，已选标签优先显示商品名并保留商品 ID 辅助识别；API smoke 证明后台商品搜索、装修草稿保存、发布和小程序页面配置读取能围绕同一个商品 ID 串起来。

## E-20260617-009：后台装修分类与服务入口浏览器 smoke

- trace_id: 20260617-admin-decoration-grid-link-editor
- generated_at: 2026-06-17
- evidence_type: screenshot
- file: `D:\Project\YunxiBakeBot\reports\ui\admin-decoration-grid-link-smoke.png`
- command: 使用临时 SQLite DB 启动本地后端 `127.0.0.1:7001`、后台 Vite `127.0.0.1:5173`、headless Chrome CDP `127.0.0.1:9224`；浏览器进入 `/admin-v2/decoration`，切换到 `products` 页面通过分类宫格表单发布 `smoke-category-a-202606170121`、`smoke-category-b-202606170121`，再切换到 `profile` 页面通过服务入口表单发布 `smoke-service-title-202606170121` 和 `smoke-service-target-202606170121`；随后调用小程序页面 API 核对 published 配置
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 装修分类与服务入口支持结构化编辑
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留截图与本地 smoke 命令结论；临时 SQLite DB、一次性 smoke 脚本和调试脚本已逐个删除；既有 Chrome profile 目录按禁止递归删除规则未自动清理
- summary: 浏览器真实操作证明后台装修页的分类宫格、服务入口结构化表单可保存并发布；小程序 `/api/v1/miniapp/pages/products` 和 `/api/v1/miniapp/pages/profile` 读取到发布后的分类 ID、服务入口标题和跳转目标。

## E-20260617-008：后台装修分类与服务入口结构化编辑验证

- trace_id: 20260617-admin-decoration-grid-link-editor
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:decoration` and `npm run typecheck` in `YunxiBakeBot\web\admin`; `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py`; architecture rg checks; `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 装修分类与服务入口支持结构化编辑
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 店铺装修页为 `categoryGrid` 增加分类 ID 多行表单，为 `quickLinks` 和 `serviceGrid` 增加模块标题、入口增删、图标文字、跳转类型和跳转目标表单；新增结构检查脚本防止关键模块退回 JSON-only。

## E-20260617-007：后台装修多页面切换浏览器 smoke

- trace_id: 20260617-admin-decoration-page-switcher
- generated_at: 2026-06-17
- evidence_type: screenshot
- file: `D:\Project\YunxiBakeBot\reports\ui\admin-decoration-page-switcher-smoke.png`
- command: 使用临时 SQLite DB 启动本地后端 `127.0.0.1:7001`、后台 Vite `127.0.0.1:5173`、headless Chrome CDP `127.0.0.1:9224`；浏览器进入 `/admin-v2/decoration`，切换到 `products` 页面，修改商品货架标题为 `smoke-products-shelf-20260617010822`，保存草稿并发布；随后调用 `/api/v1/miniapp/pages/products` 核对小程序 published 配置
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 装修编辑器支持多页面切换
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留截图与本地 smoke 命令结论；临时 SQLite DB、一次性 smoke 脚本和调试脚本已逐个删除；Chrome profile 目录按禁止递归删除规则未自动清理
- summary: 浏览器真实操作证明后台装修页可切换到商品页、编辑模块配置、保存草稿并发布；保存草稿时小程序 published 仍保持旧标题，发布后小程序页面配置读取到新标题。

## E-20260617-006：后台装修多页面切换验证

- trace_id: 20260617-admin-decoration-page-switcher
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py`; `python -m py_compile app\service\shop_page_config.py tests\api\test_shop_page_config_api.py tests\service\test_shop_page_config.py`; `npm run typecheck` in `YunxiBakeBot\web\admin`; architecture rg checks; `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 装修编辑器支持多页面切换
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 后台装修编辑器新增页面选择器，加载、刷新、保存草稿和发布均按当前页面 ID 调用既有装修 API；默认页面配置拆分为 `home`、`products`、`profile` 三套模块，并通过服务和 API 测试覆盖。

## E-20260617-005：后台装修商品选择弹窗分页验证

- trace_id: 20260617-admin-decoration-product-picker-pagination
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run typecheck` and `npm run build` in `YunxiBakeBot\web\admin`; `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/api/test_admin_featured_catalog_api.py tests/api/test_miniapp_catalog_api.py`; `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 装修商品选择弹窗补齐分页
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论；`web/admin/dist/` 为 build 生成的忽略目录，按项目禁止递归删除规则未自动清理
- summary: 店铺装修商品选择弹窗补齐当前页、总数和页大小状态；搜索时重置到第一页，翻页时复用既有商品列表接口加载对应页；弹窗底部展示分页条和在售商品总数。

## E-20260617-004：后台装修商品货架弹窗选品验证

- trace_id: 20260617-admin-decoration-product-picker
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run typecheck` and `npm run build` in `YunxiBakeBot\web\admin`; `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/api/test_admin_featured_catalog_api.py tests/api/test_miniapp_catalog_api.py`; architecture rg checks; `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 装修商品货架支持弹窗选品
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论；`web/admin/dist/` 为 build 生成的忽略目录，按项目禁止递归删除规则未自动清理
- summary: 店铺装修的商品货架模块新增商品选择弹窗，复用后台商品列表服务搜索在售商品，展示商品名、ID、编码、价格和库存，选中后写回 `productShelf.props.productIds`；已选商品以标签展示并可移除，仍保留文本批量编辑。弹窗分页已在 `20260617-admin-decoration-product-picker-pagination` 补齐。

## E-20260617-003：后台装修结构化编辑器验证

- trace_id: 20260617-admin-decoration-structured-editor
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run typecheck` and `npm run build` in `YunxiBakeBot\web\admin`; `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py`; architecture rg checks; `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 店铺装修编辑器改为结构化表单
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论；`web/admin/dist/` 为 build 生成的忽略目录，按项目禁止递归删除规则未自动清理
- summary: 后台店铺装修页从单一 `Props JSON` 文本框升级为结构化表单，覆盖搜索、公告、轮播、商品货架、富文本、会员横幅、会员摘要和须知列表；保留高级 JSON 兜底，并扩展手机预览覆盖主要模块。

## E-20260617-002：小程序商品图片后端受控代理验证

- trace_id: 20260617-miniapp-image-proxy-chain
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_admin_featured_catalog_api.py tests/api/test_miniapp_catalog_api.py tests/service/test_miniapp_catalog.py tests/api/test_shop_operations_api.py tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/service/test_miniapp_order.py tests/service/test_admin.py`; `python -m py_compile app\api\miniapp_catalog.py app\service\miniapp_catalog.py tests\api\test_miniapp_catalog_api.py tests\service\test_miniapp_catalog.py`; architecture rg checks; miniapp static/type checks; admin typecheck
- result: pass
- related_logbook: 2026-06-17 - feat(catalog): 小程序商品图片改为后端受控代理
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 商品 API `imageUrl` 返回后端同域代理路径，小程序商品 service 统一补全 `API_BASE_URL`；新增 `/api/v1/miniapp/products/{product_id}/image` 按商品 ID 查询已上架商品图片并校验协议、图片类型和大小；测试覆盖代理成功、无图、缺失商品和非法协议拒绝。

## E-20260617-001：小程序商品 API 有赞图片透传验证

- trace_id: 20260617-miniapp-product-images-chain
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_admin_featured_catalog_api.py tests/api/test_miniapp_catalog_api.py tests/service/test_miniapp_catalog.py tests/api/test_shop_operations_api.py tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/service/test_miniapp_order.py tests/service/test_admin.py`; architecture rg checks; miniapp static/type checks; admin typecheck
- result: pass
- related_logbook: 2026-06-17 - feat(catalog): 小程序商品 API 透传有赞商品图片
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 商品目录仓储从 `youzan_products.image` 读取图片并挂载为 `image_url`，小程序商品 API 输出契约字段 `imageUrl`；服务级和 API 级测试覆盖商品列表、装修货架、主推商品和详情图片字段。

## E-20260616-017：后台主推商品页面浏览器保存 smoke

- trace_id: 20260616-admin-featured-browser-smoke
- generated_at: 2026-06-16
- evidence_type: screenshot
- file: `D:\Project\YunxiBakeBot\reports\ui\admin-featured-products-smoke.png`
- command: 使用临时 SQLite DB 启动本地后端 `127.0.0.1:7001`、后台 Vite `127.0.0.1:5173`、headless Chrome CDP `127.0.0.1:9223`；浏览器打开 `/admin/products/featured`，搜索 `烟测`，添加两条候选商品，保存主推款，并调用 `/api/v1/miniapp/products?featured=true` 核对小程序公开商品列表；随后运行商品/主推后端测试、分层红线搜索、小程序静态/type checks、后台 typecheck。
- result: pass
- related_logbook: 2026-06-16 - test(admin): 浏览器验证主推商品页面保存链路
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留截图和本地 smoke 日志；临时 SQLite DB 已逐个删除；本地服务已停止
- summary: 浏览器真实操作证明后台主推商品页面可搜索候选商品、添加主推、保存配置；保存后小程序 featured 商品接口按同一顺序返回 `烟测草莓奶油蛋糕`、`烟测芒果千层`。

## E-20260616-016：后台主推商品到小程序 featured 链路验证

- trace_id: 20260616-admin-featured-catalog-chain
- generated_at: 2026-06-16
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_admin_featured_catalog_api.py tests/api/test_miniapp_catalog_api.py tests/service/test_miniapp_catalog.py tests/api/test_shop_operations_api.py tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/service/test_miniapp_order.py tests/service/test_admin.py`; architecture rg checks; miniapp static/type checks; admin typecheck
- result: pass
- related_logbook: 2026-06-16 - test(catalog): 打通后台主推到小程序 featured 商品
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 新增跨路由测试证明后台 `/api/v1/admin/shop-config/featured-products` 保存主推商品并清理空白值后，后台商品列表 `featured_only=true` 和小程序 `/api/v1/miniapp/products?featured=true` 都按同一配置顺序返回主推商品。

## E-20260616-015：小程序商品目录 API 链路验证

- trace_id: 20260616-miniapp-catalog-api-chain
- generated_at: 2026-06-16
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_miniapp_catalog_api.py tests/service/test_miniapp_catalog.py tests/api/test_shop_operations_api.py tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/service/test_miniapp_order.py`; architecture rg checks; miniapp static/type checks; admin typecheck
- result: pass
- related_logbook: 2026-06-16 - test(catalog): 补小程序商品目录 API 链路验证
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 新增 `tests/api/test_miniapp_catalog_api.py`，证明小程序公开商品 API 可读取在售商品，装修货架 `ids` 按配置顺序返回并跳过无效/重复商品，后台主推标题配置可驱动 `featured=true`，商品详情可按有赞 item_id 读取。

## E-20260616-014：店铺运营配置 API 联动验证

- trace_id: 20260616-shop-operations-api-chain
- generated_at: 2026-06-16
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_shop_operations_api.py tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/service/test_miniapp_order.py`; `python -m py_compile tests\api\test_shop_operations_api.py`; architecture rg checks; miniapp/admin type checks
- result: pass
- related_logbook: 2026-06-16 - test(shop): 补店铺运营配置 API 联动验证
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 新增 API 路由级测试证明后台店铺运营配置接口会校验管理员 Token，保存店铺名称、客服微信、客服电话、营业时间、自提和配送说明后，小程序 `/api/v1/miniapp/shop-settings` 读取同一份公开配置。

## E-20260616-013：后台装修 API 路由级验证

- trace_id: 20260616-decoration-api-chain
- generated_at: 2026-06-16
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/service/test_miniapp_order.py`; `python -m py_compile tests\api\test_shop_page_config_api.py tests\service\test_shop_page_config.py`
- result: pass
- related_logbook: 2026-06-16 - test(decoration): 补装修 API 路由级验证
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 新增 API 路由级测试证明后台装修接口会校验管理员 Token，保存草稿后小程序仍读取旧 published 配置，发布后小程序读取最新页面配置。

## E-20260616-011：后台装修发布链路服务级验证

- trace_id: 20260616-decoration-publish-chain
- generated_at: 2026-06-16
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/service/test_shop_page_config.py tests/service/test_miniapp_order.py`; `python -m py_compile app\service\shop_page_config.py tests\service\test_shop_page_config.py`; architecture rg checks; miniapp/admin type checks
- result: pass
- related_logbook: 2026-06-16 - test(decoration): 验证装修草稿发布到小程序
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 新增服务级测试证明后台保存装修草稿不会影响小程序 published 配置；发布后小程序读取到最新商品货架配置；无草稿时可发布默认配置，保证初始化后小程序可渲染。

## E-20260616-012：后台装修发布链路浏览器烟测

- trace_id: 20260616-decoration-publish-chain
- generated_at: 2026-06-16
- evidence_type: screenshot
- file: `D:\Project\YunxiBakeBot\reports\ui\admin-decoration-publish-smoke.png`
- command: Chrome 远程调试打开 `/admin-v2/login?redirect=%2Fadmin-v2%2Fdecoration`，登录后在装修页修改商品货架标题、保存草稿、发布，并通过 API 核对小程序 published 配置
- result: pass
- related_logbook: 2026-06-16 - test(decoration): 验证装修草稿发布到小程序
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留浏览器截图；临时 Chrome profile 仅用于本次烟测
- summary: 浏览器真实操作证明后台装修编辑器可登录、可修改模块 JSON、可保存草稿、可发布；保存后小程序仍读取旧 published 配置，发布后小程序读取新标题。

## E-20260616-010：小程序页面静态一致性检查

- trace_id: 20260616-miniapp-static-page-check
- generated_at: 2026-06-16
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:miniapp`; `npm run typecheck` in `YunxiBakeMiniApp`; JSON parsing for miniapp config; `npm run typecheck` in `web/admin`
- result: pass
- related_logbook: 2026-06-16 - test(miniapp): 增加页面静态一致性检查
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 小程序页面四件套、路由常量、tabBar 跳转、WXML 事件绑定和顶层 data 引用检查通过；订单详情页返回订单列表已修正为 `switchTab`。

## E-20260616-009：订单履约完整状态链 API 验证

- trace_id: 20260616-order-status-chain-smoke
- generated_at: 2026-06-16
- evidence_type: api
- file: local command output (no persisted artifact)
- command: local HTTP smoke for miniapp order create, admin status updates, miniapp order detail/list reads
- result: pass
- related_logbook: 2026-06-16 - test(order): 验证履约完整状态链
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论；临时本地服务已停止
- summary: 订单 `mp_20260616210530_72f31260` 完成 `pending -> confirmed -> making -> delivering -> done` 状态链验证；小程序详情每一步读取到最新状态；非法 `pending -> done` 和 `done -> cancelled` 均被 400 拒绝。

## E-20260616-008：小程序订单状态联动 API 验证

- trace_id: 20260616-miniapp-admin-status-sync-smoke
- generated_at: 2026-06-16
- evidence_type: api
- file: local command output (no persisted artifact)
- command: local HTTP smoke for `/api/v1/miniapp/auth/login`, `/api/v1/miniapp/pages/home`, `/api/v1/miniapp/shop-settings`, `/api/v1/miniapp/orders`, `/api/v1/admin/orders/{order_id}/status`, `/api/v1/miniapp/orders/{order_id}`
- result: pass
- related_logbook: 2026-06-16 - test(miniapp): 验证小程序订单状态联动
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论；临时本地服务已停止
- summary: 本地创建小程序订单 `mp_20260616210101_c9e57450`，后台将状态从 `pending` 更新为 `confirmed`，小程序订单详情和列表均读取到 `confirmed`。

## E-20260616-007：后台订单与店铺配置交互验证

- trace_id: 20260616-admin-interaction-smoke
- generated_at: 2026-06-16
- evidence_type: screenshot
- file: `reports/ui/admin-order-detail-drawer-smoke.png`; `reports/ui/admin-order-confirmed-smoke.png`; `reports/ui/admin-shop-settings-save-smoke.png`
- command: Chrome DevTools smoke for `/admin/orders?status=pending` and `/admin/settings/shop`
- result: pass
- related_logbook: 2026-06-16 - test(admin): 验证订单履约与店铺配置交互
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留浏览器截图；临时本地服务已停止；店铺名称已恢复原值
- summary: 后台订单详情抽屉可打开，待确认订单可通过页面操作更新为已确认；店铺配置可通过页面保存，并已通过 API 恢复原店名“芸熙烘焙”。

## E-20260616-018：后台设置摘要 MiMo 字段与本地路由收口验证

- trace_id: 20260616-admin-overview-mvp
- generated_at: 2026-06-16
- evidence_type: command / screenshot
- file: `reports/ui/admin-overview-smoke.png`; `reports/ui/admin-settings-api-smoke.png`; `reports/ui/admin-orders-pending-smoke.png`
- command: `rg -n "webhookTokenConfigured|deepseek|DeepSeek" web/admin/src app/service/admin.py app/api/admin_config.py app/models/config.py`; `npm run typecheck` and `npm run build` in `web/admin`; `python -m py_compile` for miniapp/admin MVP modules; architecture rg checks; Chrome DevTools smoke for `/admin/overview`, `/admin/settings/api`, `/admin/orders?status=pending`
- result: pass
- related_logbook: 2026-06-16 - fix(admin): 收口设置摘要 MiMo 字段引用和后台本地路由
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留浏览器截图和命令结论；临时本地服务已停止
- summary: 后台概览不再引用已移除的有赞 webhook token 和 DeepSeek 字段；Vite dev server 不再把 `/admin` 代理到后端，后台 SPA 路由可正常打开；概览、API 设置和待确认订单深链通过浏览器渲染 smoke。

## 登记模板

```markdown
## E-YYYYMMDD-001：标题

- trace_id:
- generated_at:
- evidence_type: handoff | preflight | smoke | migration | seed | embedding | review | other
- file:
- command:
- result: pass | fail | partial
- related_logbook:
- related_adr:
- contains_sensitive_data: yes | no
- retention_note:
- summary:
```

______________________________________________________________________

## 当前证据

## E-20260617-047：后台店铺配置保存到小程序公开配置 smoke

- trace_id: 20260617-admin-shop-settings-smoke
- generated_at: 2026-06-17
- evidence_type: smoke
- file: `D:\Project\YunxiBakeBot\reports\ui\shop-settings-smoke.png`
- command: `npm run smoke:shop-settings`; `npm run smoke:orders-confirmation`; `npm run smoke:products-active-toggle`; `npm run smoke:decoration-product-picker`; `npm run check:shop-settings`; `npm run check:products`; `npm run check:orders`; `npm run check:decoration`; `npm run typecheck` in `web/admin`; `python -m pytest --no-cov tests/api/test_shop_operations_api.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 店铺配置保存到小程序公开配置 smoke 跑通
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留浏览器成功截图和命令结论；临时 SQLite DB、WAL/SHM 和失败截图已逐个清理
- summary: 浏览器真实操作后台店铺配置页填写并保存店铺名称、电话、微信、营业时间、自提和配送说明后，小程序 `GET /api/v1/miniapp/shop-settings` 读取到同一份公开配置；订单确认、商品上下架、装修选品 smoke 顺序复跑通过，确认共享 smoke 工具调整没有破坏既有链路。

## E-20260616-006：后台商城经营台概览验证

- trace_id: 20260616-admin-overview-mvp
- generated_at: 2026-06-16
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run typecheck` in `web/admin`
- result: pass
- related_logbook: 2026-06-16 - feat(admin): 将后台概览改造成商城经营台
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时脚本文件
- summary: 后台概览重构后通过类型检查，订单列表 query 深链联动可用。

## E-20260617-048：小程序客服主动转人工接口验证

- trace_id: 20260617-miniapp-chat-transfer
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest -o addopts="" tests/service/test_miniapp_chat.py tests/api/test_miniapp_chat_api.py tests/test_lifespan_routes_services.py`; `python -m py_compile app\api\miniapp_chat.py app\service\miniapp_chat.py app\lifespan_services.py tests\service\test_miniapp_chat.py tests\api\test_miniapp_chat_api.py tests\test_lifespan_routes_services.py`; `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 用户主动转人工客服
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告
- summary: 小程序主动转人工接口复用既有转人工工单和后台队列；目标后端测试 13 passed，后端编译和小程序静态/类型检查均通过。

## E-20260616-005：小程序订单详情接口类型与分层验证

- trace_id: 20260616-miniapp-order-detail-mvp
- generated_at: 2026-06-16
- evidence_type: smoke
- file: local command output (no persisted report)
- command: `python -m py_compile app\service\miniapp_order.py app\api\miniapp_orders.py`; `npm run typecheck` in `YunxiBakeMiniApp`; architecture rg checks
- result: pass
- related_logbook: 2026-06-16 - feat(miniapp): 新增小程序订单详情接口
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时脚本文件
- summary: 小程序订单详情接口和页面通过类型/编译检查，API 层未直接穿透 repository，service 层未直连数据库。

## E-20260616-004：店铺运营配置类型与分层验证

- trace_id: 20260616-shop-operations-config-mvp
- generated_at: 2026-06-16
- evidence_type: smoke
- file: local command output (no persisted report)
- command: `python -m py_compile app\models\config.py app\service\admin.py app\api\admin_config.py`; `npm run typecheck` in `web/admin`; `npm run typecheck` in `YunxiBakeMiniApp`; architecture rg checks
- result: pass
- related_logbook: 2026-06-16 - feat(miniapp/admin): 接入店铺运营配置 MVP
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时脚本文件
- summary: 店铺运营配置后端 API、后台表单和小程序读取层均通过类型/编译检查，架构红线搜索无输出。

## E-20260616-003：后台订单履约状态服务级验证

- trace_id: 20260616-admin-order-fulfillment-mvp
- generated_at: 2026-06-16
- evidence_type: smoke
- file: local command output (no persisted report)
- command: `python -m py_compile app\repository\order_repo.py app\service\miniapp_order.py app\api\admin_orders.py`; `npm run typecheck` in `web/admin`; inline Python service smoke for `MiniappOrderService.update_admin_order_status`
- result: pass
- related_logbook: 2026-06-16 - feat(admin): 补齐小程序订单履约处理 MVP
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时脚本文件
- summary: 后台订单详情和状态更新代码可编译，后台前端类型检查通过，服务级 smoke 验证待确认可切换到已确认且非法越级切换会被拒绝。

## E-20260616-002：小程序完整 MVP 本地 API smoke

- trace_id: 20260616-miniapp-mvp-smoke
- generated_at: 2026-06-16
- evidence_type: smoke
- file: local command output (no persisted report)
- command: `python -m uvicorn app.main:app --host 127.0.0.1 --port 7010` 后，用 `Invoke-RestMethod` 依次验证 `/health`、`/api/v1/miniapp/auth/login`、`/api/v1/miniapp/pages/home`、`/api/v1/miniapp/products`、`/api/v1/miniapp/chat/messages`、`/api/v1/miniapp/orders`、`/api/v1/admin/orders`
- result: pass
- related_logbook: 2026-06-16 - feat(miniapp): 接入小程序登录会话 MVP / feat(miniapp): 接入小程序客服消息 API / feat(miniapp/admin): 接入小程序订单草稿和后台订单列表
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留 smoke 结论，不保留临时日志文件
- summary: 登录、装修、客服、订单和后台订单列表接口联通成功；本地商品表未命中示例商品 ID，商品接口返回空列表，说明前端仍需 Mock 兜底。

## E-20260616-001：有赞客服托管连通性测试交接快照

- trace_id: YZ-HOSTING-CONNECTIVITY-20260616
- generated_at: 2026-06-16
- evidence_type: handoff
- file: reports/harness/youzan-hosting-connectivity-20260616.md
- command: `python scripts/harness_snapshot.py --trace-id YZ-HOSTING-CONNECTIVITY-20260616 --goal "有赞客服托管与现有 AI 客服收发连通性测试" --status completed --output reports/harness/youzan-hosting-connectivity-20260616.md`
- result: pass
- related_logbook: 2026-06-16 - feat(youzan): 接入客服托管收发连通性测试
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留本次连通性测试与分层边界决策依据，便于后续有赞订阅联调和回归排障。
- summary: 记录有赞客服托管消息分流、托管回复 API、异步 webhook 测试与数据库零改造判断。

## E-20260620-001：有赞客户正式迁移与后验核对闭环

- trace_id: 20260620-customer-import-pipeline
- generated_at: 2026-06-20
- evidence_type: handoff/runbook/command
- file: `D:\Project\YunxiBakeBot\reports\harness\customer-import-pipeline-20260620.md`; `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-formal-import-runbook.md`; `D:\Project\YunxiBakeBot\scripts\import_youzan_customers.py`; `D:\Project\YunxiBakeBot\scripts\verify_youzan_customer_import.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_import_youzan_customers.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_verify_youzan_customer_import.py`
- command: `python scripts/import_youzan_customers.py --customer-csv "docs\有赞导出\客户数据_0002000408539943.csv" --orders-csv "docs\有赞导出\订单数据.csv" --db-path "data\bot.db" --tenant-id "yunxi" --source-batch-id "youzan-customer-20260620-full" --apply --json --output "reports\youzan-customer-import-apply-{timestamp}.json"`; `python scripts/verify_youzan_customer_import.py --db-path "data\bot.db" --tenant-id "yunxi" --source-batch-id "youzan-customer-20260620-full" --import-report "reports\youzan-customer-import-apply-20260620-120000.json" --json --output "reports\youzan-customer-import-verify-{timestamp}.json"`; `python scripts/harness_snapshot.py --trace-id 20260620-customer-import-pipeline --goal "接着做" --status completed --output reports/harness/customer-import-pipeline-20260620.md`
- result: pass
- related_logbook: 2026-06-20 - feat(customer): 新增正式迁移后批次核对脚本; 2026-06-20 - docs(customer): 补齐正式客户迁移执行 runbook; 2026-06-20 - feat(customer): 新增正式有赞客户迁移入口脚本
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留正式迁移、后验核对与交接快照的摘要索引；实际 JSON 报告与数据库快照按 reports/ 目录管理，不在索引中重复记录敏感内容。
- summary: customer 域正式迁移已经从“审计”推进到“dry-run / apply / 后验核对 / 交接快照”四段闭环；交接快照与证据索引已可直接用于后续补跑和换手。

## E-20260620-027：Platform 领域迁移盘点

- trace_id: 20260620-platform-domain-migration-inventory
- generated_at: 2026-06-20
- evidence_type: architecture-inventory
- file: `D:\Project\YunxiBakeBot\docs\architecture\platform-domain-migration-inventory.md`; `D:\Project\YunxiBakeBot\docs\architecture\project-boundaries.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `rg -n "platform-domain-migration-inventory|Platform 领域迁移盘点|20260620-platform-domain-migration-inventory" docs README.md LOGBOOK.md 项目进度与配置清单.md`; `rg "from app\.repository" app/api -g "*.py"`; `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service -g "*.py"`; `rg "from app\.(service|repository|api)" app/models -g "*.py"`; `python scripts/check_project.py`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 补齐 Platform 领域迁移盘点
- related_adr: ADR 0002
- contains_sensitive_data: no
- retention_note: 仅登记盘点文档和本地验证命令结论，不包含客户数据或导出 CSV。
- summary: 确认 `app/service/miniapp_*.py` 已基本退为兼容 facade，真实实现主要落在 canonical 领域；下一阶段优先迁测试和内部依赖，地址域采用 repo/model 别名过渡，不改外部路径、请求头或数据库表名。

## E-20260620-028：测试依赖迁移到 canonical 服务

- trace_id: 20260620-platform-test-dependency-migration
- generated_at: 2026-06-20
- evidence_type: test-architecture-sweep
- file: `D:\Project\YunxiBakeBot\tests\service\test_miniapp_order.py`; `D:\Project\YunxiBakeBot\tests\api\test_admin_order_api.py`; `D:\Project\YunxiBakeBot\tests\api\test_miniapp_payment_api.py`; `D:\Project\YunxiBakeBot\tests\api\test_miniapp_chat_api.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `rg -n "from app\.service\.miniapp_|app\.service\.miniapp_|MiniappPaymentService|MiniappOrderInventoryService|MiniappOrderScheduleService|MiniappOrderSerializationService|MiniappOrderService|MiniappCatalogService|MiniappAddressService|MiniappChatService|MiniappAuthService" tests app -g "*.py"`; `python scripts/check_project.py`
- result: pass
- related_logbook: 2026-06-20 - test(architecture): 迁移测试依赖到 canonical 服务
- related_adr: ADR 0002
- contains_sensitive_data: no
- retention_note: 仅登记测试依赖迁移和本地验证命令结论，不包含客户数据或导出 CSV。
- summary: 订单、支付和会话 API 相关测试已改为依赖 canonical 服务名；兼容层引用只保留在红线测试样例和 `app/service/miniapp_*.py` facade 中。

## E-20260620-029：地址域仓储和模型 canonical 命名收口

- trace_id: 20260620-customer-address-canonical-repo
- generated_at: 2026-06-20
- evidence_type: refactor/test
- file: `D:\Project\YunxiBakeBot\app\models\customer_address.py`; `D:\Project\YunxiBakeBot\app\repository\customer_address_repo.py`; `D:\Project\YunxiBakeBot\app\repository\customer_address_audit_repo.py`; `D:\Project\YunxiBakeBot\app\service\customer\address.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\service\test_miniapp_address.py tests\api\test_miniapp_address_api.py tests\api\test_admin_address_api.py tests\test_lifespan_routes_services.py -q --tb=short --no-cov`; `rg -n "MiniappAddress|miniapp_address_repo|miniapp_address_audit_repo|models\.miniapp_address|repository\.miniapp_address" app tests -g "*.py"`; `python scripts/check_project.py`
- result: pass
- related_logbook: 2026-06-20 - refactor(customer): 地址域仓储和模型切到 canonical 命名
- related_adr: ADR 0002
- contains_sensitive_data: no
- retention_note: 仅登记地址域命名收口和本地验证命令结论，不包含客户数据或导出 CSV。
- summary: 地址域新增 customer 语义模型和仓储，旧 `MiniappAddress*` 模块退为兼容导出；数据库表名、历史迁移文件和 `/api/v1/miniapp/addresses` 路径保持不变。

## E-20260620-030：lifespan 兼容 key 集中管理

- trace_id: 20260620-lifespan-legacy-key-aliases
- generated_at: 2026-06-20
- evidence_type: refactor/test
- file: `D:\Project\YunxiBakeBot\app\lifespan_services.py`; `D:\Project\YunxiBakeBot\app\main.py`; `D:\Project\YunxiBakeBot\tests\test_lifespan_routes_services.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\test_lifespan_routes_services.py -q --tb=short --no-cov`; `rg -n 'miniapp_.*service|miniapp_.*repo|miniapp-auth-service|miniapp-address-service|miniapp-catalog-service|miniapp-order-service|miniapp-chat-service' app tests -g '*.py'`; `python scripts/check_project.py`
- result: pass
- related_logbook: 2026-06-20 - refactor(lifespan): 集中管理兼容期旧 key
- related_adr: ADR 0002
- contains_sensitive_data: no
- retention_note: 仅登记 `lifespan` 兼容 key 收口和本地验证命令结论，不包含客户数据或导出 CSV。
- summary: `lifespan` 真实装配优先 canonical key，旧 `miniapp_*` service/repo key 通过集中 alias map 保留兼容，并由测试确认别名指向 canonical 对象。

## E-20260620-031：前台会话渠道常量收口

- trace_id: 20260620-storefront-conversation-constants
- generated_at: 2026-06-20
- evidence_type: refactor/test
- file: `D:\Project\YunxiBakeBot\app\constants\storefront.py`; `D:\Project\YunxiBakeBot\app\service\conversation\storefront.py`; `D:\Project\YunxiBakeBot\tests\service\test_miniapp_chat.py`; `D:\Project\YunxiBakeBot\tests\api\test_miniapp_chat_api.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\service\test_miniapp_chat.py tests\api\test_miniapp_chat_api.py -q --tb=short --no-cov`; `rg -n '小程序用户主动请求人工客服|channel_msg_id=.*miniapp:' app tests -g '*.py'`; `python scripts/check_project.py`
- result: pass
- related_logbook: 2026-06-20 - refactor(conversation): 收口前台会话渠道常量
- related_adr: ADR 0002
- contains_sensitive_data: no
- retention_note: 仅登记前台会话常量收口和本地验证命令结论，不包含客户数据或导出 CSV。
- summary: `StorefrontConversationService` 不再直接依赖 `miniapp` 常量或硬编码消息前缀；兼容期内 channel、消息 ID 前缀、demo 用户和默认转人工原因保持现有值不变。

## E-20260620-032：Platform 架构收口 P1-P3

- trace_id: 20260620-platform-architecture-closure
- generated_at: 2026-06-20
- evidence_type: refactor/test/doc-sweep
- file: `D:\Project\YunxiBakeBot\app\constants\storefront.py`; `D:\Project\YunxiBakeBot\app\service\order\application.py`; `D:\Project\YunxiBakeBot\app\api\miniapp_orders.py`; `D:\Project\YunxiBakeBot\tests\helpers\catalog_seed.py`; `D:\Project\YunxiBakeBot\docs\architecture\platform-domain-migration-inventory.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests\service\test_catalog.py tests\service\test_catalog_item_base_category.py tests\service\test_order.py tests\service\test_customer_address.py tests\service\test_storefront_conversation.py tests\api\test_miniapp_chat_api.py tests\api\test_miniapp_order_api.py tests\api\test_miniapp_address_api.py -q --tb=short --no-cov`; architecture `rg` checks; `rg -n "from app\.constants\.miniapp" app\service\order app\service\channels\storefront app\api\miniapp_chat.py app\api\miniapp_orders.py app\api\miniapp_addresses.py -g "*.py"`; `rg -n "tests\.helpers\.miniapp_catalog_seed" tests\service -g "*.py"`; `python scripts/check_project.py`
- result: pass
- related_logbook: 2026-06-20 - refactor(platform): 完成 Platform 架构收口 P1-P3
- related_adr: ADR 0002
- contains_sensitive_data: no
- retention_note: 仅登记架构收口与本地验证命令结论，不包含客户数据或导出 CSV。
- summary: 订单域、前台认证服务和 MiniApp API 内部默认用户已切到 storefront 常量；服务测试与商品测试 helper 已迁到 canonical 领域语义；旧 MiniApp API 契约、请求头、历史表名、迁移文件和微信平台配置保持不变。

## E-20260621-006：前台渠道 API 目录切换 P4

- trace_id: 20260621-storefront-api-directory
- generated_at: 2026-06-21
- evidence_type: refactor/test/guardrail
- file: `D:\Project\YunxiBakeBot\app\api\channels\storefront\auth.py`; `D:\Project\YunxiBakeBot\app\api\channels\storefront\orders.py`; `D:\Project\YunxiBakeBot\app\api\miniapp_orders.py`; `D:\Project\YunxiBakeBot\app\lifespan_routes.py`; `D:\Project\YunxiBakeBot\scripts\check_project.py`; `D:\Project\YunxiBakeBot\tests\test_red_line_rules.py`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests/test_red_line_rules.py tests/test_lifespan_routes_services.py tests/api/test_miniapp_auth_api.py tests/api/test_miniapp_catalog_api.py tests/api/test_miniapp_chat_api.py tests/api/test_miniapp_order_api.py tests/api/test_miniapp_payment_api.py tests/api/test_miniapp_address_api.py -q --tb=short --no-cov`; `python -m compileall app\api\channels app\api\miniapp_auth.py app\api\miniapp_catalog.py app\api\miniapp_addresses.py app\api\miniapp_chat.py app\api\miniapp_orders.py app\api\miniapp_payments.py app\lifespan_routes.py`; `python scripts/check_project.py --skip-tests`; `python scripts/check_project.py`; MiniAPP `npm run check:miniapp`; MiniAPP `npm run typecheck`
- result: pass
- related_logbook: 2026-06-21 - refactor(api): 完成前台渠道 API 目录切换 P4
- related_adr: ADR 0002
- contains_sensitive_data: no
- retention_note: 仅登记 API 目录切换和本地验证命令结论，不包含客户数据或导出 CSV。
- summary: `app/api/channels/storefront/*` 承载前台 API 真实实现，`app/api/miniapp_*.py` 退为兼容导出，`lifespan` 装配优先使用 canonical router；新增红线防止 MiniApp API 兼容文件重新承载真实 FastAPI router。外部 `/api/v1/miniapp/*` 和 `x-miniapp-user-id` 保持不变。

## E-20260703-009：企微智能机器人 URL 回调改为 stream 回复

- trace_id: 20260703-wecom-aibot-stream-reply
- generated_at: 2026-07-03
- evidence_type: production-fix/test/smoke
- file: `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_callback.py`; `D:\Project\YunxiBakeBot\app\service\wecom\intelligent_bot_dispatcher.py`; `D:\Project\YunxiBakeBot\tests\api\test_wecom_intelligent_bot_callback_api.py`; `D:\Project\YunxiBakeBot\docs\architecture\wecom-intelligent-bot-tools.md`; `D:\Project\YunxiBakeBot\LOGBOOK.md`
- command: `python -m pytest tests/api/test_wecom_intelligent_bot_callback_api.py tests/api/test_wecom_intelligent_bot_plugin_api.py tests/service/test_wecom_intelligent_bot_tool_response_and_format.py -q --no-cov`; `python -m ruff check app/service/wecom/intelligent_bot_callback.py app/service/wecom/intelligent_bot_dispatcher.py tests/api/test_wecom_intelligent_bot_callback_api.py`; `python scripts/check_project.py --skip-tests`; production `python3 -m compileall -q app/service/wecom/intelligent_bot_callback.py app/service/wecom/intelligent_bot_dispatcher.py`; production `/ready`; production encrypted callback probe
- result: pass
- related_logbook: 2026-07-03 - fix(wecom): 智能机器人消息回调用 stream 被动回复
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅登记命令、状态码、回复类型和备份目录，不包含企微密钥、员工原文或回复正文。
- summary: URL 回调从 `msgtype=text` 改为一次性 `msgtype=stream`、`finish=true` 的被动回复，并增加不含正文的路由观测日志；生产加密探针确认返回 200、签名通过、解密后为 stream 回复。
