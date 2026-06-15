from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class FeedbackCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    category: str = Field(default="other")
    priority: str = Field(default="P2", pattern=r"^P[0-3]$")
    project_id: Optional[int] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    product_name: Optional[str] = None
    product_version: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid = {"bug", "feature_request", "improvement", "ux", "workflow", "other"}
        if v not in valid:
            raise ValueError(f"Invalid category. Valid: {sorted(valid)}")
        return v


class FeedbackUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    admin_reply: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid = {"bug", "feature_request", "improvement", "ux", "workflow", "other"}
        if v not in valid:
            raise ValueError(f"Invalid category. Valid: {sorted(valid)}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid = {"open", "acknowledged", "in_progress", "resolved", "wont_fix"}
        if v not in valid:
            raise ValueError(f"Invalid status. Valid: {sorted(valid)}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid = {"P0", "P1", "P2", "P3"}
        if v not in valid:
            raise ValueError(f"Invalid priority. Valid: {sorted(valid)}")
        return v


class FeedbackRead(BaseModel):
    id: int
    title: str
    content: str
    category: str
    status: str
    priority: str
    submitted_by: str
    submitted_by_role: Optional[str] = None
    project_id: Optional[int] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    product_name: Optional[str] = None
    product_version: Optional[str] = None
    admin_reply: Optional[str] = None
    replied_by: Optional[str] = None
    replied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FeedbackListResponse(BaseModel):
    total: int
    items: List[FeedbackRead]
