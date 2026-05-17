# CLAUDE.md — 芸熙烘焙 AI 客服

## 项目概述

芸熙烘焙 AI 客服系统，覆盖 3 个渠道（有赞小程序、企微 1 对 1、企微群），使用 DeepSeek API 作为 LLM 大脑，SQLite 存储，单服务器部署。

## 技术栈

- Python 3.11+ / FastAPI / Uvicorn
- SQLite (aiosqlite, WAL mode)
- DeepSeek (OpenAI 协议, openai SDK)
- Nginx (HTTPS 反向代理)
- 域名: hclstudio.cn (已备案)

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
