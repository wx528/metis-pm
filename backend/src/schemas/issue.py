from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from src.schemas.comment import CommentRead

Priority = Literal["P0", "P1", "P2", "P3"]
IssueType = Literal["bug", "feature", "task", "improvement", "documentation"]
IssueStatus = Literal["open", "in_progress", "review", "deferred", "closed", "cancelled"]
IssueSource = Literal["user", "ai_agent", "collaborative"]


class IssueCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    issue_type: IssueType = "task"
    status: IssueStatus = "open"
    priority: Priority = "P2"
    source: IssueSource = "user"
    assignee: Optional[str] = None
    labels: Optional[str] = None
    milestone_id: Optional[int] = None
    deferred_to_milestone_id: Optional[int] = None
    deferred_reason: Optional[str] = None
    parent_id: Optional[int] = None


class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    issue_type: Optional[IssueType] = None
    status: Optional[IssueStatus] = None
    priority: Optional[Priority] = None
    source: Optional[IssueSource] = None
    assignee: Optional[str] = None
    labels: Optional[str] = None
    milestone_id: Optional[int] = None
    deferred_to_milestone_id: Optional[int] = None
    deferred_reason: Optional[str] = None


class IssueRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    issue_type: str
    status: str
    priority: str
    source: str
    assignee: Optional[str] = None
    labels: Optional[str] = None
    milestone_id: Optional[int] = None
    deferred_to_milestone_id: Optional[int] = None
    deferred_reason: Optional[str] = None
    parent_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class IssueReadWithComments(IssueRead):
    comments: List[CommentRead] = []


class IssueListResponse(BaseModel):
    total: int
    items: List[IssueRead]
