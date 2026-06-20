# Bakery Commerce Platform (Platform 仓)

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.4+-brightgreen.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Bakery Commerce Platform 是一个面向烘焙门店经营场景的 Platform 主仓，统一承载客户、商品、订单、履约、AI 会话、后台配置和第三方集成能力。当前首个真实落地实例为 `Yunxi`，消费者前台渠道仓为 `Storefront MiniApp`。

> 说明：当前仓库 slug 仍为 `YunxiBakeBot`，本文中的 `Platform` 指产品角色，不等于仓库名；`Storefront MiniApp` 也是前台渠道角色名，不等于仓库名。历史文档若出现 `YunxiBakeBot` / `YunxiBakeMiniApp`，优先按“当前仓库名”或“迁移阶段引用”理解，不要当作产品名。

> 当前仓库仍沿用 `YunxiBakeBot` 代码仓路径，但产品口径已升级为通用平台：`Bakery Commerce Platform`。如果你正在找的是历史上的 `YunxiBakeMiniApp` 口径，请把它理解为前台渠道仓的旧称。
>
> 如果你现在关注的是有赞客户迁移，请优先看这四段当前权威入口：`docs/architecture/youzan-customer-migration-audit-checklist.md`、`docs/architecture/youzan-customer-formal-import-runbook.md`、`scripts/verify_youzan_customer_import.py`、`docs/architecture/youzan-customer-import-handoff-and-rollback-runbook.md`。
>
> 如果你需要回看双仓推进的历史过渡材料，请到 [docs/README.md](docs/README.md) 的“历史方案”区统一查看，不要把这些材料当作当前实施蓝图。
>
> 文档分层导航见 [docs/README.md](docs/README.md)。

## 📋 目录

