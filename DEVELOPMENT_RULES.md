# YunxiBakeBot — 开发约束规范（已归档）

> ⚠️ **本文档已合并至 `CLAUDE.md`，不再单独维护。** 所有开发规则、架构约束、代码风格、质量门禁均以 `CLAUDE.md` 为唯一权威来源。 本文件保留仅供历史参考。

______________________________________________________________________

## 一、编码规范

### 1.1 语言与语法

- Python 3.11+，强制使用类型注解（`def foo(x: int) -> str:`）
- 所有 I/O 操作用 `async/await`，禁止同步阻塞调用
- 禁止 `Optional`，改用 `X | None`
- 禁止 `Union`，改用 `X | Y`
- 字符串统一用双引号 `"`，不用单引号

### 1.2 命名规范

| 类型 | 规范 | 示例 | |------|------|------| | 文件/模块 | 小写+下划线 | `session_manager.py` | | 类 | 大驼峰 |
`SessionManager` | | 函数/方法 | 小写+下划线 | `get_or_create()` | | 变量 | 小写+下划线 | `session_id` | | 常量 |
全大写+下划线 | `MAX_TOOL_ROUNDS` | | 私有方法/属性 | 前导下划线 | `_verify_signature()` | | Pydantic 模型 | 大驼峰 |
`SessionCreate` |

### 1.3 导入规范

```python
# 标准库
import uuid
from datetime import datetime, timezone
from typing import Self

# 第三方
import aiosqlite
from openai import AsyncOpenAI
from pydantic import BaseModel

# 项目本地
from app.models.session import Session
from app.repository.session_repo import SessionRepo
```

### 1.4 代码风格

- 单行 ≤ 100 字符
- 类之间空 2 行，方法之间空 1 行
- 永远不留注释掉的代码
- docstring 只写**接口契约**（参数/返回值/异常），不写实现细节
- 行内注释只解释 WHY，不解释 WHAT

______________________________________________________________________

## 二、架构约束

### 2.1 分层规则

```
api/（HTTP 路由）
  → service/（业务逻辑）
    → repository/（数据访问）
```

