from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProjectRegistrationCreate(BaseModel):
    name: str = Field(..., max_length=200)
    path: str = Field(..., max_length=500)
    description: Optional[str] = None
    tech_stack: Optional[str] = None
    repo_url: Optional[str] = None
    language: Optional[str] = None
    framework: Optional[str] = None
    status: Optional[str] = "active"
    notes: Optional[str] = None


class ProjectRegistrationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    path: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    tech_stack: Optional[str] = None
    repo_url: Optional[str] = None
    language: Optional[str] = None
    framework: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    last_scanned_at: Optional[datetime] = None


class ProjectRegistrationRead(BaseModel):
    id: int
    name: str
    path: str
    description: Optional[str] = None
    tech_stack: Optional[str] = None
    repo_url: Optional[str] = None
    language: Optional[str] = None
    framework: Optional[str] = None
    status: str
    notes: Optional[str] = None
    registered_by: Optional[str] = None
    last_scanned_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectRegistrationListResponse(BaseModel):
    total: int
    items: list[ProjectRegistrationRead]
