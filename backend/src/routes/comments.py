from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.core.dependencies import get_db
from src.routes.auth import get_current_user
from src.models.comment import Comment
from src.schemas.comment import CommentRead

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[CommentRead])
async def list_comments(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Comment).order_by(desc(Comment.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
