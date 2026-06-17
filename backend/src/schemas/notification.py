from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: int
    target_role: str
    message: str
    is_read: bool
    project_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    total: int
    items: List[NotificationRead]


class UnreadCountResponse(BaseModel):
    count: int
