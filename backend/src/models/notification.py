import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base


class NotificationType(str, enum.Enum):
    APPROVAL_NEEDED = "approval_needed"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    MENTION = "mention"
    WORKFLOW_PAUSED = "workflow_paused"
    INFO = "info"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient = Column(String(100), nullable=False, index=True)  # 目标身份，如 "admin"
    type = Column(Enum(NotificationType), default=NotificationType.INFO, nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    entity_type = Column(String(50), nullable=True)  # 关联实体类型: issue, plan, etc.
    entity_id = Column(Integer, nullable=True)        # 关联实体 ID
    read = Column(Boolean, default=False, nullable=False)
    created_by = Column(String(100), nullable=True)   # 触发者身份
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", foreign_keys=[project_id])
