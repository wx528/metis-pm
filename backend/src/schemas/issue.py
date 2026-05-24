from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from src.schemas.comment import CommentRead
from src.models.issue import IssueType, IssueStatus, IssuePriority, IssueSource


class IssueCreate(BaseModel):
    project_id: Optional[int] = None
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    issue_type: IssueType = IssueType.TASK
    status: IssueStatus = IssueStatus.OPEN
    priority: IssuePriority = IssuePriority.P2
    source: IssueSource = IssueSource.USER
    created_by: Optional[str] = None
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
    priority: Optional[IssuePriority] = None
    source: Optional[IssueSource] = None
    assignee: Optional[str] = None
    labels: Optional[str] = None
    milestone_id: Optional[int] = None
    deferred_to_milestone_id: Optional[int] = None
    deferred_reason: Optional[str] = None


class IssueRead(BaseModel):
    id: int
    project_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    issue_type: str
    status: str
    priority: str
    source: str
    created_by: Optional[str] = None
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
