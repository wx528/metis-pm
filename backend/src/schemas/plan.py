from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

PlanStatusType = Literal["draft", "pending_approval", "active", "completed", "abandoned"]
PlanSourceType = Literal["user", "ai_agent", "collaborative"]
PlanItemStatusType = Literal["pending", "in_progress", "done", "blocked"]


class PlanItemRead(BaseModel):
    id: int
    plan_id: int
    title: str
    description: Optional[str] = None
    status: PlanItemStatusType
    sort_order: int
    completed_by: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlanItemCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    status: PlanItemStatusType = "pending"
    sort_order: int = 0


class PlanItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[PlanItemStatusType] = None
    sort_order: Optional[int] = None
    completed_by: Optional[str] = None
    completed_at: Optional[datetime] = None


class PlanCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    status: PlanStatusType = "draft"
    proposed_by: PlanSourceType = "user"
    current_milestone_id: Optional[int] = None


class PlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[PlanStatusType] = None
    current_milestone_id: Optional[int] = None


class PlanRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: PlanStatusType
    proposed_by: PlanSourceType
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    current_milestone_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlanReadWithItems(PlanRead):
    plan_items: List[PlanItemRead] = []


class PlanReadWithStats(PlanRead):
    item_count: int = 0
    item_done_count: int = 0
