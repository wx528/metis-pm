import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from src.core.database import Base, EnumColumn


class RegistrationStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    STALE = "stale"  # 长期未扫描


class ProjectRegistration(Base):
    """项目登记 — 记录散落在机器各处的项目信息"""
    __tablename__ = "project_registrations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="项目名称")
    path = Column(String(500), nullable=False, comment="项目本地路径")
    description = Column(Text, nullable=True, comment="项目描述")
    tech_stack = Column(String(200), nullable=True, comment="技术栈，如 Python/React/Go，逗号分隔")
    repo_url = Column(String(500), nullable=True, comment="Git 仓库地址")
    language = Column(String(100), nullable=True, comment="主要编程语言")
    framework = Column(String(200), nullable=True, comment="框架，如 FastAPI/Django/Next.js")
    status = Column(EnumColumn(RegistrationStatus), default=RegistrationStatus.ACTIVE, comment="状态")
    notes = Column(Text, nullable=True, comment="备注")
    registered_by = Column(String(100), nullable=True, comment="登记人（Agent 名称）")
    last_scanned_at = Column(DateTime, nullable=True, comment="最后扫描时间")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
