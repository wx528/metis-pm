from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ActivityLogCreate(BaseModel):
    project_id: Optional[int] = None
    entity_type: str
    entity_id: int
    action: str
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    actor: str = "user"


class ActivityLogRead(BaseModel):
    id: int
    project_id: Optional[int] = None
    entity_type: str
    entity_id: int
    action: str
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    actor: str
    created_at: datetime

    class Config:
        from_attributes = True
