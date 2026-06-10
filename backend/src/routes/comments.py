"""评论管理路由"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from src.core.dependencies import get_db
from src.routes.auth import get_current_user
from src.models.comment import Comment, CommentType
from src.schemas.comment import CommentRead

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.put("/{comment_id}/read")
async def mark_comment_read(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """标记评论为已读（主要用于交接评论）"""
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    agent_name = user.get("sub", "unknown")
    comment.read_by = agent_name
    comment.read_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(comment)
    
    return {"message": f"Marked as read by {agent_name}", "comment": comment}


@router.get("", response_model=list[CommentRead])
async def list_comments(
    comment_type: Optional[str] = Query(None),
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """查询评论列表（支持按类型和已读状态过滤）"""
    query = select(Comment)
    
    if comment_type:
        query = query.where(Comment.comment_type == comment_type)
    
    if unread_only:
        query = query.where(
            and_(
                Comment.read_by.is_(None),
                Comment.read_at.is_(None),
            )
        )
    
    query = query.order_by(desc(Comment.created_at)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    items = result.scalars().all()
    return items
