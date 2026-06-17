from sqlalchemy.ext.asyncio import AsyncSession
from src.models.notification import Notification


async def create_notification(
    db: AsyncSession,
    target_role: str,
    message: str,
    project_id: int | None = None,
):
    notification = Notification(
        target_role=target_role,
        message=message,
        project_id=project_id,
    )
    db.add(notification)
    await db.commit()
