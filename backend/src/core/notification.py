"""通知服务 — 统一创建通知的入口"""
import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.notification import Notification, NotificationType

# SSE 连接管理：recipient -> list of asyncio.Queue
_sse_connections: dict[str, list[asyncio.Queue]] = {}


async def create_notification(
    db: AsyncSession,
    recipient: str,
    type: NotificationType,
    title: str,
    body: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    created_by: Optional[str] = None,
    project_id: Optional[int] = None,
) -> Notification:
    """创建通知并推送到 SSE 连接"""
    notification = Notification(
        recipient=recipient,
        type=type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        created_by=created_by,
        project_id=project_id,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    # 推送到 SSE 连接
    await _push_to_sse(recipient, notification)

    return notification


async def _push_to_sse(recipient: str, notification: Notification):
    """向该 recipient 的所有 SSE 连接推送通知"""
    from src.schemas.notification import NotificationRead
    data = NotificationRead.model_validate(notification).model_dump_json()
    queues = _sse_connections.get(recipient, [])
    for queue in queues:
        try:
            queue.put_nowait(data)
        except asyncio.QueueFull:
            pass  # 丢弃旧消息


def register_sse_connection(recipient: str, queue: asyncio.Queue):
    """注册 SSE 连接"""
    if recipient not in _sse_connections:
        _sse_connections[recipient] = []
    _sse_connections[recipient].append(queue)


def unregister_sse_connection(recipient: str, queue: asyncio.Queue):
    """注销 SSE 连接"""
    if recipient in _sse_connections:
        try:
            _sse_connections[recipient].remove(queue)
        except ValueError:
            pass
        if not _sse_connections[recipient]:
            del _sse_connections[recipient]
