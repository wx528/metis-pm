from datetime import date, datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field

MilestoneStatusType = Literal["open", "closed"]


class MilestoneCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    phase: Optional[str] = None
    due_date: Optional[date] = None


class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    phase: Optional[str] = None
    status: Optional[MilestoneStatusType] = None
    due_date: Optional[date] = None


class MilestoneRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    phase: Optional[str] = None
    status: MilestoneStatusType
    due_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MilestoneReadWithStats(MilestoneRead):
    """带统计信息的里程碑"""
    total_issues: int = 0
    open_issues: int = 0
    closed_issues: int = 0
    deferred_issues: int = 0
