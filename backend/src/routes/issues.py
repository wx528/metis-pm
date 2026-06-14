from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc
from sqlalchemy.orm import selectinload

from src.core.dependencies import get_db
from src.core.activity import log_activity
from src.core.notification import create_notification
from src.core.trigger_hub import get_trigger_hub
from src.core.metrics import agent_operations_total, issue_transitions_total, handovers_total
from src.core.debounce import debounce_check_or_raise
from src.models.issue import Issue, IssueType, IssueStatus, IssuePriority, IssueSource
from src.models.notification import NotificationType
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
    source: Optional[str] = Query(None),
    assignee: Optional[str] = Query(None),
    unassigned: bool = Query(False),
    created_by: Optional[str] = Query(None),
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
    if unassigned:
        query = query.where((Issue.assignee.is_(None)) | (Issue.assignee == ""))
    if created_by:
        query = query.where(Issue.created_by == created_by)
    if milestone_id:
        query = query.where(Issue.milestone_id == milestone_id)
    if deferred_only:
        query = query.where(Issue.status == IssueStatus.DEFERRED)
    if search:
        query = query.where(Issue.title.contains(search, autoescape=True) | Issue.description.contains(search, autoescape=True))

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
async def create_issue(data: IssueCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "agent", "tester"))):
    # 防抖：10 秒内相同内容去重
    debounce_check_or_raise("/api/v1/issues", data.model_dump_json().encode(), user["sub"])
    issue = Issue(**data.model_dump())
    if user["role"] == "tester":
        issue.source = IssueSource.USER
        if not issue.created_by:
            issue.created_by = user["sub"]
    db.add(issue)
    await db.commit()
    await db.refresh(issue)

    # 业务指标：记录 Agent 操作
    agent_operations_total.labels(
        role=user["role"],
        operation="create",
        entity_type="issue"
    ).inc()

    await log_activity(
        db, entity_type="issue", entity_id=issue.id,
        actor=user["sub"],
        action="created",
        new_value={"title": issue.title, "priority": issue.priority, "status": issue.status},
        project_id=issue.project_id,
    )

    # 如果 Agent 创建了 P0/P1 issue，通知 admin
    if issue.priority in (IssuePriority.P0, IssuePriority.P1):
        get_trigger_hub().fire_event("p0_issue_created", str(issue.id), {"issue_id": issue.id, "priority": str(issue.priority), "project_id": issue.project_id})
    if user["role"] == "agent" and issue.priority in (IssuePriority.P0, IssuePriority.P1):
        await create_notification(
            db, recipient="admin",
            type=NotificationType.TASK_CREATED,
            title=f"Agent {user['sub']} 创建了 {issue.priority} Issue",
            body=issue.title,
            entity_type="issue", entity_id=issue.id,
            created_by=user["sub"],
            project_id=issue.project_id,
        )

    # 如果 Tester 创建了 Issue，通知 admin 和所有 mate
    if user["role"] == "tester":
        from src.settings import settings
        recipients = ["admin"]
        for name, (pwd, role) in settings.agent_password_map.items():
            if role == "mate":
                recipients.append(name)
        for recip in recipients:
            await create_notification(
                db, recipient=recip,
                type=NotificationType.TASK_CREATED,
                title=f"Tester {user['sub']} 提交了 {issue.priority} Issue",
                body=issue.title,
                entity_type="issue", entity_id=issue.id,
                created_by=user["sub"],
                project_id=issue.project_id,
            )

    # 给创建者发确认通知
    if user["role"] in ("agent", "tester"):
        await create_notification(
            db, recipient=user["sub"],
            type=NotificationType.INFO,
            title=f"Issue #{issue.id} 已创建",
            body=f"[{issue.priority}] {issue.title}",
            entity_type="issue", entity_id=issue.id,
            created_by="system",
            project_id=issue.project_id,
        )

    # 检查并触发 on_issue_created 工作流
    try:
        from src.core.workflow_engine import check_and_trigger_workflows
        await check_and_trigger_workflows(
            db, trigger_type="on_issue_created",
            project_id=issue.project_id,
            context={"issue_id": issue.id, "issue_type": issue.issue_type, "priority": issue.priority},
        )
    except Exception:
        pass  # 工作流触发失败不影响 Issue 创建

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

    # tester 只能修改自己创建的 Issue，且只能改状态（关闭/退回）
    if user["role"] == "tester":
        if issue.created_by != user["sub"]:
            raise HTTPException(status_code=403, detail="Tester 只能修改自己提交的 Issue")
        update_data = data.model_dump(exclude_unset=True)
        allowed_status_changes = {"closed", "in_progress"}
        if "status" in update_data and update_data["status"] not in allowed_status_changes:
            raise HTTPException(status_code=403, detail="Tester 只能将 Issue 关闭(closed)或退回(in_progress)")
        non_status_keys = [k for k in update_data if k != "status"]
        if non_status_keys:
            raise HTTPException(status_code=403, detail=f"Tester 只能修改状态，不能修改: {', '.join(non_status_keys)}")

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
        if action == "status_changed":
            # 业务指标：Issue 状态流转
            issue_transitions_total.labels(
                from_status=old_values.get("status", "unknown"),
                to_status=update_data["status"]
            ).inc()

    await log_activity(
        db, entity_type="issue", entity_id=issue.id,
        action=action, actor=user["sub"],
        old_value=old_values,
        new_value={k: getattr(issue, k) for k in old_values.keys()},
        project_id=issue.project_id,
    )

    # Agent 完成 issue 时通知 admin
    if user["role"] == "agent" and update_data.get("status") == IssueStatus.CLOSED:
        get_trigger_hub().fire_event("issue_closed", str(issue.id), {"issue_id": issue.id, "project_id": issue.project_id})
        await create_notification(
            db, recipient="admin",
            type=NotificationType.TASK_COMPLETED,
            title=f"Agent {user['sub']} 完成了 Issue #{issue.id}",
            body=issue.title,
            entity_type="issue", entity_id=issue.id,
            created_by=user["sub"],
            project_id=issue.project_id,
        )

    # Issue 进入 review 状态时通知创建者（如果是 tester 创建的）
    if update_data.get("status") == IssueStatus.REVIEW and issue.created_by:
        from src.settings import settings
        creator_role = "agent"
        for name, (pwd, role) in settings.agent_password_map.items():
            if name == issue.created_by:
                creator_role = role
                break
        if creator_role == "tester":
            await create_notification(
                db, recipient=issue.created_by,
                type=NotificationType.INFO,
                title=f"Issue #{issue.id} 等待验证",
                body=f"[{issue.priority}] {issue.title}",
                entity_type="issue", entity_id=issue.id,
                created_by=user["sub"],
                project_id=issue.project_id,
            )

    return issue


