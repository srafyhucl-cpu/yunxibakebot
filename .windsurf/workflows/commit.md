______________________________________________________________________

## description: 开发任务收口工作流，用于芸熙烘焙 AI 客服项目的任务完成检查、LOGBOOK 更新和代码提交

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

### 4. LOGBOOK.md 更新（必须，否则阻断提交）

在 `LOGBOOK.md` 顶部追加本轮变更记录，格式：

```markdown
## [版本/日期] - YYYY-MM-DD
- **操作人**: AI (Cascade) / 开发者
- **关联任务/功能**: 一句话描述
- **核心变更文件说明**:
  - `app/xxx/yyy.py`: 说明变更内容
- **数据库状态变更 (Schema Update)**:
  - 无 / 具体说明
- **测试覆盖与验证结果**:
  - `python scripts/xxx.py` ✅ 验证结果描述
- **潜伏风险/遗留未决事项说明 (Risk & Debt)**:
  - 无 / 具体说明
```

### 5. 项目进度与配置清单等文档更新（必须，否则阻断提交）

每次开发任务完成后，必须同步检查并更新项目根目录下的核心文档：

- `项目进度与配置清单.md`：必须同步更新完成的开发阶段百分比、配置项状态、以及已知问题和风险的自愈消除情况。
- `1-业务方案.md` / `2-工作流设计.md` / `3-技术架构.md` / `4-上线检查清单.md`：如本次修改涉及到了核心业务流程变更、对话卡片视觉流或底层技术部署等，必须同步对齐。

**更新要求**：

- 严禁任何项目进度与实际代码运行状态脱节。
- 严禁配置清单说明滞后于真实的 `.env.example` 或 `config.py` 改动。

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

**代码改动 → 测试验证 → LOGBOOK 与文档更新 → 提交 → 推送**

严格按此顺序执行，不可跳过任何步骤。
