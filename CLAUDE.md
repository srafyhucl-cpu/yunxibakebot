# CLAUDE.md — 芸熙烘焙 AI 客服

## 项目概述

芸熙烘焙 AI 客服系统，覆盖 3 个渠道（有赞小程序、企微 1 对 1、企微群），使用 DeepSeek API 作为 LLM 大脑，SQLite 存储，单服务器部署。

## 技术栈

- Python 3.11+ / FastAPI / Uvicorn
- SQLite (aiosqlite, WAL mode)
- DeepSeek (OpenAI 协议, openai SDK)
- Nginx (HTTPS 反向代理)
- 域名: hclstudio.cn (已备案)
- 管理后台: yunxi.hclstudio.cn/admin (子域名, 免费)

## 核心设计决策

### 1. 渠道接入顺序
小程序(有赞) → 企微 1 对 1 → 企微群，逐步接入。AI 对话核心复用同一套。

### 2. 人工介入形式
- **小程序**: 客服在管理后台网页回复
- **企微 1 对 1**: 员工在企微客户端直接回复（AI 自动让路，最自然）
- **企微群**: 店长群内直接回复

### 3. 企微冲突处理
AI 回复后延迟 3-5 秒发送，检测员工是否已回复。已回复 → AI 取消，未回复 → AI 发送。

### 4. 下单流程
AI 提取订单信息 → 发给客户确认 → 客户确认 → 订单入库 → 店员审核生产。AI 不自动落单。

### 5. 滑动窗口
对话历史取最近的消息，累计 ≤ 16K tokens，超出部分截断并插入截断提示。

### 6. Tool Calling 限制
最多 3 轮连续 function call，超限输出兜底回复。

## 模块结构

```
app/
├── main.py              # FastAPI app
├── config.py            # 配置 (pydantic-settings)
├── database.py          # SQLite + 建表
├── models/              # Pydantic 模型
├── repository/          # 数据访问层
├── service/
│   ├── llm/             # DeepSeek 调用 + Function Calling
│   ├── youzan/          # 有赞 Webhook + API
│   ├── wecom/           # 企微回调 + API
│   ├── chat.py          # 核心对话循环
│   ├── session_manager.py
│   ├── transfer_manager.py
│   └── knowledge_retriever.py
└── api/                 # 路由
    ├── webhook.py
    └── admin.py
```

## 关键约定

- 所有 DeepSeek 调用走 OpenAI 协议 (openai SDK)
- 数据库使用 raw SQL + aiosqlite，不用 ORM
- 异步优先 (async/await)
- 配置走环境变量 + .env，不硬编码
- 日志走标准 logging 或 loguru

## 依赖

fastapi, uvicorn, openai, aiosqlite, httpx, pydantic, pydantic-settings

## 部署

- Systemd 管理进程
- Nginx 反向代理 + Let's Encrypt HTTPS
- 端口: 443 (外部) → 7001 (内部 FastAPI)

## 常用开发命令

```bash
# 启动服务（热重载）
uvicorn app.main:app --host 127.0.0.1 --port 7001 --reload

# 运行场景测试
python scripts/test_scenarios.py

# 运行意图分类测试
python scripts/test_intents.py

# 知识库种子数据导入
python scripts/seed_knowledge.py

# 商品数据校验
python scripts/validate_products.py
```

## AI 自动化行为守则（预提交阻断）

每次执行 `/commit` 或 `git commit` 前，必须触发以下静态红线审查，任一未通过则阻断提交：

### 红线审查项

1. **单引号检查**：新增/修改的代码中禁止使用单引号 `'`（SQL 语句内部字符串和 f-string 内部闭环除外），普通字符串、字典键名、日志一律使用双引号 `"`。
2. **Optional/Union 检查**：禁止隐式引入 `typing.Optional` 或 `typing.Union`，一律改写为 `X | None` 或 `X | Y`。
3. **TODO 占位符检查**：代码中禁止存在 `# TODO` 或未实现的业务占位符（如返回 `"待实现"` 的 stub 函数）。
4. **LOGBOOK.md 同步检查**：本轮修改必须在 `LOGBOOK.md` 中追加日志记录，未记录则阻断提交。
5. **测试验证**：涉及核心逻辑的修改，需在提交前运行对应测试验证通过。

### 审查流程

```bash
# 1. 检查单引号（排除 SQL 和 f-string）
git diff --cached -- '*.py' | grep "'" | grep -v "sql|f'" || true

# 2. 检查 Optional/Union
git diff --cached -- '*.py' | grep -E "Optional\[|Union\[" && echo "ERROR: 禁止使用 Optional/Union" && exit 1

# 3. 检查 TODO
git diff --cached -- '*.py' | grep "# TODO" && echo "ERROR: 存在未完成的 TODO" && exit 1

# 4. 检查 LOGBOOK.md 是否更新
git diff --cached -- LOGBOOK.md | grep "+" || echo "WARNING: LOGBOOK.md 未更新"
```