@router.delete("/{issue_id}", status_code=204)
async def delete_issue(issue_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin"))):
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


@router.post("/{issue_id}/undefer", response_model=IssueRead)
async def undefer_issue(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """取消暂缓，将 deferred issue 恢复为 open"""
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    if issue.status != IssueStatus.DEFERRED:
        raise HTTPException(status_code=400, detail="Only deferred issues can be undeferred")

    old_status = issue.status
    old_milestone = issue.deferred_to_milestone_id
    issue.status = IssueStatus.OPEN
    issue.deferred_to_milestone_id = None
    issue.deferred_reason = None

    await db.commit()
    await db.refresh(issue)

    await log_activity(
        db, entity_type="issue", entity_id=issue.id,
        action="undeferred", actor=user["sub"],
        old_value={"status": old_status, "deferred_to_milestone_id": old_milestone},
        new_value={"status": issue.status},
        project_id=issue.project_id,
    )
    return issue


@router.get("/{issue_id}/comments", response_model=List[CommentRead])
async def list_comments(issue_id: int, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db)):
    """获取 Issue 的评论列表"""
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

    # 业务指标：Handover 评论统计
    if data.comment_type == "handover":
        # 尝试从评论内容解析 @目标角色
        import re
        at_match = re.search(r'@(\w+)', data.content)
        to_role = at_match.group(1) if at_match else "unknown"
        handovers_total.labels(
            from_role=user["role"],
            to_role=to_role
        ).inc()

    await log_activity(
        db, entity_type="issue", entity_id=issue.id,
        action="commented", actor=user["sub"],
        new_value={"comment_id": comment.id, "content": data.content[:100]},
        project_id=issue.project_id,
    )
    return comment
