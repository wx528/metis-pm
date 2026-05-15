from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Date
from sqlalchemy.orm import relationship

from src.core.database import Base


class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    phase = Column(String(50), nullable=True)      # 分期标识，如 "phase-1", "phase-2", "MVP"
    status = Column(String(20), default="open")     # open, closed
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    issues = relationship("Issue", back_populates="milestone", foreign_keys="Issue.milestone_id")
