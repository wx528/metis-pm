import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from src.core.database import Base


class IssueType(str, enum.Enum):
    BUG = "bug"
    FEATURE = "feature"
    TASK = "task"
    IMPROVEMENT = "improvement"
    DOCUMENTATION = "documentation"
    IDEA = "idea"


class IssueStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DEFERRED = "deferred"       # 暂缓 - 推到后期阶段处理
    CLOSED = "closed"
    CANCELLED = "cancelled"


class IssuePriority(str, enum.Enum):
    P0 = "P0"   # 紧急/阻塞 - 必须立即修复，影响核心功能
    P1 = "P1"   # 高优先级 - 重要功能，当前阶段必须完成
    P2 = "P2"   # 中优先级 - 需要完成，但不阻塞当前进度
    P3 = "P3"   # 低优先级 - 有则更好，可推迟到后期


class IssueSource(str, enum.Enum):
    USER = "user"               # 用户创建
    AI_AGENT = "ai_agent"       # AI coding agent 创建
    COLLABORATIVE = "collaborative"  # 人机协作创建


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    issue_type = Column(Enum(IssueType), default=IssueType.TASK, nullable=False)
    status = Column(Enum(IssueStatus), default=IssueStatus.OPEN, nullable=False)
    priority = Column(Enum(IssuePriority), default=IssuePriority.P2, nullable=False)
    source = Column(Enum(IssueSource), default=IssueSource.USER, nullable=False)
    assignee = Column(String(100), nullable=True)
    labels = Column(String(500), nullable=True)  # 逗号分隔的标签
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=True)
    deferred_to_milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=True)  # 推迟到哪个阶段
    deferred_reason = Column(Text, nullable=True)   # 推迟原因
    parent_id = Column(Integer, ForeignKey("issues.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="issues", foreign_keys=[project_id])
    milestone = relationship("Milestone", back_populates="issues", foreign_keys=[milestone_id])
    deferred_to_milestone = relationship("Milestone", foreign_keys=[deferred_to_milestone_id])
    comments = relationship("Comment", back_populates="issue", cascade="all, delete-orphan")
