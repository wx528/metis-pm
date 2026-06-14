# ─── Stage 1: 依赖安装 ────────────────────────────────
FROM python:3.11-slim AS deps

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

# ─── Stage 2: 运行时 ──────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# 仅复制安装好的包
COPY --from=deps /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN groupadd -r pm && useradd -r -g pm -d /data -s /sbin/nologin pm

# 数据目录
RUN mkdir -p /data/backups && chown -R pm:pm /data

# 环境变量
ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite+aiosqlite:////data/metis_pm.db

EXPOSE 8000

USER pm

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
