# 芸熙烘焙 AI 客服 — AI Agent 工作规范

> 本文件供所有 AI coding agent（Devin、Claude、Cascade 等）在进入本项目时**首先阅读**。  
> 以下规范优先级高于 agent 的默认行为。

______________________________________________________________________

## 零、Skill 触发原则（最高优先级）

> 来自 `using-superpowers`：**只要有 1% 的可能性某个 Skill 适用，就必须调用它。**  
> 不允许用"任务太简单"、"我记得规范"、"先看代码再说"来跳过 Skill 调用。

______________________________________________________________________

## 一、启动检查清单（每次任务开始前必须执行）

在分析代码、回答问题或动手修改前，先完成以下步骤：

### Step 1：新功能 / 新需求 → 先用 brainstorming

凡是新增功能、新 API 端点、新对话逻辑、新 UI 组件，**必须先调用 `brainstorming` skill**，完成需求确认和方案设计后再动代码。

> 禁止跳过：即使需求"看起来很简单"，brainstorming 也是必须的——简单需求最容易因假设错误造成返工。

### Step 2：识别涉及的代码范围 → 调用对应 Guard Skill

| 涉及范围 | 必须调用的 Skill |
|---------|----------------|
| `app/api/` / `app/service/` / `app/repository/` / `app/models/` 任意一层 | **yunxi-architecture-guard** |
| `app/service/llm/`（Prompt、Function Calling、意图识别、对话循环） | **yunxi-llm-guard** |
| 任意 `.py` 文件（新增内容 / 修改函数 / 新增类） | **yunxi-file-size-guard** |
| 代码 Review / 发现命名混乱 / 魔法数字 / 函数过长 | **yunxi-clean-code-guard** |

> ⚠️ **不允许跳过**：即使任务看起来很小，只要涉及上表中的文件范围，就必须先调用 Skill。

### Step 3：读取 LOGBOOK.md 最新条目

快速扫描 `LOGBOOK.md` 前 30 行，了解最近一次变更的上下文，避免重复工作或与已有设计冲突。

### Step 4：确认修改范围不跨越架构边界

参考 **yunxi-architecture-guard** 中的分层规则：

```
api/ → service/ → repository/ → models/
```

禁止任何层级向上穿透调用。

______________________________________________________________________

## 二、编码红线（违反即阻断，不允许例外）

以下规则由 `pre-commit` 自动检查，违反会导致 commit 失败：

| 红线 | 说明 |
|------|------|
| 禁止 `Optional[X]` / `Union[X, Y]` | 使用 `X \| None` / `X \| Y` |
| 禁止 `# TODO` 占位符 | 要么实现，要么删除 |
| 禁止 `SELECT *` | 必须明确列出字段 |
| 禁止 `api/` 直接导入 `repository/` | 必须经过 `service/` |
| 禁止 `service/` 直接调用 `aiosqlite` | 必须经过 `repository/` |
| 禁止 `models/` 引用上层模块 | `models/` 只依赖标准库和 pydantic |
| 禁止 SQL f-string 拼接 | 必须使用 `?` 参数化绑定 |
| 禁止静默吞异常（`except: pass`） | 至少记录 `logger.error` |
| 禁止 `print()` 调试 | 使用 `logger.debug()` |
| 禁止硬编码密钥/Token | 通过 `app/config.py` 的 `get_settings()` 获取 |

______________________________________________________________________

## 三、提交收口规范（每次提交前必须完成）

按顺序执行，**不可跳过或乱序**：

1. **调用相关 Guard Skill** 确认代码符合规范
2. **更新 `LOGBOOK.md`**（在顶部追加本轮条目，格式见 `.windsurf/workflows/commit.md` 第 4.1 步）
3. **更新 `项目进度与配置清单.md`**（修改"最后更新"日期 + 已完成功能 + 已知问题状态，详见第 4.2 步）
4. **运行测试**：`python -m pytest tests/ -q`
5. **git add + commit**（pre-commit 会自动检查 LOGBOOK 和进度文档是否已暂存）
6. **推送到两个远端**：`git push origin master && git push server master`
7. **重启服务器**：`ssh root@47.94.102.250 "systemctl restart yunxibakebot"`

> 📄 完整格式参见 `.windsurf/workflows/commit.md`

______________________________________________________________________

## 四、项目关键路径速查

| 需求 | 文件 |
|------|------|
| AI 对话入口 | `app/service/chat.py` |
| System Prompt 构建 | `app/service/llm/prompt.py` |
| Function Calling 调度 | `app/service/llm/functions.py` |
| 意图识别 | `app/service/llm/intent.py` |
| RAG 检索 | `app/service/knowledge_retriever.py` |
| 向量搜索 | `app/service/embedding_search.py` |
| 有赞 Webhook 入口 | `app/api/webhook.py` |
| 有赞事件分发 | `app/service/youzan/event_handler.py` |
| 管理后台路由 | `app/api/admin.py` |
| 知识配置后台 | `app/api/admin_knowledge.py` |
| 数据库初始化 | `app/repository/database.py` |
| 商品实时刷新 | `app/service/llm/function_tool_product.py` |

______________________________________________________________________

## 五、Skill 调用速查

### 5.1 项目 Guard Skill（修改代码前必须调用）

| 场景 | 调用命令 |
|------|---------|
| 修改任意分层代码 | `skill invoke yunxi-architecture-guard` |
| 修改 LLM/Prompt/意图 | `skill invoke yunxi-llm-guard` |
| 新增/修改 `.py` 文件 | `skill invoke yunxi-file-size-guard` |
| 代码审查/发现质量问题 | `skill invoke yunxi-clean-code-guard` |

### 5.2 全局 Skill（按场景引入）

| 场景 | Skill | 说明 |
|------|-------|------|
| **新功能 / 新需求设计** | `brainstorming` | 探索需求、提 2-3 方案、用户确认后再实现；禁止跳过 |
| **查阅外部 API 文档**（有赞、DeepSeek、微信） | `defuddle` | 清洁提取网页正文，去噪省 token，替代 WebFetch |
| **创建或改进 Guard Skill** | `skill-creator` | 草稿 → 测试 → 迭代，优化 description 触发精度 |
| **向飞书发送开发通知**（部署结果、生产告警） | `lark-im` | 推送消息到开发群或个人 |
| **Skill 发现习惯建立** | `using-superpowers` | 任务开始前查找可用 skill 的元协议 |

### 5.3 工作流

| 场景 | 工作流 |
|------|-------|
| 全流程收口检查 | `/check` |
| 代码 Review | `/review` |
| 提交 | `/commit` |
| Skill 同步更新 | `/sync-skills` |

______________________________________________________________________

## 六、测试与部署速查

```bash
# 全套测试
python -m pytest tests/ -q

# 本地启动
uvicorn app.main:app --host 127.0.0.1 --port 7001 --reload

# 健康检查
curl http://127.0.0.1:7001/health  # 预期: {"status":"ok","version":"0.1.0"}

# 知识种子导入（仅 FAQ / 规则 / 话术）
python scripts/seed_knowledge.py

# 远程重启
ssh root@47.94.102.250 "systemctl restart yunxibakebot && systemctl is-active yunxibakebot"
```
