# 项目快速参考

______________________________________________________________________

## 关键路径速查

| 需求 | 文件 |
|------|------|
| AI 对话入口 | `app/service/chat.py` |
| System Prompt 构建 | `app/service/llm/prompt.py` |
| Function Calling 调度 | `app/service/llm/functions.py` |
| 意图识别 | `app/service/llm/intent.py` |
| RAG 检索 | `app/service/knowledge_retriever.py` |
| 向量搜索 | `app/service/embedding_search.py` |
| 有赞 Webhook 入口 | `app/api/integrations/youzan_webhook.py` |
| 有赞事件分发 | `app/service/youzan/event_handler.py` |
| 管理后台路由 | `app/api/admin/root.py` |
| 新后台前端入口 | `app/api/admin/frontend.py` |
| 新后台前端工程 | `web/admin/` |
| 知识配置后台 | `app/api/admin/knowledge.py` |
| 数据观察台后台 | `app/api/admin/observability.py` |
| 数据库初始化 | `app/database.py` |
| 商品实时刷新 | `app/service/llm/function_tool_product.py` |
| 版本号（唯一来源） | `VERSION` |
| 版本同步门禁 | `scripts/sync_version.py` |
| LOGBOOK 自动追加 | `scripts/append_logbook.py` |
| 企业微信告警 | `app/service/alerting.py` |

---

## 测试与部署速查

```bash
# 全量测试
python -m pytest tests/ -q

# 仅跑红线规则自测
python -m pytest tests/test_red_line_rules.py -q --tb=short

# 本地启动
uvicorn app.main:app --host 127.0.0.1 --port 7001 --reload

# 健康检查
curl http://127.0.0.1:7001/health  # 预期: {"status":"ok","version":"0.1.0"}

# 知识种子导入（仅 FAQ / 规则 / 话术）
python scripts/seed_baseline_knowledge.py
python scripts/seed_baseline_knowledge.py --apply

# 远程重启
ssh root@47.94.102.250 "systemctl restart yunxibakebot && systemctl is-active yunxibakebot"
```

---

## 架构分层

```
api/ → service/ → repository/ → models/
```

- `api/`：HTTP 路由层（FastAPI Router），接收请求、返回响应
- `service/`：业务逻辑层，编排 repository 和外部服务调用
- `repository/`：数据访问层，封装 SQL 操作和数据持久化
- `models/`：数据模型层，纯 Pydantic 模型，不依赖任何上层模块

禁止任何层级向上穿透调用。

---

## Harness 运行口径

- 中大型任务先分配 `trace_id`，再按 `docs/harness-engineering/core/verification-matrix.md` 选验证。
- 需要交接时优先用 `scripts/harness_snapshot.py`，不要只留聊天记录。
- 需要长期记忆的错误先写 `docs/harness-engineering/core/mistake-ledger.md`，再补测试、脚本、pre-commit、AGENTS 或 Skill 中至少一类防线。
