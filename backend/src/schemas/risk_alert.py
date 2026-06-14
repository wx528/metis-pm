from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class RiskAlertCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    level: str = Field(default="medium")
    source: str = Field(default="manual")
    suggested_action: Optional[str] = None
    project_id: Optional[int] = None


class RiskAlertUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    level: Optional[str] = None
    status: Optional[str] = None
    suggested_action: Optional[str] = None


class RiskAlertRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    level: str
    source: str
    status: str
    suggested_action: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    project_id: Optional[int] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RiskAlertListResponse(BaseModel):
    total: int
    items: List[RiskAlertRead]
