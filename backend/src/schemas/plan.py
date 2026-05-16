from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from src.models.plan import PlanStatus, PlanSource
from src.models.plan_item import PlanItemStatus


class PlanItemRead(BaseModel):
    id: int
    plan_id: int
    title: str
    description: Optional[str] = None
    status: PlanItemStatus
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
    status: PlanItemStatus = PlanItemStatus.PENDING
    sort_order: int = 0


class PlanItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[PlanItemStatus] = None
    sort_order: Optional[int] = None
    completed_by: Optional[str] = None
    completed_at: Optional[datetime] = None


class PlanCreate(BaseModel):
    project_id: Optional[int] = None
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    status: PlanStatus = PlanStatus.DRAFT
    proposed_by: PlanSource = PlanSource.USER
    current_milestone_id: Optional[int] = None


class PlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[PlanStatus] = None
    current_milestone_id: Optional[int] = None


class PlanRead(BaseModel):
    id: int
    project_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: PlanStatus
    proposed_by: PlanSource
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
