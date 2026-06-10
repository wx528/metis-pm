"""Phase 6 — 工作流引擎模型"""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from src.core.database import Base, EnumColumn


class WorkflowTrigger(str, enum.Enum):
    ON_ISSUE_CREATED = "on_issue_created"
    ON_PLAN_APPROVED = "on_plan_approved"
    ON_SCHEDULE = "on_schedule"
    MANUAL = "manual"


class WorkflowStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class StepType(str, enum.Enum):
    CREATE_ISSUE = "create_issue"
    UPDATE_ISSUE = "update_issue"
    NOTIFY = "notify"
    WAIT_APPROVAL = "wait_approval"
    PROPOSE_PLAN = "propose_plan"


class OnFailure(str, enum.Enum):
    SKIP = "skip"
    RETRY = "retry"
    ABORT = "abort"
    NOTIFY_HUMAN = "notify_human"


class WorkflowRunStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"
    ABORTED = "aborted"


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    trigger = Column(EnumColumn(WorkflowTrigger), default=WorkflowTrigger.MANUAL, nullable=False)
    trigger_config = Column(JSON, nullable=True)  # 触发条件配置，如 {"issue_type": "bug"}
    status = Column(EnumColumn(WorkflowStatus), default=WorkflowStatus.ACTIVE)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", foreign_keys=[project_id])
    steps = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowStep.sort_order")
    runs = relationship("WorkflowRun", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False, index=True)
    step_type = Column(EnumColumn(StepType), nullable=False)
    name = Column(String(200), nullable=True)  # 步骤名称
    config = Column(JSON, nullable=True)  # 步骤配置，如 {"priority": "P1", "issue_type": "bug"}
    sort_order = Column(Integer, default=0)
    timeout_seconds = Column(Integer, default=300)  # 超时秒数，默认 5 分钟
    on_failure = Column(EnumColumn(OnFailure), default=OnFailure.ABORT)
    
    # 新增：工作流灵活性字段
    condition = Column(Text, nullable=True)  # 条件表达式，如 "context.status == 'failed'"
    next_step_id = Column(Integer, ForeignKey("workflow_steps.id"), nullable=True)  # 条件为真时的下一步
    else_step_id = Column(Integer, ForeignKey("workflow_steps.id"), nullable=True)  # 条件为假时的下一步
    parallel_group = Column(String(50), nullable=True)  # 并行组标识（同组步骤并行执行）
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    workflow = relationship("Workflow", back_populates="steps")


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False, index=True)
    triggered_by = Column(String(100), nullable=True)  # 触发者 + 原因
    status = Column(EnumColumn(WorkflowRunStatus), default=WorkflowRunStatus.RUNNING)
    current_step_index = Column(Integer, default=0)
    context = Column(JSON, nullable=True)  # 步骤间传递的上下文
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    workflow = relationship("Workflow", back_populates="runs")
