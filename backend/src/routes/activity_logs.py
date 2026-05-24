from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.core.dependencies import get_db
from src.models.activity_log import ActivityLog
from src.schemas.activity_log import ActivityLogCreate, ActivityLogRead
from src.routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=List[ActivityLogRead])
async def list_activity_logs(
    db: AsyncSession = Depends(get_db),
    entity_type: Optional[str] = Query(None, description="issue | plan | plan_item | server | milestone"),
    entity_id: Optional[int] = Query(None),
    actor: Optional[str] = Query(None, description="按操作者筛选"),
    limit: int = Query(50, ge=1, le=200),
):
    """查询活动日志（支持按实体或操作者筛选）"""
    query = select(ActivityLog).order_by(desc(ActivityLog.created_at))
    if entity_type and entity_id:
        query = query.where(ActivityLog.entity_type == entity_type, ActivityLog.entity_id == entity_id)
    elif entity_type:
        query = query.where(ActivityLog.entity_type == entity_type)
    if actor:
        query = query.where(ActivityLog.actor == actor)
    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ActivityLogRead, status_code=201)
async def create_activity_log(data: ActivityLogCreate, db: AsyncSession = Depends(get_db)):
    """创建活动日志（供内部调用或 MCP 使用）"""
    log = ActivityLog(**data.model_dump())
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log
