from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.core.database import engine, Base
from src.routes import api_router
from src.settings import settings


MIGRATIONS = [
    "ALTER TABLE plans ADD COLUMN reject_reason TEXT",
    "ALTER TABLE plans ADD COLUMN current_milestone_id INTEGER REFERENCES milestones(id)",
]


async def _run_migrations(conn):
    result = await conn.execute(text("PRAGMA table_info(plans)"))
    existing = {row[1] for row in result.fetchall()}
    for sql in MIGRATIONS:
        col_name = sql.split("ADD COLUMN ")[1].split()[0]
        if col_name not in existing:
            await conn.execute(text(sql))


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _run_migrations(conn)
    yield


app = FastAPI(
    title="Project Manager",
    version="0.2.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": "project_manager"}
