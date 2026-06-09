import enum
from sqlalchemy import Enum as SaEnum, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from src.settings import settings


def EnumColumn(enum_class, **kwargs):
    return SaEnum(enum_class, values_callable=lambda x: [e.value for e in x], **kwargs)


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    connect_args={"check_same_thread": False},
    # SQLite 连接池优化
    # pool_size: 保持的连接数，SQLite 单文件建议较小值
    # max_overflow: 允许额外创建的连接，应对突发并发
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,  # 等待可用连接的超时时间（秒）
    pool_recycle=3600,  # 连接回收时间（秒），防止长时间持有
)

# SQLite 启用 WAL 模式以支持并发读写
# WAL 模式下：读不阻塞写，写不阻塞读，允许多读 + 一写并发
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")  # 平衡性能与可靠性
    cursor.execute("PRAGMA temp_store=MEMORY")   # 临时表存内存，减少磁盘 I/O
    cursor.close()


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()
