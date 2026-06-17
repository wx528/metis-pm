FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi uvicorn[standard] sqlalchemy[asyncio] aiosqlite pydantic pydantic-settings python-multipart python-dotenv pyjwt[crypto] httpx bcrypt

COPY . .

RUN groupadd -r pm && useradd -r -g pm -d /data -s /sbin/nologin pm
RUN mkdir -p /data && chown -R pm:pm /data

ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite+aiosqlite:////data/metis_pm.db

EXPOSE 8000

USER pm

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