- **api/**: 只做请求解析 + 响应序列化，不包含业务逻辑
- **service/**: 纯业务逻辑，不能直接调用 `aiosqlite`，只能调用 `repository/`
- **repository/**: 纯 SQL 操作，不能包含业务逻辑
- **models/**: 纯数据结构，不能包含逻辑，不能引用其他模块

### 2.2 禁止事项

- ❌ 禁止使用 ORM（SQLAlchemy / tortoise-orm）
- ❌ 禁止在 repository 层之外拼接 SQL
- ❌ 禁止在 api/ 层直接调用 repository/
- ❌ 禁止 `except: pass` 静默忽略异常
- ❌ 禁止用 `+` 或 f-string 拼接 SQL 参数
- ❌ 禁止在代码中硬编码敏感信息（secret、token 等）
- ❌ 禁止使用 `typing.Optional` / `typing.Union`

______________________________________________________________________

## 三、数据库约束

### 3.1 连接配置

```sql
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;
```

- 全局只维护 1 个连接实例
- 所有查询使用 `?` 参数化绑定
- 禁止使用 `*` SELECT

### 3.2 查询规范

```python
# ✅ 正确
await db.execute("SELECT id, name FROM sessions WHERE user_id = ?", (user_id,))

# ❌ 禁止
await db.execute(f"SELECT * FROM sessions WHERE user_id = '{user_id}'")
```

### 3.3 事务

- 单行写入不需要显式事务
- 多表写入必须用事务
- repository 方法不管理事务，由 service 层决定事务边界

______________________________________________________________________

## 四、RAG 高可用与高并发核心红线

### 4.1 统一媒体协议 (UMP) 交互契约规范

- **后端参数拼装强制约束**：凡是涉及多媒体资源投递（`type="image"`）或商品卡片（`type="card"`）在 RAG 动态注入、大模型上下文组装或渠道适配层（Channel Adapter）的参数拼装，**绝对禁止直接使用 f-string 或字符串手工拼装参数键值对**。必须强制、无条件统一调用标准库 `urllib.parse.urlencode(params, quote_via=urllib.parse.quote)` 进行高保真标准查询字符串编码，彻底死锁由于特殊品名、加料 SPU、空格及中文复杂 emoji 引发的前端分段截断 Bug。
- **前端抗噪规范**：前端或控制台多媒体解析微内核在执行正则捕获提取后，读取任意参数必须强制执行 `.trim()` 首尾去空和短路安全兜底（如 `|| "0.00"`），彻底绝缘并抹除任何因大模型 Markdown 幻觉或冗余换行引发的组件卡片吞没崩溃。

### 4.2 高性能向量存储与冷启动自愈控制规范

- **格式闭密隔离**：彻底清退并全面禁止引入任何具有 Python 版本强依赖和安全反序列化漏洞隐患的 `pickle` 二进制缓存。密集向量连续特征矩阵必须统一通过 NumPy 原生的 `np.save`（指定临时的 `.tmp.npy` 并通过系统级 `os.replace` 原子覆写）转化为 `vectors.npy` 保存，其余结构化元数据和数据特征哈希通过标准 JSON 文件物理隔离读写。
- **冷启动特征版本锁**：服务 Lifespan 启动期初始化时，必须对数据库所有合法知识点的内容（content_md）进行全量串联计算 MD5 文本强特征版本锁 `current_db_md5`。启动对齐判定必须满足：`vs._ready and cached_keys == db_keys and vs._data_hash == current_db_md5` 双重特征完全一致。任何不一致（包含话术微调或本地改价）必须在云端精准触发全量无损重建自愈。
- **节流刷盘守护**：禁止在任何业务消费层、API 视图层单条变更后手工、高频直调 `vs.save()` 覆写磁盘。所有增删改属性变动一律归集于内存层追加池（List Buffer），并统一交由常驻的 120 秒后台守护任务（`periodic_save_task`）执行批量合并异步无损落盘，极致减载服务器磁盘 I/O 锁空间。

### 4.3 高并发数仓事务隔离与索引红线规范

- **强事务包裹契约**：在有赞 Webhook 回调高频打入且涉及多表联动级联写入时（如物理宽表同步 + RAG 知识表 Upsert + Analytics 审计埋点落库），必须在 service 层统一生命周期，**强制紧密包裹在同一个原生 SQL 事务（TRANSACTION）控制块中一次性全量落盘**，将 SQLite 排他性写锁持有耗时锁死在 2ms 以内。
- **归因大查询底线**：所有针对高清分析埋点数据执行的长周期 lookback 滑动归因大查询或 Dashboard 看板多维多阶统计，必须严格且 100% 依赖高精度复合联合索引，绝对禁止引发任何导致发生排他锁挂起的全表线性扫描，誓死捍卫 Webhook 3 秒超时生死线。

______________________________________________________________________

## 五、API 约束

### 5.1 响应格式

所有 HTTP 响应统一格式：

```python
# 成功
{"code": 0, "data": {...}}

# 失败
{"code": 40001, "message": "参数错误", "detail": "..."}
```

### 5.2 状态码使用

| 场景 | HTTP 状态码 |
|------|------------|
| 成功 | 200 |
| 参数校验失败 | 422 |
| 未授权 | 401 |
| 无权限 | 403 |
| 资源不存在 | 404 |
| Webhook 签名错误 | 403 |

### 5.3 Webhook 约束

- Webhook 处理函数收到请求后 **立即返回 200**，处理放在后台协程
- 必须有签名验证，验证失败返回 403
- 必须有消息去重（通过 channel_msg_id 的 TTL 锁自愈驱逐机制）

______________________________________________________________________

## 六、错误处理约束

### 6.1 异常层级

```
AppError（基类）
├── AuthError        # 认证/签名错误
├── NotFoundError    # 资源不存在
├── LLMError         # DeepSeek API 错误
├── APIError         # 有赞/企微外部 API 错误
└── ConfigError      # 配置错误
```

### 6.2 异常处理规则

- 所有外部 API 调用（DeepSeek / 有赞 / 企微）必须用 try/except 包裹
- 外部 API 失败时记录完整上下文（请求参数、响应状态码、耗时）
- LLM 调用失败使用兜底回复（"系统正忙，请稍后再试"），不向上抛
- Webhook 处理中的异常只记录日志，不返回 500

______________________________________________________________________

## 七、日志约束

### 7.1 级别使用

| 级别 | 场景 |
|------|------|
| `DEBUG` | SQL 执行、API 请求/响应体 |
| `INFO` | 服务启动、会话创建、消息收发 |
| `WARNING` | API 重试、配置缺失但可以降级 |
| `ERROR` | 外部 API 失败、数据库错误 |
| `CRITICAL` | 启动失败、致命错误 |

### 7.2 每条日志必须包含的字段

```python
{"time": "...", "level": "INFO", "module": "chat", "session_id": "...", "message": "..."}
```

- service 层日志必须带 `session_id`
- API 调用日志必须带 `channel` 和 `user_id`

______________________________________________________________________

## 八、安全约束

- 密码使用 bcrypt 哈希（管理后台登录）
- JWT token 有效期 ≤ 24 小时
- `.env` 文件不进版本控制
- SQLite 文件不进版本控制
- HTTPS 必须在 Nginx 层终结，服务内部不处理 TLS
- 所有管理后台 API 需要 JWT 或 Bearer token 鉴权

______________________________________________________________________

## 九、测试约束（后续扩展）

- 测试文件放在 `tests/`，目录结构镜像 `app/`
- 数据库测试使用临时文件，不污染开发数据
- 外部 API 测试使用 mock

______________________________________________________________________

## 十、Git 约束

- `.env`、`data/`、`__pycache__/`、`*.pyc` 进 `.gitignore`
- 不提交调试代码、临时文件
- 不做 `git commit --no-verify`
