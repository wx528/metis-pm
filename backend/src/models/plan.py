import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from src.core.database import Base


class PlanStatus(str, enum.Enum):
    DRAFT = "draft"               # 草稿
    PENDING_APPROVAL = "pending_approval"  # 待审批
    ACTIVE = "active"             # 进行中
    COMPLETED = "completed"       # 已完成
    ABANDONED = "abandoned"       # 已废弃


class PlanSource(str, enum.Enum):
    USER = "user"
    AI_AGENT = "ai_agent"
    COLLABORATIVE = "collaborative"


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(PlanStatus), default=PlanStatus.DRAFT)
    proposed_by = Column(Enum(PlanSource), default=PlanSource.USER)
    approved_by = Column(String(20), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    reject_reason = Column(Text, nullable=True)
    current_milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    current_milestone = relationship("Milestone", foreign_keys=[current_milestone_id])
    plan_items = relationship("PlanItem", back_populates="plan", cascade="all, delete-orphan", order_by="PlanItem.sort_order")
