import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship

from src.core.database import Base, EnumColumn


class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(EnumColumn(ProjectStatus), default=ProjectStatus.ACTIVE)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    issues = relationship("Issue", back_populates="project", foreign_keys="Issue.project_id")
    plans = relationship("Plan", back_populates="project", foreign_keys="Plan.project_id")
    notifications = relationship("Notification", foreign_keys="Notification.project_id")
