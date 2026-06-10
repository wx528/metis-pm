"""ActivityLog 自动记录工具"""
from datetime import datetime, date
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.activity_log import ActivityLog


def _json_safe(value):
    """将 datetime/date 对象转为 ISO 字符串，支持嵌套 dict/list"""
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


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
        old_value=_json_safe(old_value) if old_value is not None else None,
        new_value=_json_safe(new_value) if new_value is not None else None,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log
