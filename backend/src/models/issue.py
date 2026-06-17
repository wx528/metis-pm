import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base, EnumColumn


class IssueType(str, enum.Enum):
    BUG = "bug"
    FEATURE = "feature"
    TASK = "task"


class IssueStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IssuePriority(str, enum.Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    issue_type = Column(EnumColumn(IssueType), default=IssueType.TASK, nullable=False)
    status = Column(EnumColumn(IssueStatus), default=IssueStatus.OPEN, nullable=False)
    priority = Column(EnumColumn(IssuePriority), default=IssuePriority.P2, nullable=False)
    assignee_role = Column(String(50), nullable=True)
    source_role = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="issues", foreign_keys=[project_id])
    comments = relationship("Comment", back_populates="issue", cascade="all, delete-orphan")
