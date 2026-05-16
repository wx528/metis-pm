from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from src.models.project import ProjectStatus


class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=200)
    slug: str = Field(..., max_length=100, pattern=r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$")
    description: Optional[str] = None
    repo_url: Optional[str] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    owner: Optional[str] = None
    default_milestone_id: Optional[int] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    repo_url: Optional[str] = None
    status: Optional[ProjectStatus] = None
    owner: Optional[str] = None
    default_milestone_id: Optional[int] = None
    # slug 不可修改，避免破坏已有 URL


class ProjectRead(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    repo_url: Optional[str] = None
    status: str
    owner: Optional[str] = None
    default_milestone_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectReadWithStats(ProjectRead):
    issue_count: int = 0
    open_issue_count: int = 0
    plan_count: int = 0
    milestone_count: int = 0
    server_count: int = 0
