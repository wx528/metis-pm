import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime

from src.core.database import Base


class ServerType(str, enum.Enum):
    WEB = "web"
    DB = "db"
    CACHE = "cache"
    WORKER = "worker"
    OTHER = "other"


class ServerStatus(str, enum.Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"
    DECOMMISSIONED = "decommissioned"


class ServerEnvironment(str, enum.Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    ip_address = Column(String(100), nullable=True)
    port = Column(Integer, nullable=True)
    username = Column(String(100), nullable=True)
    password = Column(String(200), nullable=True)       # 明文存储（仅本地/内网）
    ssh_key = Column(Text, nullable=True)               # SSH 私钥
    server_type = Column(String(20), default="other")   # web | db | cache | worker | other
    status = Column(String(20), default="active")       # active | maintenance | offline | decommissioned
    environment = Column(String(20), default="development")  # production | staging | development
    labels = Column(String(500), nullable=True)         # 逗号分隔
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
