# 芸熙烘焙 AI 客服 — 生产环境 Docker 镜像
# 构建：docker build -t yunxi-bakebot .
# 运行：docker-compose up -d

FROM python:3.11-slim-bookworm

# 环境配置
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# 安装系统依赖（用于密码学库编译）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# 依赖层缓存（先复制锁文件，利用 Docker 层缓存）
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-dev.txt

# 下载 sentence-transformers 模型（构建时预缓存，避免启动时下载超时）
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')" || true

# 复制应用代码
COPY . .

# 运行时数据目录
RUN mkdir -p data

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://127.0.0.1:7001/health').raise_for_status()" || exit 1

EXPOSE 7001

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7001"]
