from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    author_role: Optional[str] = None


class CommentRead(BaseModel):
    id: int
    issue_id: int
    author_role: Optional[str] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
