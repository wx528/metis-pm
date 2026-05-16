from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from src.models.notification import NotificationType


class NotificationCreate(BaseModel):
    recipient: str
    type: NotificationType = NotificationType.INFO
    title: str
    body: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    created_by: Optional[str] = None
    project_id: Optional[int] = None


class NotificationRead(BaseModel):
    id: int
    recipient: str
    type: str
    title: str
    body: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    read: bool = False
    created_by: Optional[str] = None
    project_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    total: int
    items: List[NotificationRead]


class UnreadCountResponse(BaseModel):
    count: int
