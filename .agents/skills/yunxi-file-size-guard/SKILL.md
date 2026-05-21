______________________________________________________________________

## name: yunxi-file-size-guard version: 1.0.0 description: "芸熙烘焙 AI 客服项目防止上帝类与单文件膨胀的强制约束。当修改任意 .py 文件行数 ≥ 警戒线、新增公开类/函数、或评估文件是否需要拆分时使用。超阈值强制触发 large-file-refactor-review 工作流。"

# 芸熙烘焙单文件体量与上帝类守卫

## 📏 单文件体量阈值

> 阈值是「职责可能过载」的早期信号，不是拆分目标。超线必须先评估职责是否真实混杂，不是为压行数而拆。

| 层级 | 警戒线（warning） | 硬上限（blocking） | |------|------------------|-------------------| |
`app/api/*.py` 路由层 | 250 行 | 350 行 | | `app/service/*.py` 业务层 | 220 行 | 320 行 | |
`app/service/llm/*.py` LLM 子模块 | 120 行 | 180 行 | | `app/service/wecom/*.py` / `youzan/*.py` | 150 行
| 250 行 | | `app/repository/*.py` 数据层 | 150 行 | 250 行 | | `app/models/*.py` 模型层 | 80 行 | 120 行 |

**附加硬约束（任一违反即 blocking）：**

- 单文件公开类（非 `_` 前缀）数量 **≤ 3**
- 单类公开方法数量 **≤ 20**
- 单个函数/方法体 **≤ 50 行**（不含注释和空行）
- 禁止在大文件上继续追加新职责（无论是否超线）

## 🚫 上帝类反模式识别

满足以下任一条件即判定为上帝类，必须进入拆分流程：

- 单类/单模块同时承担 **≥ 4 类职责**（如：路由解析 + 业务逻辑 + DB 操作 + 外部 API 同时存在）
- 单个函数体超过 **50 行**
- 单文件同时包含 **≥ 4 个公开类**
- 单文件 import 跨越 **≥ 3 个不同功能模块**
- 同一函数既有 I/O 操作又有复杂业务逻辑判断

## ⚠️ 当前存量警戒文件

| 文件 | 实测行数 | 阈值 | 状态 | |------|---------|------|------| | `app/api/admin.py` | 293 行 | 250 warning
/ 350 blocking | ⚠️ 超警戒线 | | `app/service/chat.py` | 232 行 | 220 warning / 320 blocking | ⚠️ 超警戒线 |
| `app/service/llm/functions.py` | 128 行 | 120 warning / 180 blocking | ⚠️ 超警戒线 |

**修改这些文件时必须先走 `large-file-refactor-review` 工作流，且不得追加新职责。**

## 🧭 拆分方向指引

### `admin.py`（页面路由 + API 路由 + 认证混杂）

建议拆分为：

```
app/api/
├── admin_pages.py    # 页面路由（login/dashboard/transfers/chat-test）
├── admin_api.py      # API 路由（CRUD/transfer ops/session query）
└── admin_auth.py     # 认证依赖（token 验证/cookie 验证）
```

### `chat.py`（意图→检索→AI 循环混杂）

建议拆分为：

```
app/service/
├── chat.py               # 保留：入口调度 + 幂等去重 + 状态判断
└── chat_pipeline.py      # 抽出：AI 对话循环（query改写→检索→LLM→tool调用）
```

### `functions.py`（工具定义 + dispatch 混杂）

建议拆分为：

```
app/service/llm/
├── function_defs.py   # FUNCTION_DEFINITIONS 常量列表
└── function_dispatch.py  # dispatch_tool + 各工具处理函数
```

## 🔧 检查方法（PowerShell）

```powershell
# 查看所有 .py 文件行数排序
Get-ChildItem -Recurse -Filter "*.py" -Path "app" |
  ForEach-Object { [PSCustomObject]@{File=$_.Name; Lines=@(Get-Content $_.FullName).Count} } |
  Sort-Object Lines -Descending | Format-Table -AutoSize

# 单文件行数
@(Get-Content -LiteralPath "app/service/chat.py").Count

# 单文件公开类数量（不以 _ 开头的 class 定义）
Select-String -LiteralPath "app/service/chat.py" -Pattern "^class [A-Z]" | Measure-Object | Select-Object -ExpandProperty Count

# 函数行数超 50 行检测
$content = Get-Content "app/service/chat.py"
# 人工结合 IDE 展开查看各函数体行数
```

## 拆分前 3 问自检（任一为 No 就不拆）

1. 抽出后的单元能否被独立 mock 测试？
1. 抽出后原文件与新文件的职责边界是否更清晰？
1. 抽出是否会引入循环依赖、过多 callback、或破坏已有调用链？

## ✅ 拆分 Review Checklist

- [ ] 行数已回归阈值内（主文件 + 新文件均在警戒线下）
- [ ] 单文件公开类 ≤ 3，单类公开方法 ≤ 20
- [ ] 单函数体 ≤ 50 行
- [ ] 拆分后无循环依赖（分层方向：`api → service → repository → models`）
- [ ] 原调用方 import 路径无需修改（或已做向后兼容 re-export）
- [ ] 相关测试仍通过
- [ ] `LOGBOOK.md` 已更新
