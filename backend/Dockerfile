# ─── Stage 1: 依赖安装 ────────────────────────────────
FROM python:3.11-slim AS deps

WORKDIR /app

# 系统依赖（bcrypt 编译需要）
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Stage 2: 运行时 ──────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# 仅复制安装好的包
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN groupadd -r pm && useradd -r -g pm -d /data -s /sbin/nologin pm

# 数据目录
RUN mkdir -p /data/backups && chown -R pm:pm /data

# 环境变量
ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite+aiosqlite:////data/project_manager.db

EXPOSE 8000

USER pm

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
