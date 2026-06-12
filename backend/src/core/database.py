import enum
import logging
import os
import shutil
from datetime import datetime, timezone

from sqlalchemy import Enum as SaEnum, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from src.settings import settings

logger = logging.getLogger(__name__)


def EnumColumn(enum_class, **kwargs):
    return SaEnum(enum_class, values_callable=lambda x: [e.value for e in x], **kwargs)


def _is_sqlite(url: str) -> bool:
    return "sqlite" in url


def _build_engine_args(url: str) -> dict:
    """根据数据库类型构建引擎参数"""
    args = {
        "echo": settings.DEBUG,
        "future": True,
    }
    if _is_sqlite(url):
        args.update({
            "connect_args": {"check_same_thread": False},
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 3600,
        })
    else:
        # PostgreSQL 适配
        args.update({
            "pool_size": 20,
            "max_overflow": 30,
            "pool_timeout": 30,
            "pool_recycle": 1800,
            "pool_pre_ping": True,
        })
    return args


engine = create_async_engine(settings.DATABASE_URL, **_build_engine_args(settings.DATABASE_URL))


# SQLite 专用配置：WAL 模式 + 性能优化
if _is_sqlite(settings.DATABASE_URL):
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA wal_autocheckpoint=1000")  # WAL 文件大小限制
        cursor.close()


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


# ─── SQLite 自动备份 ──────────────────────────────────

async def backup_sqlite_db():
    """备份 SQLite 数据库文件（冷备份）

    备份到 backups/ 目录，保留最近 7 份备份。
    仅在 SQLite 模式下执行，PostgreSQL 模式跳过。
    """
    if not _is_sqlite(settings.DATABASE_URL):
        logger.debug("Skipping backup: not using SQLite")
        return

    db_path = settings.DATABASE_URL.split("///")[-1] if "///" in settings.DATABASE_URL else ""
    if not db_path or not os.path.exists(db_path):
        logger.warning(f"SQLite DB file not found: {db_path}")
        return

    backup_dir = os.path.join(os.path.dirname(db_path), "backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"pm_{timestamp}.db")

    try:
        # 使用 WAL checkpoint 确保数据一致性
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))

        shutil.copy2(db_path, backup_path)
        logger.info(f"SQLite backup created: {backup_path}")

        # 清理旧备份，保留最近 7 份
        backups = sorted(
            [f for f in os.listdir(backup_dir) if f.startswith("pm_") and f.endswith(".db")],
            reverse=True,
        )
        for old_backup in backups[7:]:
            old_path = os.path.join(backup_dir, old_backup)
            os.remove(old_path)
            logger.info(f"Removed old backup: {old_path}")

    except Exception as e:
        logger.error(f"SQLite backup failed: {e}")
