import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, select

from src.core.database import engine, Base
from src.routes import api_router
from src.settings import settings
from src.core.crypto import encrypt_value
from src.core.message_queue import message_queue, create_message_queue_tables
from src.core.workflow_timeout import workflow_timeout_monitor


def _get_version() -> str:
    env_version = os.environ.get("APP_VERSION", "").strip()
    if env_version:
        return env_version
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "0.0.0"


APP_VERSION = _get_version()

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

    # Phase 6.1: 添加 _credentials_encrypted 列（必须存在，不依赖 ENCRYPTION_KEY）
    result = await conn.execute(text("PRAGMA table_info(servers)"))
    server_cols = {row[1] for row in result.fetchall()}
    if "_credentials_encrypted" not in server_cols:
        try:
            await conn.execute(text("ALTER TABLE servers ADD COLUMN _credentials_encrypted INTEGER DEFAULT 0"))
            logger.info("Added _credentials_encrypted column to servers")
        except Exception as e:
            logger.warning(f"Failed to add _credentials_encrypted to servers: {e}")

    # Phase 6.2: 加密已有明文凭据（需要 ENCRYPTION_KEY）
    if settings.ENCRYPTION_KEY:
        try:
            result = await conn.execute(
                text("SELECT id, password, ssh_key FROM servers WHERE _credentials_encrypted = 0")
            )
            rows = result.fetchall()
            for row in rows:
                sid, pwd, key = row
                enc_pwd = encrypt_value(pwd) if pwd else None
                enc_key = encrypt_value(key) if key else None
                await conn.execute(
                    text("UPDATE servers SET password = :pwd, ssh_key = :key, _credentials_encrypted = 1 WHERE id = :id"),
                    {"pwd": enc_pwd, "key": enc_key, "id": sid},
                )
            if rows:
                logger.info(f"Encrypted credentials for {len(rows)} server(s)")
        except Exception as e:
            logger.warning(f"Failed to encrypt existing credentials: {e}")

    # Phase 7: proposed_by_name / created_by 字段
    result = await conn.execute(text("PRAGMA table_info(plans)"))
    plans_cols = {row[1] for row in result.fetchall()}
    if "proposed_by_name" not in plans_cols:
        try:
            await conn.execute(text("ALTER TABLE plans ADD COLUMN proposed_by_name VARCHAR(100)"))
            logger.info("Added proposed_by_name column to plans")
        except Exception as e:
            logger.warning(f"Failed to add proposed_by_name to plans: {e}")

    result = await conn.execute(text("PRAGMA table_info(issues)"))
    issues_cols = {row[1] for row in result.fetchall()}
    if "created_by" not in issues_cols:
        try:
            await conn.execute(text("ALTER TABLE issues ADD COLUMN created_by VARCHAR(100)"))
            logger.info("Added created_by column to issues")
        except Exception as e:
            logger.warning(f"Failed to add created_by to issues: {e}")

    # Phase 8: agent_memories 表
    result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_memories'"))
    if not result.fetchone():
        await conn.execute(text("""
            CREATE TABLE agent_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id VARCHAR(100) NOT NULL,
                key VARCHAR(200) NOT NULL,
                value TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("CREATE INDEX ix_agent_memories_agent_id ON agent_memories(agent_id)"))
        logger.info("Created agent_memories table")

    result = await conn.execute(text("PRAGMA table_info(comments)"))
    comments_cols = {row[1] for row in result.fetchall()}
    if "parent_id" not in comments_cols:
        try:
            await conn.execute(text("ALTER TABLE comments ADD COLUMN parent_id INTEGER REFERENCES comments(id)"))
            logger.info("Added parent_id column to comments")
        except Exception as e:
            logger.warning(f"Failed to add parent_id to comments: {e}")
    if "comment_type" not in comments_cols:
        try:
            await conn.execute(text("ALTER TABLE comments ADD COLUMN comment_type VARCHAR(20) DEFAULT 'normal'"))
            logger.info("Added comment_type column to comments")
        except Exception as e:
            logger.warning(f"Failed to add comment_type to comments: {e}")
    if "read_by" not in comments_cols:
        try:
            await conn.execute(text("ALTER TABLE comments ADD COLUMN read_by VARCHAR(100)"))
            logger.info("Added read_by column to comments")
        except Exception as e:
            logger.warning(f"Failed to add read_by to comments: {e}")
    if "read_at" not in comments_cols:
        try:
            await conn.execute(text("ALTER TABLE comments ADD COLUMN read_at DATETIME"))
            logger.info("Added read_at column to comments")
        except Exception as e:
            logger.warning(f"Failed to add read_at to comments: {e}")

    # Phase 10: workflow_steps 添加条件分支字段
    result = await conn.execute(text("PRAGMA table_info(workflow_steps)"))
    step_cols = {row[1] for row in result.fetchall()}
    for col, col_type in [
        ("condition", "TEXT"),
        ("next_step_id", "INTEGER"),
        ("else_step_id", "INTEGER"),
        ("parallel_group", "VARCHAR(50)"),
    ]:
        if col not in step_cols:
            try:
                await conn.execute(text(f"ALTER TABLE workflow_steps ADD COLUMN {col} {col_type}"))
                logger.info(f"Added {col} column to workflow_steps")
            except Exception as e:
                logger.warning(f"Failed to add {col} to workflow_steps: {e}")


async def _check_stuck_workflows():
    """后台任务：定期检测卡住的工作流并发送通知"""
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.core.database import AsyncSessionLocal
    from src.core.notification import create_notification
    from src.models.issue import Issue, IssueStatus
    from src.models.plan import Plan, PlanStatus
    from src.models.notification import NotificationType
    
    while True:
        try:
            await asyncio.sleep(3600)  # 每小时检查一次
            
            async with AsyncSessionLocal() as db:
                now = datetime.now(timezone.utc)
                threshold = now - timedelta(hours=24)
                
                # 检测卡住的 Issue（in_progress/review 超过 24 小时）
                stuck_issues_result = await db.execute(
                    select(Issue).where(
                        Issue.status.in_([IssueStatus.IN_PROGRESS, IssueStatus.REVIEW]),
                        Issue.updated_at <= threshold,
                    )
                )
                stuck_issues = stuck_issues_result.scalars().all()
                
                for issue in stuck_issues:
                    await create_notification(
                        db,
                        recipient="admin",
                        type=NotificationType.TASK_FAILED,
                        title=f"⚠️ Issue #{issue.id} 已卡住 {issue.status} 超过 24 小时",
                        body=f"{issue.title}\n负责人: {issue.assignee or '未分配'}\n请检查工作流是否阻塞。",
                        entity_type="issue",
                        entity_id=issue.id,
                    )
                
                # 检测卡住的 Plan（pending_approval 超过 24 小时）
                stuck_plans_result = await db.execute(
                    select(Plan).where(
                        Plan.status == PlanStatus.PENDING_APPROVAL,
                        Plan.updated_at <= threshold,
                    )
                )
                stuck_plans = stuck_plans_result.scalars().all()
                
                for plan in stuck_plans:
                    await create_notification(
                        db,
                        recipient="admin",
                        type=NotificationType.APPROVAL_NEEDED,
                        title=f"⏰ Plan '{plan.title}' 等待审批超过 24 小时",
                        body=f"由 {plan.proposed_by} 提议，请及时审批。",
                        entity_type="plan",
                        entity_id=plan.id,
                    )
                
                if stuck_issues or stuck_plans:
                    logger.info(f"Stuck workflow check: {len(stuck_issues)} issues, {len(stuck_plans)} plans")
                    
        except Exception as e:
            logger.error(f"Stuck workflow check failed: {e}")
            await asyncio.sleep(3600)


async def _recover_workflow_runs():
    """启动时恢复未完成的 WorkflowRun（断点续传）

    利用 WorkflowStepRun 记录，从最后成功步骤恢复：
    - 已完成的步骤（step_run.status=completed）直接跳过
    - 正在运行的步骤（step_run.status=running）重置为 pending 重新执行
    - 未开始的步骤正常执行
    """
    from src.core.database import AsyncSessionLocal
    from src.models.workflow import WorkflowRun, WorkflowRunStatus, Workflow, WorkflowStepRun, StepRunStatus
    from src.core.workflow_engine import WorkflowEngine
    from sqlalchemy.orm import selectinload

    try:
        async with AsyncSessionLocal() as db:
            # 恢复 RUNNING 和 WAITING_APPROVAL 状态的 Run
            result = await db.execute(
                select(WorkflowRun).where(
                    WorkflowRun.status.in_([WorkflowRunStatus.RUNNING, WorkflowRunStatus.WAITING_APPROVAL])
                ).options(
                    selectinload(WorkflowRun.workflow).selectinload(Workflow.steps)
                )
            )
            stuck_runs = result.scalars().all()

            if not stuck_runs:
                return

            logger.info(f"Recovering {len(stuck_runs)} incomplete workflow run(s)")

            for run in stuck_runs:
                try:
                    workflow = run.workflow
                    if not workflow:
                        logger.warning(f"WorkflowRun #{run.id} has no workflow, marking as failed")
                        run.status = WorkflowRunStatus.FAILED
                        run.error_message = "Workflow deleted during execution"
                        run.completed_at = datetime.now(timezone.utc)
                        continue

                    # WAITING_APPROVAL 状态不需要恢复执行，等待审批即可
                    if run.status == WorkflowRunStatus.WAITING_APPROVAL:
                        logger.info(f"WorkflowRun #{run.id} is waiting approval, skipping recovery")
                        continue

                    # 将 running 状态的 step_run 重置为 pending（可能崩溃中断了）
                    step_run_result = await db.execute(
                        select(WorkflowStepRun).where(
                            WorkflowStepRun.run_id == run.id,
                            WorkflowStepRun.status == StepRunStatus.RUNNING,
                        )
                    )
                    for sr in step_run_result.scalars().all():
                        sr.status = StepRunStatus.PENDING
                        sr.started_at = None
                    await db.commit()

                    # 从当前步骤继续执行（已完成的步骤会被跳过）
                    engine = WorkflowEngine(db)
                    await engine._execute_steps(run, workflow)
                    logger.info(f"Recovered WorkflowRun #{run.id}")
                except Exception as e:
                    logger.error(f"Failed to recover WorkflowRun #{run.id}: {e}")
                    run.status = WorkflowRunStatus.FAILED
                    run.error_message = f"Recovery failed: {e}"
                    run.completed_at = datetime.now(timezone.utc)

            await db.commit()
    except Exception as e:
        logger.error(f"Workflow recovery failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _run_migrations(conn)
    
    # 创建消息队列表
    await create_message_queue_tables()
    
    # 启动消息队列消费者
    await message_queue.start()
    
    # 恢复未完成的 WorkflowRun
    await _recover_workflow_runs()
    
    # 启动后台任务
    tasks = [
        asyncio.create_task(_check_stuck_workflows()),
        asyncio.create_task(workflow_timeout_monitor()),
    ]
    yield
    
    # 清理
    for task in tasks:
        task.cancel()
    await message_queue.stop()


app = FastAPI(
    title="Project Manager",
    version=APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Prometheus 监控：自动收集请求延迟、吞吐量、错误率等指标
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    instrumentator = Instrumentator()
    instrumentator.instrument(app).expose(app)
    logger.info("Prometheus metrics exposed at /metrics")
except ImportError:
    logger.warning("prometheus-fastapi-instrumentator not installed, metrics disabled")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# API 限流：每秒 20 次，每分钟 200 次，突发 30 次
from src.core.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware, per_second=20, per_minute=200, burst=30)

app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": "project_manager", "version": APP_VERSION}
