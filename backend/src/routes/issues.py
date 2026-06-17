from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc
from sqlalchemy.orm import selectinload

from src.core.dependencies import get_db
from src.core.notification import create_notification
from src.models.issue import Issue, IssueType, IssueStatus, IssuePriority
from src.models.comment import Comment
from src.schemas.issue import IssueCreate, IssueUpdate, IssueRead, IssueReadWithComments, IssueListResponse
from src.schemas.comment import CommentCreate, CommentRead
from src.routes.auth import get_current_user, require_role

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=IssueListResponse)
async def list_issues(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    project_id: Optional[int] = Query(None),
    issue_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assignee_role: Optional[str] = Query(None),
    source_role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at_desc"),
):
    query = select(Issue)
    if project_id:
        query = query.where(Issue.project_id == project_id)
    if issue_type:
        query = query.where(Issue.issue_type == issue_type)
    if status:
        query = query.where(Issue.status == status)
    if priority:
        query = query.where(Issue.priority == priority)
    if assignee_role:
        query = query.where(Issue.assignee_role == assignee_role)
    if source_role:
        query = query.where(Issue.source_role == source_role)
    if search:
        query = query.where(Issue.title.contains(search, autoescape=True))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    sort_map = {
        "created_at_desc": desc(Issue.created_at),
        "created_at_asc": asc(Issue.created_at),
        "updated_at_desc": desc(Issue.updated_at),
        "priority_asc": asc(Issue.priority),
        "priority_desc": desc(Issue.priority),
    }
    order_clause = sort_map.get(sort_by, desc(Issue.created_at))
    query = query.order_by(order_clause).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()
    return {"total": total, "items": items}


@router.post("", response_model=IssueRead, status_code=201)
async def create_issue(data: IssueCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "agent", "tester"))):
    issue = Issue(**data.model_dump())
    db.add(issue)
    await db.commit()
    await db.refresh(issue)

    if issue.priority in (IssuePriority.P0, IssuePriority.P1):
        await create_notification(
            db, target_role="admin",
            message=f"[{issue.priority}] {issue.title}",
            project_id=issue.project_id,
        )
    return issue


@router.get("/{issue_id}", response_model=IssueReadWithComments)
async def get_issue(issue_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Issue).where(Issue.id == issue_id).options(selectinload(Issue.comments))
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.put("/{issue_id}", response_model=IssueRead)
async def update_issue(issue_id: int, data: IssueUpdate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(issue, key, value)

    await db.commit()
    await db.refresh(issue)

    if update_data.get("status") == IssueStatus.CLOSED:
        await create_notification(
            db, target_role="admin",
            message=f"Issue #{issue.id} closed: {issue.title}",
            project_id=issue.project_id,
        )
    return issue


@router.delete("/{issue_id}", status_code=204)
async def delete_issue(issue_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin"))):
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    await db.delete(issue)
    await db.commit()
    return None


@router.get("/{issue_id}/comments", response_model=List[CommentRead])
async def list_comments(issue_id: int, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Comment).where(Comment.issue_id == issue_id).order_by(asc(Comment.created_at)).offset(offset).limit(limit)
    )
    return result.scalars().all()


@router.post("/{issue_id}/comments", response_model=CommentRead, status_code=201)
async def add_comment(issue_id: int, data: CommentCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    comment = Comment(issue_id=issue_id, **data.model_dump())
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment
