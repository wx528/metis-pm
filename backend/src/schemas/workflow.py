"""Phase 6 — 工作流 Schema"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from src.models.workflow import WorkflowTrigger, WorkflowStatus, StepType, OnFailure, WorkflowRunStatus


# ── WorkflowStep ──────────────────────────────────

class WorkflowStepCreate(BaseModel):
    step_type: StepType
    name: Optional[str] = None
    config: Optional[dict] = None
    sort_order: int = 0
    timeout_seconds: int = 300
    on_failure: OnFailure = OnFailure.ABORT


class WorkflowStepRead(BaseModel):
    id: int
    workflow_id: int
    step_type: str
    name: Optional[str] = None
    config: Optional[dict] = None
    sort_order: int
    timeout_seconds: int
    on_failure: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Workflow ──────────────────────────────────────

class WorkflowCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    project_id: Optional[int] = None
    trigger: WorkflowTrigger = WorkflowTrigger.MANUAL
    trigger_config: Optional[dict] = None
    status: WorkflowStatus = WorkflowStatus.ACTIVE
    steps: List[WorkflowStepCreate] = []


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    trigger: Optional[WorkflowTrigger] = None
    trigger_config: Optional[dict] = None
    status: Optional[WorkflowStatus] = None


class WorkflowRead(BaseModel):
    id: int
    project_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    trigger: str
    trigger_config: Optional[dict] = None
    status: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkflowReadWithSteps(WorkflowRead):
    steps: List[WorkflowStepRead] = []


# ── WorkflowRun ───────────────────────────────────

class WorkflowRunRead(BaseModel):
    id: int
    workflow_id: int
    triggered_by: Optional[str] = None
    status: str
    current_step_index: int
    context: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkflowRunReadWithDetails(WorkflowRunRead):
    workflow_name: Optional[str] = None