- [项目介绍](#项目介绍)
- [功能特性](#功能特性)
- [生产级补强流程图](#生产级补强流程图)
- [Vibe Coding Harness Engineering](#vibe-coding-harness-engineering)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [安装配置](#安装配置)
- [运行指南](#运行指南)
- [目录结构](#目录结构)
- [测试说明](#测试说明)
- [部署指南](#部署指南)
- [开发规范](#开发规范)
- [API 文档](#api-文档)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## 项目介绍

### 🎯 项目背景

芸熙烘焙是一家线上烘焙店，通过有赞小程序接收客户咨询和下单。随着业务增长，人工客服压力增大，需要一套智能客服系统来：

1. **自动回答常见问题**（营业时间、配送范围、产品信息等）
2. **实时查询订单状态**（订单详情、物流信息）
3. **智能推荐商品**（根据客户需求推荐合适的烘焙产品）
4. **无缝转接人工**（复杂问题自动转接人工客服）
5. **多渠道接入**（有赞小程序、企业微信等）

如果你关注的是当前有赞客户迁移工作，完整入口见：

- [有赞客户迁移审计清单](docs/architecture/youzan-customer-migration-audit-checklist.md)
- [有赞客户正式迁移执行 Runbook](docs/architecture/youzan-customer-formal-import-runbook.md)
- [有赞客户迁移后核对脚本](scripts/verify_youzan_customer_import.py)
- [有赞客户迁移交接与回滚 Runbook](docs/architecture/youzan-customer-import-handoff-and-rollback-runbook.md)

### 💡 解决方案

本系统采用 **FastAPI + DeepSeek LLM + RAG（检索增强生成）** 技术栈，实现了：

- 🤖 **智能对话**：基于 DeepSeek 大模型，支持多轮对话、上下文理解
- 📚 **知识库管理**：支持 FAQ、产品信息、规则话术等知识的录入和检索
- 🔍 **混合检索**：向量语义搜索 + 关键词搜索，提高召回准确率
- 🛒 **有赞集成**：自动同步商品信息、实时查询订单和物流
- 👨💼 **人工接管**：AI 无法处理时自动转接人工客服
- 📊 **数据观察台**：实时监控对话质量、会话统计、性能分析

---

## 生产级补强流程图

本轮本地生产化补强已整理为一份可离线打开的对比流程图，覆盖修改前的上线风险、修改后的 `/ready` 门禁、`preflight` 恢复计划、显式迁移、基础知识种子、向量重建和冒烟 JSON 留档闭环；图中还补充了细节矩阵、明日生产同步泳道、当前运行时缺口和验收信号。

- 打开流程图：[docs/production-readiness-before-after.html](docs/production-readiness-before-after.html)
- 上线前清单：[项目进度与配置清单.md](项目进度与配置清单.md)
- 最近变更日志：[LOGBOOK.md](LOGBOOK.md)

---

## Vibe Coding Harness Engineering

项目已新增一套面向 AI 驾驭和 Vibe Coding 可持续演进的 Harness Engineering 体系，用于把需求、决策、改动、验证、证据和复盘串成可追溯闭环，并把重复错误沉淀为测试、脚本、规则或 runbook。所有 Harness 文档统一收纳在一个父目录中：

- 统一入口：[docs/harness-engineering/README.md](docs/harness-engineering/README.md)
- 前后对比图：[docs/harness-engineering/before-after.html](docs/harness-engineering/before-after.html)
- 项目 Harness Skill：`.agents/skills/yunxi-harness-engineering/SKILL.md`
- 交接快照命令：`python scripts/harness_snapshot.py`
- 防重犯账本检查：`python scripts/check_mistake_ledger.py`，并已接入 pre-commit 的 `check-mistake-ledger` hook
- 中文乱码处理：[docs/AGENTS/encoding-and-terminal.md](docs/AGENTS/encoding-and-terminal.md)，当前 PowerShell 可执行 `.\scripts\enable_utf8_console.ps1`

---

## 功能特性

### ✨ 核心功能

#### 1. AI 智能对话

- ✅ **多轮对话管理**：支持上下文记忆，理解用户意图
- ✅ **Function Calling**：LLM 可自动调用工具（订单查询、物流查询、商品查询等）
- ✅ **意图识别**：自动识别用户意图（咨询、下单、投诉、转人工等）
- ✅ **情绪安抚**：检测用户情绪，自动触发安抚话术

#### 2. 知识库管理

- ✅ **多类型知识**：支持 FAQ、产品信息、规则话术、闲聊等类型
- ✅ **混合检索**：向量语义搜索 + 关键词搜索，提高召回准确率
- ✅ **实时数据注入**：动态注入商品库存、价格等实时数据
- ✅ **向量同步**：知识更新时自动同步到向量索引

#### 3. 有赞电商集成

- ✅ **Webhook 对接**：接收有赞商品上架/下架、订单状态变更等事件
- ✅ **商品同步**：自动同步有赞商品信息到知识库
- ✅ **订单查询**：实时查询订单状态、物流信息
- ✅ **商品推荐**：根据对话内容推荐相关商品

#### 4. 人工客服转接

- ✅ **智能转接**：AI 无法处理时自动转接人工客服
- ✅ **会话接力**：人工客服可查看 AI 对话历史
- ✅ **队列管理**：支持转人工队列管理
- ✅ **人工回复**：人工客服通过管理后台回复用户

#### 5. 管理后台

- ✅ **AI 对话调试**：实时查看 AI 对话过程、调试 Prompt
- ✅ **商品管理**：管理有赞商品、设置主推款
- ✅ **知识配置**：管理知识库、批量导入/导出
- ✅ **转人工队列**：查看和处理转人工请求
- ✅ **数据观察台**：会话统计、消息分析、性能监控
- ✅ **系统配置**：管理 API Token、系统参数

#### 6. 企业微信集成（开发中）

- ⏳ **企微消息接收**：接收企微单聊和群聊消息
- ⏳ **企微消息发送**：通过企微发送 AI 回复
- ⏳ **客户联系**：管理企微客户联系功能

### 🎨 UI/UX 特性

- ✅ **响应式设计**：适配桌面端和移动端
- ✅ **移动端优化**：iOS Safe Area 适配、触摸优化
- ✅ **暗色主题**：管理后台支持暗色主题
- ✅ **实时反馈**：加载状态、错误提示、空状态展示

---

## 技术栈

### 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11+ | 后端编程语言 |
| **FastAPI** | 0.104+ | Web 框架，提供高性能 API |
| **DeepSeek API** | - | 大语言模型，提供对话能力 |
| **SQLite** | 3.x | 本地数据库，存储会话、消息、知识库 |
| **aiosqlite** | 0.19+ | 异步 SQLite 驱动 |
| **Pydantic** | 2.x | 数据验证和设置管理 |
| **pydantic-settings** | 2.x | 从环境变量加载配置 |

### 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Vue 3** | 3.4+ | 前端框架 |
| **Vite** | 5.x | 构建工具 |
| **TypeScript** | 5.x | 类型安全 |
| **Element Plus** | 2.5+ | UI 组件库 |
| **Pinia** | 2.x | 状态管理 |
| **Vue Router** | 4.x | 路由管理 |
| **Axios** | 1.x | HTTP 客户端 |

### 核心算法与技术

| 技术 | 用途 |
|------|------|
| **RAG（检索增强生成）** | 结合知识库检索和 LLM 生成 |
| **向量语义搜索** | 使用 NumPy 实现向量相似度搜索 |
| **关键词搜索** | SQL LIKE 模糊匹配 |
| **混合检索** | 向量搜索 + 关键词搜索组合 |
| **Function Calling** | LLM 自动调用工具函数 |
| **意图识别** | 基于规则 + LLM 的意图分类 |

---

## 系统架构

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      用户渠道                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ 有赞小程序 │  │ 企业微信 │  │ 其他渠道 │              │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘              │
└────────┼───────────────┼─────────────┼──────────────────┘
         │               │             │
         ▼               ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 应用层                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Webhook   │  │ 管理后台 │  │ 企微回调 │              │
│  │ API       │  │ API      │  │ API      │              │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘              │
└────────┼───────────────┼─────────────┼──────────────────┘
         │               │             │
         ▼               ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                    业务服务层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Chat      │  │ Knowledge │  │ Youzan   │              │
│  │ Service   │  │ Retriever │  │ Service  │              │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘              │
│  ┌─────┴────┐  ┌─────┴────┐  ┌─────┴────┐             │
│  │ LLM       │  │ Embedding │  │ Transfer │             │
│  │ Client    │  │ Searcher  │  │ Manager  │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────────┘
         │               │             │
         ▼               ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                    数据访问层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Session   │  │ Knowledge │  │ Youzan   │              │
│  │ Repo      │  │ Repo      │  │ Product  │              │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘              │
└────────┼───────────────┼─────────────┼──────────────────┘
         │               │             │
         ▼               ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                    SQLite 数据库                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ sessions  │  │ messages  │  │ knowledge│              │
│  └──────────┘  └──────────┘  └──────────┘              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ youzan_   │  │ transfers │  │ analytics │              │
│  │ products  │  │           │  │           │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                  外部服务                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ DeepSeek  │  │ 有赞云   │  │ 企业微信 │              │
│  │ API       │  │ API      │  │ API      │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────────┘
```

### 分层架构

项目采用经典的三层架构：

```
┌─────────────────────────────────────────────────────────────┐
│                    API 层 (app/api/)                      │
│  负责：接收 HTTP 请求、参数验证、路由分发、响应返回      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Service 层 (app/service/)                 │
│  负责：业务逻辑、LLM 调用、外部 API 对接、数据处理      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               Repository 层 (app/repository/)              │
│  负责：数据库 CRUD、SQL 查询、数据访问                   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Models 层 (app/models/)                   │
│  负责：数据模型定义、Pydantic 验证、类型定义            │
└─────────────────────────────────────────────────────────────┘
```

**架构原则**：

1. ✅ **单向依赖**：API → Service → Repository → Models
2. ❌ **禁止反向依赖**：Models 不能依赖上层，Repository 不能直接被 API 调用
3. ✅ **依赖注入**：通过构造函数注入依赖，便于测试和复用
4. ✅ **单一职责**：每层只负责自己的职责

---

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 18+
- 有赞云账号（可选，支持 Mock 模式）
- DeepSeek API Key

### 5 分钟快速启动

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/YunxiBakeBot.git
cd YunxiBakeBot

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. 安装后端依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 DeepSeek API Key

# 5. 初始化数据库
python scripts/init_db.py

# 6. 导入知识种子数据
python scripts/seed_knowledge.py

# 7. 启动后端服务
python -m uvicorn app.main:app --host 127.0.0.1 --port 7001 --reload

# 8. 新开终端，启动前端（可选）
cd web/admin
npm install
npm run dev

# 9. 访问应用
# 后端 API 文档：http://127.0.0.1:7001/docs
# 管理后台：http://localhost:5173
```

---

## 安装配置

### 1. 后端安装

#### 1.1 克隆项目

```bash
git clone https://github.com/your-repo/YunxiBakeBot.git
cd YunxiBakeBot
```

#### 1.2 创建虚拟环境

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

#### 1.3 安装依赖

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖（测试、代码检查）
```

#### 1.4 配置环境变量

复制 `.env.example` 到 `.env`：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要配置：

```env
# DeepSeek API（必须）
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# 有赞云（可选，支持 Mock 模式）
YOUZAN_CLIENT_ID=your-client-id
YOUZAN_CLIENT_SECRET=your-client-secret
YOUZAN_KDT_ID=your-kdt-id
YOUZAN_MOCK_MODE=True

# 企业微信（可选，第四阶段启用）
WECOM_CORP_ID=your-corp-id
WECOM_AGENT_ID=your-agent-id
WECOM_SECRET=your-secret

# 管理后台（必须）
ADMIN_API_TOKEN=your-admin-token

# 服务配置（可选）
SERVER_HOST=127.0.0.1
SERVER_PORT=7001
LOG_LEVEL=info
```

#### 1.5 初始化数据库

```bash
python scripts/init_db.py
```

这将创建 `data/bot.db` 数据库文件，并初始化所有表结构。

#### 1.6 导入知识种子数据

```bash
python scripts/seed_knowledge.py
```

这将导入 FAQ、产品信息、规则话术等基础知识到知识库。

#### 1.7（可选）同步有赞商品

```bash
python scripts/sync_youzan_products.py
```

这将从有赞 API 同步商品信息到本地数据库和知识库。

### 2. 前端安装（可选）

如果需要使用管理后台前端，需要安装前端依赖。

#### 2.1 进入前端目录

```bash
cd web/admin
```

#### 2.2 安装依赖

```bash
npm install
```

#### 2.3 配置环境变量

复制 `.env.example` 到 `.env`：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
VITE_API_BASE_URL=http://127.0.0.1:7001
VITE_ADMIN_TOKEN=your-admin-token
```

---

## 运行指南

### 1. 本地开发运行

#### 1.1 启动后端

```bash
# 开发模式（自动重载）
python -m uvicorn app.main:app --host 127.0.0.1 --port 7001 --reload

# 生产模式
python -m uvicorn app.main:app --host 0.0.0.0 --port 7001 --workers 4
```

启动后访问：

- **API 文档（Swagger UI）**：http://127.0.0.1:7001/docs
- **API 文档（ReDoc）**：http://127.0.0.1:7001/redoc
- **健康检查**：http://127.0.0.1:7001/health

#### 1.2 启动前端（可选）

```bash
cd web/admin
npm run dev
```

启动后访问：

- **管理后台**：http://localhost:5173
- **默认登录账号**：Admin / Admin123!

#### 1.3 验证运行

```bash
# 健康检查
curl http://127.0.0.1:7001/health
# 预期返回：{"status":"ok","version":"0.1.0"}

# 测试 AI 对话
curl -X POST http://127.0.0.1:7001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"channel":"test","user_id":"user123","content":"你好"}'
```

### 2. 生产部署运行

#### 2.1 使用 systemd（Linux）

创建 systemd 服务文件 `/etc/systemd/system/yunxibakebot.service`：

```ini
[Unit]
Description=Bakery Commerce Platform - Platform Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/YunxiBakeBot
ExecStart=/path/to/YunxiBakeBot/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 7001 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start yunxibakebot
sudo systemctl enable yunxibakebot  # 开机自启
sudo systemctl status yunxibakebot   # 查看状态
```

#### 2.2 使用 SSH 远程部署

```bash
# 部署到远程服务器
ssh root@your-server-ip "cd /path/to/YunxiBakeBot && git pull && systemctl restart yunxibakebot"
```

#### 2.3 查看日志

```bash
# 使用 systemd
sudo journalctl -u yunxibakebot -f

# 或直接查看日志文件
tail -f logs/bot.log
```

### 3. 常用运维命令

```bash
# 重启服务
sudo systemctl restart yunxibakebot

# 查看服务状态
sudo systemctl status yunxibakebot

# 查看实时日志
sudo journalctl -u yunxibakebot -f

# 备份数据库
cp data/bot.db data/bot.db.backup.$(date +%Y%m%d)

# 恢复数据库
cp data/bot.db.backup.20260104 data/bot.db

# 重新导入知识种子
python scripts/seed_knowledge.py --force

# 重新同步有赞商品
python scripts/sync_youzan_products.py --force
```

---

## 目录结构

```
YunxiBakeBot/
├── app/                          # 后端应用目录
│   ├── api/                      # API 路由层
│   │   ├── wecom.py              # 企微回调 API
│   │   ├── admin.py              # 管理后台页面路由
│   │   ├── admin_dialog.py       # AI 对话调试 API
│   │   ├── admin_transfer.py     # 转人工管理 API
│   │   ├── admin_knowledge.py   # 知识配置 API
│   │   ├── admin_observability.py # 数据观察台 API
│   │   └── webhook.py           # 有赞 Webhook API
│   ├── service/                  # 业务服务层
│   │   ├── chat.py               # 核心对话服务
│   │   ├── knowledge_retriever.py # 知识检索服务
│   │   ├── embedding_search.py   # 向量搜索服务
│   │   ├── session_manager.py    # 会话管理服务
│   │   ├── transfer_manager.py   # 转人工管理服务
│   │   ├── youzan/               # 有赞服务
│   │   │   ├── client.py         # 有赞 API 客户端
│   │   │   └── event_handler.py  # 有赞事件处理器
│   │   ├── wecom/                # 企微服务（开发中）
│   │   └── llm/                  # LLM 服务
│   │       ├── client.py         # DeepSeek API 客户端
│   │       ├── functions.py      # Function Calling 分发器
│   │       ├── prompt.py         # System Prompt 构建器
│   │       ├── intent.py         # 意图识别器
│   │       └── soothe.py         # 情绪安抚处理器
│   ├── repository/                # 数据访问层
│   │   ├── session_repo.py       # 会话仓库
│   │   ├── message_repo.py       # 消息仓库
│   │   ├── knowledge_repo.py     # 知识库仓库
│   │   ├── youzan_repo.py        # 有赞商品仓库
│   │   └── transfer_repo.py      # 转人工仓库
│   ├── models/                    # 数据模型层
│   │   ├── session.py             # 会话模型
│   │   ├── message.py             # 消息模型
│   │   ├── knowledge.py           # 知识条目模型
│   │   └── youzan_product.py      # 有赞商品模型
│   ├── config.py                  # 配置管理
│   ├── main.py                    # FastAPI 应用入口
│   ├── database.py                # 数据库初始化
│   ├── exceptions.py              # 自定义异常
│   └── logger.py                  # 日志配置
├── web/                          # 前端目录
│   └── admin/                     # 管理后台前端
│       ├── src/
│       │   ├── pages/             # 页面组件
│       │   ├── components/        # 通用组件
│       │   ├── services/          # API 服务层
│       │   ├── stores/            # Pinia 状态管理
│       │   ├── router/           # 路由配置
│       │   └── utils/             # 工具函数
│       ├── public/                # 静态资源
│       ├── package.json           # 依赖配置
│       ├── vite.config.ts         # Vite 配置
│       └── tsconfig.json          # TypeScript 配置
├── scripts/                      # 脚本目录
│   ├── init_db.py                 # 数据库初始化脚本
│   ├── seed_knowledge.py          # 知识种子导入脚本
│   ├── sync_youzan_products.py   # 有赞商品同步脚本
│   └── ...
├── tests/                        # 测试目录
│   ├── api/                       # API 测试
│   ├── service/                   # Service 测试
│   ├── repository/                # Repository 测试
│   └── ...
├── data/                         # 数据目录
│   ├── bot.db                     # SQLite 数据库文件
│   └── embeddings/                # 向量索引文件
├── docs/                         # 文档目录
│   ├── 评估报告.md                # 项目评估报告
│   └── ...
├── .env.example                  # 环境变量示例文件
├── requirements.txt               # Python 依赖
├── pytest.ini                     # pytest 配置
├── README.md                     # 项目 README
└── AGENTS.md                     # AI Agent 工作规范
```

---

## 测试说明

### 1. 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行所有测试（简洁模式）
python -m pytest tests/ -q

# 运行指定目录的测试
python -m pytest tests/api/ -v
python -m pytest tests/service/ -v
python -m pytest tests/repository/ -v

# 运行指定文件
python -m pytest tests/api/test_chat.py -v

# 运行指定测试函数
python -m pytest tests/api/test_chat.py::test_handle_message -v

# 跳过慢速测试
python -m pytest tests/ -m "not slow" -v

# 只运行慢速测试
python -m pytest tests/ -m "slow" -v
```

### 2. 测试覆盖

当前项目共有 **118 个测试用例**，全部通过。

| 测试类型 | 用例数 | 覆盖模块 |
|---------|-------|---------|
| API 测试 | 8 | 所有 API 端点 |
| Service 测试 | 5 | 核心业务逻辑 |
| Repository 测试 | 10 | 数据访问层 |
| 集成测试 | 95 | 端到端流程 |

### 3. 编写新测试

测试文件位于 `tests/` 目录，按照模块组织：

```
tests/
├── api/               # API 测试
├── service/           # Service 测试
├── repository/        # Repository 测试
├── models/           # Model 测试
└── conftest.py       # 共享 fixtures
```

示例测试：

```python
# tests/service/test_chat.py
import pytest
from app.service.chat import ChatService

@pytest.mark.asyncio
async def test_handle_message():
    """测试处理用户消息"""
    # 1. 准备测试数据
    chat_service = ChatService(...)
    
    # 2. 执行测试
    reply = await chat_service.handle_message(
        channel="test",
        user_id="user123",
        content="你好"
    )
    
    # 3. 断言结果
    assert reply is not None
    assert "你好" in reply
```

---

## 部署指南

### 1. 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                    负载均衡（可选）                        │
│                  Nginx / HAProxy                          │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI 应用服务器                       │
│            Uvicorn (多 worker 模式)                      │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  SQLite 数据库                             │
│              data/bot.db                                  │
└─────────────────────────────────────────────────────────────┘
```

### 2. 部署步骤

#### 2.1 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Python 3.11+
sudo apt install python3.11 python3.11-venv python3-pip -y

# 安装 Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# 安装 Nginx（可选）
sudo apt install nginx -y
```

#### 2.2 部署后端

```bash
# 1. 克隆代码
git clone https://github.com/your-repo/YunxiBakeBot.git /opt/yunxibakebot
cd /opt/yunxibakebot

# 2. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 5. 初始化数据库
python scripts/init_db.py

# 6. 导入知识种子
python scripts/seed_knowledge.py

# 7. 创建 systemd 服务
sudo nano /etc/systemd/system/yunxibakebot.service
# 内容见上文

# 8. 启动服务
sudo systemctl daemon-reload
sudo systemctl start yunxibakebot
sudo systemctl enable yunxibakebot
```

#### 2.3 部署前端（可选）

```bash
# 1. 构建前端
cd web/admin
npm install
npm run build

# 2. 部署到 Nginx
sudo cp -r dist/* /var/www/html/yunxibakebot/

# 3. 配置 Nginx
sudo nano /etc/nginx/sites-available/yunxibakebot
```

Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /var/www/html/yunxibakebot;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:7001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:7001;
    }
}
```

#### 2.4 配置 HTTPS（可选）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx -y

# 申请证书
sudo certbot --nginx -d your-domain.com
```

### 3. 监控与维护

```bash
# 查看服务状态
sudo systemctl status yunxibakebot

# 查看日志
sudo journalctl -u yunxibakebot -f

# 查看资源占用
top -p $(pgrep -f uvicorn)

# 数据库备份
cp data/bot.db data/bot.db.backup.$(date +%Y%m%d)

# 日志轮转
sudo nano /etc/logrotate.d/yunxibakebot
```

---

## 开发规范

### 1. 代码规范

项目遵循以下代码规范：

| 规范 | 说明 |
|------|------|
| **PEP 8** | Python 代码风格规范 |
| **类型注解** | 所有函数必须有类型注解 |
| **中文注释** | 代码注释使用中文 |
| **禁止 Optional[X]** | 使用 `X \| None` 替代 `Optional[X]` |
| **禁止 Union[X, Y]** | 使用 `X \| Y` 替代 `Union[X, Y]` |
| **禁止 SELECT \*** | 必须明确列出字段 |
| **禁止 SQL 拼接** | 必须使用 `?` 参数化绑定 |
| **禁止 print()** | 使用 `logger.debug()` |
| **禁止静默吞异常** | 至少记录 `logger.error` |

### 2. Git 提交规范

提交信息格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

类型（type）：

- **feat**：新功能
- **fix**：Bug 修复
- **docs**：文档更新
- **style**：代码格式调整
- **refactor**：重构
- **test**：测试相关
- **chore**：构建/工具相关

示例：

```
feat(chat): 添加情绪安抚功能

- 添加情绪检测逻辑
- 添加安抚话术生成
- 添加测试用例

Closes #123
```

### 3. 分支管理

```
main/master       # 生产分支
develop          # 开发分支
feature/xxx      # 功能分支
fix/xxx          # 修复分支
release/vX.X.X   # 发布分支
```

工作流程：

1. 从 `develop` 创建功能分支 `feature/xxx`
2. 开发完成后合并回 `develop`
3. 发布时从 `develop` 创建 `release/vX.X.X`
4. 测试通过后合并到 `main/master` 和 `develop`

---

## API 文档

### 1. 自动生成文档

启动服务后访问：

- **Swagger UI**：http://127.0.0.1:7001/docs
- **ReDoc**：http://127.0.0.1:7001/redoc

### 2. 主要 API 端点

#### 2.1 有赞 Webhook

```
POST /api/v1/youzan/webhook
```

接收有赞事件通知（商品上架/下架、订单状态变更等）。

#### 2.2 AI 对话

```
POST /api/v1/chat
```

处理用户消息，返回 AI 回复。

请求体：

```json
{
  "channel": "youzan",
  "user_id": "buyer_123",
  "content": "你们家有哪些面包？",
  "channel_msg_id": "msg_123"
}
```

响应：

```json
{
  "reply": "您好！我们家有以下几种面包：..."
}
```

#### 2.3 管理后台 API

所有管理后台 API 需要在请求头中携带 Token：

```
Authorization: Bearer <ADMIN_API_TOKEN>
```

或使用 Cookie：

```
Cookie: admin_token=<ADMIN_API_TOKEN>
```

主要端点：

- `GET /api/v1/admin/dialog` - AI 对话调试页面
- `GET /api/v1/admin/transfer` - 转人工队列页面
- `GET /api/v1/admin/knowledge` - 知识配置页面
- `GET /api/v1/admin/observability` - 数据观察台页面

---

## 常见问题

### 1. 安装问题

#### Q: pip install 失败怎么办？

**A**: 尝试以下方法：

```bash
# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 升级 pip
pip install --upgrade pip

# 清理缓存
pip cache purge
```

#### Q: 数据库初始化失败怎么办？

**A**: 检查以下内容：

1. 确保 `data/` 目录存在且有写权限
2. 确保 SQLite 版本 >= 3.x
3. 查看错误日志：`python scripts/init_db.py 2>&1 | tee init_db.log`

### 2. 运行问题

#### Q: 启动后访问 http://127.0.0.1:7001/health 返回 404？

**A**: 检查以下内容：

1. 确保服务启动成功，查看启动日志
2. 确保端口 7001 没有被占用：`netstat -ano | findstr :7001`
3. 检查防火墙设置

#### Q: AI 回复很慢怎么办？

**A**: 可能的原因：

1. DeepSeek API 限流：检查 API Key 余额和限流设置
2. 向量搜索慢：检查向量索引是否构建成功
3. 数据库慢：检查 SQLite 数据库文件是否过大

### 3. 部署问题

#### Q: 远程部署后无法访问？

**A**: 检查以下内容：

1. 确保服务已启动：`sudo systemctl status yunxibakebot`
2. 确保端口已开放：`sudo ufw allow 7001`
3. 确保防火墙允许外部访问

#### Q: 如何更新代码？

**A**: 使用以下命令：

```bash
cd /opt/yunxibakebot
git pull
sudo systemctl restart yunxibakebot
```

---

## 贡献指南

### 1. 如何贡献

欢迎贡献代码、文档、Bug 报告等！

#### 1.1 报告 Bug

请在 GitHub Issues 中报告 Bug，包含以下信息：

- 问题描述
- 复现步骤
- 预期行为
- 实际行为
- 环境信息（OS、Python 版本、依赖版本）

#### 1.2 提交功能请求

请在 GitHub Issues 中提交功能请求，包含以下信息：

- 功能描述
- 使用场景
- 预期效果

#### 1.3 提交代码

1. Fork 项目
2. 创建功能分支 `git checkout -b feature/xxx`
3. 提交代码 `git commit -m "feat(xxx): 添加 xxx 功能"`
4. 推送分支 `git push origin feature/xxx`
5. 创建 Pull Request

### 2. 开发环境搭建

```bash
# 1. Fork 项目（在 GitHub 上操作）

# 2. 克隆你的 Fork
git clone https://github.com/your-username/YunxiBakeBot.git
cd YunxiBakeBot

# 3. 添加上游仓库
git remote add upstream https://github.com/original-repo/YunxiBakeBot.git

# 4. 创建开发分支
git checkout -b feature/xxx

# 5. 安装开发依赖
pip install -r requirements-dev.txt

# 6. 运行测试
python -m pytest tests/ -q

# 7. 提交代码
git add .
git commit -m "feat(xxx): 添加 xxx 功能"

# 8. 推送分支
git push origin feature/xxx

# 9. 创建 Pull Request（在 GitHub 上操作）
```

### 3. 代码审查标准

所有 Pull Request 必须通过以下检查：

- ✅ 代码符合规范（PEP 8、类型注解、中文注释等）
- ✅ 所有测试通过（`python -m pytest tests/ -q`）
- ✅ 新增功能包含测试用例
- ✅ 文档已更新（如有必要）
- ✅ 提交信息符合规范

---

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 联系方式

- **项目主页**：https://github.com/your-repo/YunxiBakeBot
- **Issue Tracker**：https://github.com/your-repo/YunxiBakeBot/issues
- **讨论区**：https://github.com/your-repo/YunxiBakeBot/discussions

---

## 致谢

感谢以下开源项目：

- [FastAPI](https://fastapi.tiangolo.com/)
- [DeepSeek](https://www.deepseek.com/)
- [Vue 3](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)
- [Pydantic](https://docs.pydantic.dev/)

---

**最后更新**：2026-06-04
