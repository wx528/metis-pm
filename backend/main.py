import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.core.database import engine, Base
from src.routes import api_router
from src.settings import settings

logger = logging.getLogger(__name__)

# Phase 4 迁移：多项目 + 通知
MIGRATIONS = [
    # 旧迁移
    "ALTER TABLE plans ADD COLUMN reject_reason TEXT",
    "ALTER TABLE plans ADD COLUMN current_milestone_id INTEGER REFERENCES milestones(id)",
    # Phase 4: 所有现有表添加 project_id
    "ALTER TABLE issues ADD COLUMN project_id INTEGER REFERENCES projects(id)",
    "ALTER TABLE milestones ADD COLUMN project_id INTEGER REFERENCES projects(id)",
    "ALTER TABLE plans ADD COLUMN project_id INTEGER REFERENCES projects(id)",
    "ALTER TABLE servers ADD COLUMN project_id INTEGER REFERENCES projects(id)",
    "ALTER TABLE activity_logs ADD COLUMN project_id INTEGER REFERENCES projects(id)",
]


async def _run_migrations(conn):
    """运行数据库迁移"""
    # 先检查 projects 表是否存在（新数据库不需要迁移旧列）
    result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"))
    projects_exists = result.fetchone() is not None

    if not projects_exists:
        # projects 表不存在 → 全新数据库，create_all 会创建所有表，跳过 ALTER TABLE
        return

    # 检查 plans 表的列（旧迁移）
    result = await conn.execute(text("PRAGMA table_info(plans)"))
    existing_plans_cols = {row[1] for row in result.fetchall()}

    # 旧迁移
    if "reject_reason" not in existing_plans_cols:
        await conn.execute(text("ALTER TABLE plans ADD COLUMN reject_reason TEXT"))
    if "current_milestone_id" not in existing_plans_cols:
        await conn.execute(text("ALTER TABLE plans ADD COLUMN current_milestone_id INTEGER REFERENCES milestones(id)"))

    # Phase 4 迁移：为现有表添加 project_id
    for table in ["issues", "milestones", "plans", "servers", "activity_logs"]:
        result = await conn.execute(text(f"PRAGMA table_info({table})"))
        existing_cols = {row[1] for row in result.fetchall()}
        if "project_id" not in existing_cols:
            try:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN project_id INTEGER REFERENCES projects(id)"))
                logger.info(f"Added project_id column to {table}")
            except Exception as e:
                logger.warning(f"Failed to add project_id to {table}: {e}")

    # 创建默认项目并回填数据
    result = await conn.execute(text("SELECT COUNT(*) FROM projects WHERE slug = 'default'"))
    default_count = result.scalar()
    if default_count == 0:
        await conn.execute(text(
            "INSERT INTO projects (name, slug, description, status, owner) "
            "VALUES ('Default Project', 'default', 'Default project for existing data', 'active', 'admin')"
        ))
        logger.info("Created default project")

    # 回填 project_id
    result = await conn.execute(text("SELECT id FROM projects WHERE slug = 'default' LIMIT 1"))
    default_project_row = result.fetchone()
    if default_project_row:
        default_project_id = default_project_row[0]
        for table in ["issues", "milestones", "plans", "servers", "activity_logs"]:
            try:
                await conn.execute(text(
                    f"UPDATE {table} SET project_id = {default_project_id} WHERE project_id IS NULL"
                ))
            except Exception as e:
                logger.warning(f"Failed to backfill project_id in {table}: {e}")
        logger.info(f"Backfilled project_id={default_project_id} for existing data")

    # Phase 4.1: notifications 表添加 updated_at 列
    result = await conn.execute(text("PRAGMA table_info(notifications)"))
    notif_cols = {row[1] for row in result.fetchall()}
    if "updated_at" not in notif_cols:
        try:
            await conn.execute(text("ALTER TABLE notifications ADD COLUMN updated_at DATETIME"))
            logger.info("Added updated_at column to notifications")
        except Exception as e:
            logger.warning(f"Failed to add updated_at to notifications: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _run_migrations(conn)
    yield


app = FastAPI(
    title="Project Manager",
    version="0.5.0",
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
    return {"status": "ok", "app": "project_manager", "version": "0.5.0"}
