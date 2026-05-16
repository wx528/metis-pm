import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from src.core.dependencies import get_db
from src.models.notification import Notification, NotificationType
from src.schemas.notification import (
    NotificationRead, NotificationListResponse, UnreadCountResponse,
)
from src.core.notification import register_sse_connection, unregister_sse_connection
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
    """通知列表（当前用户的通知）"""
    recipient = user["sub"]
    query = select(Notification).where(Notification.recipient == recipient)
    if unread_only:
        query = query.where(Notification.read == False)
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
    """未读通知数"""
    recipient = user["sub"]
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.recipient == recipient,
            Notification.read == False,
        )
    )
    return {"count": result.scalar() or 0}


@router.put("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(notification_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """标记单条通知已读"""
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.recipient != user["sub"]:
        raise HTTPException(status_code=403, detail="Not your notification")
    notification.read = True
    await db.commit()
    await db.refresh(notification)
    return notification


@router.put("/read-all", status_code=204)
async def mark_all_read(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """全部标记已读"""
    recipient = user["sub"]
    from sqlalchemy import update
    await db.execute(
        update(Notification)
        .where(Notification.recipient == recipient, Notification.read == False)
        .values(read=True)
    )
    await db.commit()
    return None


@router.get("/stream")
async def notification_stream(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """SSE 端点：实时推送通知到当前用户"""
    recipient = user["sub"]
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    register_sse_connection(recipient, queue)

    async def event_generator():
        try:
            # 发送初始连接确认
            yield f"event: connected\ndata: {recipient}\n\n"
            while True:
                try:
                    # 等待新通知，超时 30 秒发送心跳
                    data = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"event: notification\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    yield f"event: heartbeat\ndata: ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            unregister_sse_connection(recipient, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
