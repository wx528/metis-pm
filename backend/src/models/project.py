import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base


class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    repo_url = Column(String(500), nullable=True)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    owner = Column(String(100), nullable=True)
    default_milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # relationships
    issues = relationship("Issue", back_populates="project", foreign_keys="Issue.project_id")
    milestones = relationship("Milestone", back_populates="project", foreign_keys="Milestone.project_id")
    plans = relationship("Plan", back_populates="project", foreign_keys="Plan.project_id")
    servers = relationship("Server", back_populates="project", foreign_keys="Server.project_id")
    notifications = relationship("Notification", foreign_keys="Notification.project_id")
