"""ActivityLog 自动记录工具"""
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.activity_log import ActivityLog


async def log_activity(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
    action: str,
    actor: str = "user",
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    project_id: Optional[int] = None,
) -> ActivityLog:
    """记录活动日志"""
    log = ActivityLog(
        project_id=project_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log
