import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base, EnumColumn
from src.core.crypto import encrypt_value, decrypt_value


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
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    ip_address = Column(String(100), nullable=True)
    port = Column(Integer, nullable=True)
    username = Column(String(100), nullable=True)
    _password = Column("password", String(500), nullable=True)       # Fernet 加密存储
    _ssh_key = Column("ssh_key", Text, nullable=True)                # Fernet 加密存储
    _credentials_encrypted = Column("_credentials_encrypted", Integer, default=1)  # 标记凭据是否已加密
    server_type = Column(EnumColumn(ServerType), default=ServerType.OTHER)
    status = Column(EnumColumn(ServerStatus), default=ServerStatus.ACTIVE)
    environment = Column(EnumColumn(ServerEnvironment), default=ServerEnvironment.DEVELOPMENT)
    labels = Column(String(500), nullable=True)         # 逗号分隔
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="servers", foreign_keys=[project_id])

    @property
    def password(self) -> str | None:
        return decrypt_value(self._password)

    @password.setter
    def password(self, value: str | None):
        self._password = encrypt_value(value)

    @property
    def ssh_key(self) -> str | None:
        return decrypt_value(self._ssh_key)

    @ssh_key.setter
    def ssh_key(self, value: str | None):
        self._ssh_key = encrypt_value(value)
