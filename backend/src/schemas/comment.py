from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    author: str = Field(default="anonymous", max_length=100)
    parent_id: Optional[int] = None
    comment_type: str = Field(default="normal", max_length=20)


class CommentRead(BaseModel):
    id: int
    issue_id: int
    author: Optional[str] = None
    content: str
    parent_id: Optional[int] = None
    comment_type: str = "normal"
    created_at: Optional[datetime] = None
    read_by: Optional[str] = None      # 谁已读
    read_at: Optional[datetime] = None # 何时已读

    class Config:
        from_attributes = True
