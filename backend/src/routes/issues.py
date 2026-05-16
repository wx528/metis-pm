from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc
from sqlalchemy.orm import selectinload

from src.core.dependencies import get_db
from src.core.activity import log_activity
from src.core.notification import create_notification
from src.models.issue import Issue, IssueType, IssueStatus, IssuePriority, IssueSource
from src.models.notification import NotificationType
from src.models.comment import Comment
from src.schemas.issue import IssueCreate, IssueUpdate, IssueRead, IssueReadWithComments, IssueListResponse
from src.schemas.comment import CommentCreate, CommentRead
from src.routes.auth import get_current_user

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
    source: Optional[str] = Query(None),
    assignee: Optional[str] = Query(None),
    milestone_id: Optional[int] = Query(None),
    deferred_only: bool = Query(False),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at_desc"),
):
    """问题列表（支持筛选和搜索）"""
    query = select(Issue)
    if project_id:
        query = query.where(Issue.project_id == project_id)
    if issue_type:
        query = query.where(Issue.issue_type == issue_type)
    if status:
        query = query.where(Issue.status == status)
    if priority:
        query = query.where(Issue.priority == priority)
    if source:
        query = query.where(Issue.source == source)
    if assignee:
        query = query.where(Issue.assignee == assignee)
    if milestone_id:
        query = query.where(Issue.milestone_id == milestone_id)
    if deferred_only:
        query = query.where(Issue.status == IssueStatus.DEFERRED)
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Issue.title.contains(escaped, autoescape=False) | Issue.description.contains(escaped, autoescape=False))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    sort_map = {
        "created_at_desc": desc(Issue.created_at),
        "created_at_asc": asc(Issue.created_at),
        "updated_at_desc": desc(Issue.updated_at),
        "updated_at_asc": asc(Issue.updated_at),
        "priority_asc": asc(Issue.priority),
        "priority_desc": desc(Issue.priority),
    }
    order_clause = sort_map.get(sort_by, desc(Issue.created_at))
    query = query.order_by(order_clause).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"total": total, "items": items}


@router.post("", response_model=IssueRead, status_code=201)
async def create_issue(data: IssueCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    issue = Issue(**data.model_dump())
    db.add(issue)
    await db.commit()
    await db.refresh(issue)

    await log_activity(
        db, entity_type="issue", entity_id=issue.id,
        actor=user["sub"],
        action="created",
        new_value={"title": issue.title, "priority": issue.priority, "status": issue.status},
        project_id=issue.project_id,
    )

    # 如果 Agent 创建了 P0/P1 issue，通知 admin
    if user["role"] == "agent" and issue.priority in (IssuePriority.P0, IssuePriority.P1):
        await create_notification(
            db, recipient="admin",
            type=NotificationType.TASK_COMPLETED,
            title=f"Agent {user['sub']} 创建了 {issue.priority} Issue",
            body=issue.title,
            entity_type="issue", entity_id=issue.id,
            created_by=user["sub"],
            project_id=issue.project_id,
        )

    return issue


@router.get("/{issue_id}", response_model=IssueReadWithComments)
async def get_issue(issue_id: int, db: AsyncSession = Depends(get_db)):
    """问题详情"""
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

    old_values = {
        k: getattr(issue, k)
        for k in ["title", "description", "status", "priority", "milestone_id"]
    }

    update_data = data.model_dump(exclude_unset=True)

    if update_data.get("status") == "deferred" and not update_data.get("deferred_to_milestone_id"):
        if not issue.deferred_to_milestone_id:
            raise HTTPException(
                status_code=400,
                detail="deferred 状态必须指定 deferred_to_milestone_id（推迟到哪个阶段）"
            )

    for key, value in update_data.items():
        setattr(issue, key, value)

    await db.commit()
    await db.refresh(issue)

    # 记录状态变更
    action = "updated"
    if "status" in update_data:
        action = "status_changed" if update_data["status"] != old_values.get("status") else "updated"

    await log_activity(
        db, entity_type="issue", entity_id=issue.id,
        action=action, actor=user["sub"],
        old_value=old_values,
        new_value={k: getattr(issue, k) for k in old_values.keys()},
        project_id=issue.project_id,
    )

    # Agent 完成 issue 时通知 admin
    if user["role"] == "agent" and update_data.get("status") == IssueStatus.CLOSED:
        await create_notification(
            db, recipient="admin",
            type=NotificationType.TASK_COMPLETED,
            title=f"Agent {user['sub']} 完成了 Issue #{issue.id}",
            body=issue.title,
            entity_type="issue", entity_id=issue.id,
            created_by=user["sub"],
            project_id=issue.project_id,
        )

    return issue


@router.delete("/{issue_id}", status_code=204)
async def delete_issue(issue_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    await log_activity(
        db, entity_type="issue", entity_id=issue.id,
        action="deleted", actor=user["sub"],
        old_value={"title": issue.title},
        project_id=issue.project_id,
    )

    await db.delete(issue)
    await db.commit()
    return None


@router.post("/{issue_id}/defer", response_model=IssueRead)
async def defer_issue(
    issue_id: int,
    deferred_to_milestone_id: int,
    deferred_reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    old_status = issue.status
    issue.status = IssueStatus.DEFERRED
    issue.deferred_to_milestone_id = deferred_to_milestone_id
    issue.deferred_reason = deferred_reason

    await db.commit()
    await db.refresh(issue)

    await log_activity(
        db, entity_type="issue", entity_id=issue.id,
        action="deferred", actor=user["sub"],
        old_value={"status": old_status},
        new_value={"status": issue.status, "deferred_to_milestone_id": deferred_to_milestone_id, "reason": deferred_reason},
        project_id=issue.project_id,
    )
    return issue


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

    await log_activity(
        db, entity_type="issue", entity_id=issue.id,
        action="commented", actor=user["sub"],
        new_value={"comment_id": comment.id, "content": data.content[:100]},
        project_id=issue.project_id,
    )
    return comment
