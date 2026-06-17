from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update

from src.core.dependencies import get_db
from src.models.notification import Notification
from src.schemas.notification import NotificationRead, NotificationListResponse, UnreadCountResponse
from src.routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    project_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    role = user.get("role", "")
    query = select(Notification).where(
        Notification.target_role.in_([role, "all"])
    )
    if unread_only:
        query = query.where(Notification.is_read == False)
    if project_id is not None:
        query = query.where(Notification.project_id == project_id)
    query = query.order_by(desc(Notification.created_at))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    result = await db.execute(query.offset(skip).limit(limit))
    items = result.scalars().all()
    return {"total": total, "items": items}


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    role = user.get("role", "")
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.target_role.in_([role, "all"]),
            Notification.is_read == False,
        )
    )
    return {"count": result.scalar() or 0}


@router.put("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(notification_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification


@router.put("/read-all", status_code=204)
async def mark_all_read(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    role = user.get("role", "")
    await db.execute(
        update(Notification)
        .where(Notification.target_role.in_([role, "all"]), Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return None
