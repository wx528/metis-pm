from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    author: str = Field(default="user", max_length=100)
    parent_id: Optional[int] = None


class CommentRead(BaseModel):
    id: int
    issue_id: int
    author: Optional[str] = None
    content: str
    parent_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
