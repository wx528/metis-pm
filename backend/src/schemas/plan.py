from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class PlanCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    proposed_by: Optional[str] = None
    project_id: Optional[int] = None


class PlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class PlanRead(BaseModel):
    id: int
    project_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: str
    proposed_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlanReadWithItems(PlanRead):
    plan_items: List["PlanItemRead"] = []


class PlanReadWithStats(PlanRead):
    item_count: int = 0
    item_done_count: int = 0


class PlanItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    sort_order: int = 0


class PlanItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None
    completed_by: Optional[str] = None


class PlanItemRead(BaseModel):
    id: int
    plan_id: int
    title: str
    description: Optional[str] = None
    status: str
    sort_order: int
    completed_by: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
