from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    entity_type = Column(String(20), nullable=False)  # issue | plan | plan_item | server | milestone
    entity_id = Column(Integer, nullable=False)
    action = Column(String(30), nullable=False)       # created | updated | status_changed | approved | rejected | deferred | commented | completed
    old_value = Column(JSON, nullable=True)           # 变更前
    new_value = Column(JSON, nullable=True)           # 变更后
    actor = Column(String(20), default="user")        # user | ai_agent
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", foreign_keys=[project_id])
