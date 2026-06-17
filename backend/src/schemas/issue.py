from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from src.schemas.comment import CommentRead


class IssueCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    issue_type: str = Field(default="task")
    priority: str = Field(default="P2")
    assignee_role: Optional[str] = None
    source_role: Optional[str] = None
    project_id: Optional[int] = None


class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    issue_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_role: Optional[str] = None


class IssueRead(BaseModel):
    id: int
    project_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    issue_type: str
    status: str
    priority: str
    assignee_role: Optional[str] = None
    source_role: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IssueReadWithComments(IssueRead):
    comments: List["CommentRead"] = []


class IssueListResponse(BaseModel):
    total: int
    items: List[IssueRead]
