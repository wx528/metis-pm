from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    author: str = Field(default="user", max_length=100)


class CommentRead(BaseModel):
    id: int
    issue_id: int
    author: Optional[str] = None
    content: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
