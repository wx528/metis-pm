from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


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


class PlanItemCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    status: str = "pending"
    sort_order: int = 0


class PlanItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None
    completed_by: Optional[str] = None
    completed_at: Optional[datetime] = None


class PlanCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    status: str = "draft"
    proposed_by: str = "user"
    current_milestone_id: Optional[int] = None


class PlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    current_milestone_id: Optional[int] = None


class PlanRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    proposed_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    current_milestone_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlanReadWithItems(PlanRead):
    plan_items: List[PlanItemRead] = []
