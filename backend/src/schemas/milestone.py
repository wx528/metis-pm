from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class MilestoneCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    phase: Optional[str] = None       # 分期标识，如 "phase-1", "MVP"
    due_date: Optional[date] = None


class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    phase: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[date] = None


class MilestoneRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    phase: Optional[str] = None
    status: str
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
