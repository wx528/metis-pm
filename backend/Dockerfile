FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.cloud.tencent.com/pypi/simple -r requirements.txt

# Copy code
COPY . .

# Create data directory for SQLite
RUN mkdir -p /data

# Environment
ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite+aiosqlite:///data/project_manager.db

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
