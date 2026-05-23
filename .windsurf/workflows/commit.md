---
description: 开发任务收口工作流，用于芸熙烘焙 AI 客服项目的任务完成检查、LOGBOOK 更新和代码提交
---


# 开发任务收口工作流

## 触发场景

当一次开发任务进入收尾阶段时使用此工作流，确保交付闭环符合项目规范。

## 收口检查清单

### 1. 代码红线自查

在提交前逐项检查：

```powershell
# 检查 Optional/Union（必须零输出）
git diff --cached -- "*.py" | Select-String "Optional\[|Union\["

# 检查 TODO 占位符（必须零输出）
git diff --cached -- "*.py" | Select-String "# TODO"

# 检查单引号字符串（人工判断，SQL 和 f-string 内部除外）
git diff --cached -- "*.py" | Select-String "= '"
```

- **任意一项有输出 → 立即修复，不得提交**

### 2. 测试验证

根据修改范围选择性运行：

```powershell
# 场景测试（覆盖意图识别、对话流）
python scripts/test_scenarios.py

# 意图识别测试
python scripts/test_intents.py

# 商品数据校验（修改了知识库时运行）
python scripts/validate_products.py
```

### 3. 服务启动验证

确认服务能正常启动：

```powershell
# 启动服务
uvicorn app.main:app --host 127.0.0.1 --port 7001 --reload

# 健康检查
curl http://127.0.0.1:7001/health
```

- 预期响应：`{"status": "ok", "version": "0.1.0"}`

### 4. 项目文档强制更新（pre-commit 自动拦截）

> **本步骤已有 pre-commit hook 自动检查**（`scripts/check_logbook.py`）。  
> 凡暂存区含 `.py / .html / .css / .js` 文件，以下两份文档必须同时在暂存区，否则 commit 被拦截。  
> 纯配置/格式修正时可用 `SKIP_LOGBOOK_CHECK=1 git commit ...` 临时跳过。

#### 4.1 LOGBOOK.md（开发日志）

在 `LOGBOOK.md` **顶部**（第一个分隔线后）追加本轮变更记录：

```markdown
## [YYYY-MM-DD] - 一句话标题

- **操作人**: AI (Devin) / 开发者
- **关联任务**: 一句话描述
- **核心变更文件说明**:
  - `app/xxx/yyy.py`（修改/新增）: 说明变更内容
- **数据库状态变更**: 无 / 具体说明
- **测试覆盖与验证结果**: `pytest -q` → N passed ✅
- **潜伏风险/遗留未决事项说明**: 无 / 具体说明
```

#### 4.2 项目进度与配置清单.md（项目状态）

同步更新以下内容（按实际变更勾选）：

- **"最后更新"日期**：改为今天
- **三、已完成功能**：新增 `[x]` 条目描述本次功能
- **九、已知问题与风险**：将已修复的问题状态改为 `✅ 已解决`，新增新风险条目
- **七、测试脚本清单**：如新增测试脚本，补充到表格

> 以下文档仅在涉及核心业务流程/架构变更时才需更新：  
> `1-业务方案.md` / `2-工作流设计.md` / `3-技术架构.md` / `4-上线检查清单.md`

### 4.5 Skill 同步检查（本次变更涉及新增文件 / 类 / 调用关系时）

若本次变更涉及以下任一情况，必须先运行 `/sync-skills` 工作流：

- 新增 / 删除 `.py` 文件
- 新增 / 删除公开类或核心函数
- 改变模块间调用关系
- 修改 LLM 相关逻辑

### 6. Git 提交

```powershell
git add .
git status

# 提交（中文 Conventional Commits 格式）
git commit -m "feat(chat): 新增功能描述"
git push
```

## 提交类型速查

| type | 说明 | 示例 | |------|------|------| | `feat` | 新增功能 | `feat(chat): 新增运费关键词前置匹配` | | `fix` | 修复
bug | `fix(wecom): 修复企微消息解密失败问题` | | `docs` | 文档更新 | `docs(logbook): 更新项目演进记录` | | `refactor` | 重构 |
`refactor(repo): 提取公共查询方法` | | `perf` | 性能优化 | `perf(vector): 优化 TF-IDF 构建速度` | | `test` | 测试 |
`test(intent): 补充闲聊意图测试用例` | | `chore` | 构建/工具 | `chore(deps): 升级 openai 至最新版` |

## 验收标准

- [ ] 代码红线自查通过（Optional/Union/TODO 零输出）
- [ ] 相关测试通过
- [ ] 服务健康检查通过
- [ ] `LOGBOOK.md` 已更新
- [ ] 项目进度与配置清单等相关文档已同步更新
- [ ] Git 提交信息符合 Conventional Commits 格式
- [ ] 已推送到远程分支

## 收口顺序

代码改动 → 测试验证 → LOGBOOK 与文档更新 → 提交 → 推送

严格按此顺序执行，不可跳过任何步骤。
