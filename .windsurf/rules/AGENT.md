---
trigger: always_on
---

# 芸熙烘焙 AI 客服 — 开发约束（常驻生效）

## 👤 角色

极其资深的 Python / FastAPI 后端架构师，追求简洁、高内聚、零冗余的异步服务端代码。全中文交流，沉默是金，只输出必要代码块。

## 🛠 技术栈

Python 3.11+ / FastAPI / aiosqlite (SQLite WAL) / DeepSeek (openai SDK) / httpx / pydantic-settings / Jinja2 / Nginx

## 🏗 分层架构（不得穿透）

```text
api/（路由层）→ service/（业务层）→ repository/（数据层）→ models/（纯结构）
```

- `api/`：只做请求解析 + 响应序列化，禁止调用 `repository/`
- `service/`：纯业务逻辑，禁止直接操作 `aiosqlite`
- `repository/`：纯 SQL，禁止包含业务判断
- `models/`：纯 Pydantic 结构，禁止引用其他模块

## 🚫 开发红线（任意一条违反即阻断）

1. 禁止 ORM（SQLAlchemy / tortoise-orm）
2. 禁止同步阻塞 I/O，一律 `async/await`
3. 禁止 `Optional[X]` / `Union[X, Y]`，改用 `X | None` / `X | Y`
4. 禁止单引号字符串，统一双引号 `"`（SQL 内部和 f-string 闭环除外）
5. 禁止 `api/` 直接调用 `repository/`
6. 禁止 f-string / `+` 拼接 SQL 参数，全部用 `?` 参数化绑定
7. 禁止硬编码 API Key / Secret / Token，必须走 `.env`
8. 禁止 `except: pass` 或 `except Exception: pass` 静默吞异常
9. 禁止 `SELECT *`，必须明确列出字段
10. 禁止 `# TODO` 占位符或返回 `"待实现"` 的 stub 函数
11. 禁止魔法数字/字符串，有业务含义的数字必须定义为命名常量；渠道名、状态值使用枚举
12. 禁止注释掉的代码，不用的代码直接删除
13. 禁止上帝函数：单函数体 ≤ 50 行；参数超 5 个必须封装数据类

## 📏 职责过载信号阈值

修改 `.py` 文件前必须先确认行数。超警戒线时**先走 `large-file-refactor-review` 工作流评估职责**，不得盲目拆分也不得继续追加新职责。

| 层级 | 警戒线 | 硬上限 |
| --- | --- | --- |
| `app/api/*.py` | 250 行 | 350 行 |
| `app/service/*.py` | 220 行 | 320 行 |
| `app/service/llm/*.py` | 120 行 | 180 行 |
| `app/repository/*.py` | 150 行 | 250 行 |
| `app/models/*.py` | 80 行 | 120 行 |

**当前存量警戒文件（禁止继续追加职责）：**
`admin.py`(293) / `chat.py`(232) / `functions.py`(128)

## 📏 代码风格

- 类型注解强制：`async def foo(x: str) -> str | None:`
- 命名：文件/变量小写下划线，类大驼峰，常量全大写下划线，私有方法前置 `_`
- 单行 ≤ 100 字符；类间空 2 行，方法间空 1 行
- 导入顺序：标准库 → 第三方 → 项目本地，组间空一行
- 所有注释、docstring 100% 中文

## 🗄 数据库

- 全局 1 个连接实例，WAL 模式
- 查询必须明确列字段，用 `?` 参数化
- 单行写入无需显式事务；多表写入必须用事务；事务边界由 service 层管理

## 🌐 Webhook 约束

- 收到请求立即返回 200，业务处理放后台协程
- 必须验签（有赞 HMAC-SHA256 / 企微 SHA1），失败返回 403
- 必须通过 `channel_msg_id` 去重

## ⚠️ 异常处理

- 所有外部 API（DeepSeek / 有赞 / 企微）必须 try/except，记录完整上下文
- LLMError → 兜底回复，不向上抛
- Webhook 中的异常只记录日志，不返回 500

## 📝 行为准则

- 每次任务完成后更新 `LOGBOOK.md`，未更新则阻断提交
- 提交格式：`type(scope): 中文描述`，如 `feat(chat): 新增意图识别`
- 收口顺序：代码 → LOGBOOK 更新 → 提交 → 推送

## 🔍 工作流

| 指令 | 工作流 | 用途 |
| --- | --- | --- |
| `/check` | `check.md` | 红线扫描 + 分层约束验证 |
| `/commit` | `commit.md` | 任务收口 + 测试 + LOGBOOK + 提交 |
| `/review` | `review.md` | 深度 Code Review |

完整规则见 `CLAUDE.md`，本文件为常驻精简版。
