import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base, EnumColumn


class FeedbackCategory(str, enum.Enum):
    BUG = "bug"                    # 遇到 Bug
    FEATURE_REQUEST = "feature_request"  # 希望新增功能
    IMPROVEMENT = "improvement"    # 改进建议
    UX = "ux"                      # 使用体验
    WORKFLOW = "workflow"          # 工作流相关
    OTHER = "other"                # 其他


class FeedbackStatus(str, enum.Enum):
    OPEN = "open"                  # 待处理
    ACKNOWLEDGED = "acknowledged"  # 已确认
    IN_PROGRESS = "in_progress"   # 处理中
    RESOLVED = "resolved"          # 已解决
    WONT_FIX = "wont_fix"         # 不修复


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(EnumColumn(FeedbackCategory), default=FeedbackCategory.OTHER, nullable=False)
    status = Column(EnumColumn(FeedbackStatus), default=FeedbackStatus.OPEN, nullable=False)
    priority = Column(String(10), default="P2")  # P0-P3
    # 提交者信息
    submitted_by = Column(String(100), nullable=False)  # agent 身份，如 "ai_agent", "mate"
    submitted_by_role = Column(String(50), nullable=True)  # 角色类型: agent, mate, tester, etc.
    # 关联上下文
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    entity_type = Column(String(50), nullable=True)  # 关联实体类型: issue, plan, workflow, etc.
    entity_id = Column(Integer, nullable=True)        # 关联实体 ID
    # 产品信息（外部 Agent 提交时必填）
    product_name = Column(String(200), nullable=True)       # 产品名称
    product_version = Column(String(100), nullable=True)    # 产品版本
    # 管理员回复
    admin_reply = Column(Text, nullable=True)
    replied_by = Column(String(100), nullable=True)
    replied_at = Column(DateTime, nullable=True)
    # 时间
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", foreign_keys=[project_id])
