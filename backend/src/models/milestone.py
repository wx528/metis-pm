import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Enum, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base


class MilestoneStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    phase = Column(String(50), nullable=True)
    status = Column(Enum(MilestoneStatus), default=MilestoneStatus.OPEN)
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="milestones", foreign_keys=[project_id])
    issues = relationship("Issue", back_populates="milestone", foreign_keys="Issue.milestone_id")
