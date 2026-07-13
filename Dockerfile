# 芸熙烘焙 AI 客服 — 生产环境 Docker 镜像
# 构建：docker build -t yunxi-bakebot .
# 运行：docker-compose up -d

FROM python:3.11-slim-bookworm@sha256:f5cf0344c9886ff24d34797578d5d7dd6e8911ae0fe5962bb55d0f89603ec361 AS builder

# 环境配置
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    TZ=Asia/Shanghai

WORKDIR /build

# 安装系统依赖（用于密码学库编译）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

ARG PYTORCH_CPU_INDEX_URL=https://download.pytorch.org/whl/cpu

# 依赖层缓存（先复制锁文件，利用 Docker 层缓存）
COPY requirements.txt ./
RUN pip wheel --no-cache-dir --wheel-dir /wheels \
        --index-url "${PYTORCH_CPU_INDEX_URL}" 'torch==2.12.0+cpu' && \
    pip wheel --no-cache-dir --wheel-dir /wheels \
        --find-links /wheels -r requirements.txt

FROM python:3.11-slim-bookworm@sha256:f5cf0344c9886ff24d34797578d5d7dd6e8911ae0fe5962bb55d0f89603ec361 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    TZ=Asia/Shanghai \
    DB_PATH=/app/data/bot.db \
    EMBEDDING_INDEX_DIR=/app/data

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY --from=builder /build/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --no-index --find-links /wheels \
        -r /tmp/requirements.txt && \
    pip uninstall --yes wheel jaraco.context && \
    rm -rf /wheels /tmp/requirements.txt

# 复制应用代码
COPY . .

# 运行时数据目录
RUN useradd --create-home --uid 10001 yunxi && \
    mkdir -p data && \
    chown -R yunxi:yunxi /app

USER yunxi

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import httpx; response = httpx.get('http://127.0.0.1:7001/ready'); response.raise_for_status()" || exit 1

EXPOSE 7001

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7001", "--workers", "1"]
