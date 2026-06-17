from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from src.core.dependencies import get_db
from src.models.issue import Issue, IssueStatus, IssuePriority
from src.models.plan import Plan, PlanStatus
from src.models.server import Server, ServerStatus
from src.models.activity_log import ActivityLog
from src.routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("")
async def get_dashboard(
    project_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard 数据聚合"""

    # Issues 统计
    issues_query = select(
        func.count(Issue.id).label("total"),
        func.sum(case((Issue.priority == IssuePriority.P0, 1), else_=0)).label("p0"),
        func.sum(case((Issue.priority == IssuePriority.P1, 1), else_=0)).label("p1"),
        func.sum(case((Issue.status == IssueStatus.OPEN, 1), else_=0)).label("open"),
        func.sum(case((Issue.status == IssueStatus.IN_PROGRESS, 1), else_=0)).label("in_progress"),
        func.sum(case((Issue.status == IssueStatus.DEFERRED, 1), else_=0)).label("deferred"),
        func.sum(case((Issue.source == "ai_agent", 1), else_=0)).label("ai_agent"),
    )
    if project_id:
        issues_query = issues_query.where(Issue.project_id == project_id)
    issues_result = await db.execute(issues_query)
    issues_row = issues_result.one()

    # Plans 统计
    plans_query = select(
        func.count(Plan.id).label("total"),
        func.sum(case((Plan.status == PlanStatus.PENDING, 1), else_=0)).label("pending_approval"),
        func.sum(case((Plan.status == PlanStatus.IN_PROGRESS, 1), else_=0)).label("active"),
    )
    if project_id:
        plans_query = plans_query.where(Plan.project_id == project_id)
    plans_result = await db.execute(plans_query)
    plans_row = plans_result.one()

    # Servers 统计
    servers_query = select(
        func.count(Server.id).label("total"),
        func.sum(case((Server.status == ServerStatus.ACTIVE, 1), else_=0)).label("active"),
        func.sum(case((Server.status == ServerStatus.MAINTENANCE, 1), else_=0)).label("maintenance"),
        func.sum(case((Server.status == ServerStatus.OFFLINE, 1), else_=0)).label("offline"),
    )
    if project_id:
        servers_query = servers_query.where(Server.project_id == project_id)
    servers_result = await db.execute(servers_query)
    servers_row = servers_result.one()

    # 最近 Activity
    activity_query = select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(10)
    if project_id:
        activity_query = activity_query.where(ActivityLog.project_id == project_id)
    activity_result = await db.execute(activity_query)
    activities = activity_result.scalars().all()

    # 待审批计划列表
    pending_plans_query = select(Plan).where(Plan.status == PlanStatus.PENDING).order_by(Plan.created_at.desc())
    if project_id:
        pending_plans_query = pending_plans_query.where(Plan.project_id == project_id)
    pending_plans_result = await db.execute(pending_plans_query)
    pending_plans = pending_plans_result.scalars().all()

    # 最近 Issues
    recent_issues_query = select(Issue).order_by(Issue.created_at.desc()).limit(5)
    if project_id:
        recent_issues_query = recent_issues_query.where(Issue.project_id == project_id)
    recent_issues_result = await db.execute(recent_issues_query)
    recent_issues = recent_issues_result.scalars().all()

    # Agent 工作负载：每个 assignee 的 in_progress / open Issue 数
    workload_query = select(
        Issue.assignee,
        func.count(Issue.id).label("total"),
        func.sum(case((Issue.status == IssueStatus.IN_PROGRESS, 1), else_=0)).label("in_progress"),
        func.sum(case((Issue.status == IssueStatus.OPEN, 1), else_=0)).label("open"),
    ).where(Issue.assignee.isnot(None), Issue.assignee != "").group_by(Issue.assignee)
    if project_id:
        workload_query = workload_query.where(Issue.project_id == project_id)
    workload_result = await db.execute(workload_query)
    agent_workload = [
        {"assignee": row.assignee, "total": row.total or 0, "in_progress": row.in_progress or 0, "open": row.open or 0}
        for row in workload_result.all()
    ]

    # 无负责人 P0 Issue
    unassigned_p0_query = select(Issue).where(
        Issue.priority == IssuePriority.P0,
        (Issue.assignee.is_(None) | (Issue.assignee == "")),
        Issue.status.in_([IssueStatus.OPEN, IssueStatus.IN_PROGRESS]),
    )
    if project_id:
        unassigned_p0_query = unassigned_p0_query.where(Issue.project_id == project_id)
    unassigned_p0_result = await db.execute(unassigned_p0_query)
    unassigned_p0_issues = unassigned_p0_result.scalars().all()

    return {
        "issues": {
            "total": issues_row.total or 0,
            "p0": issues_row.p0 or 0,
            "p1": issues_row.p1 or 0,
            "open": issues_row.open or 0,
            "in_progress": issues_row.in_progress or 0,
            "deferred": issues_row.deferred or 0,
            "ai_agent": issues_row.ai_agent or 0,
        },
        "plans": {
            "total": plans_row.total or 0,
            "pending_approval": plans_row.pending_approval or 0,
            "active": plans_row.active or 0,
        },
        "servers": {
            "total": servers_row.total or 0,
            "active": servers_row.active or 0,
            "maintenance": servers_row.maintenance or 0,
            "offline": servers_row.offline or 0,
        },
        "recent_activities": [
            {
                "id": a.id,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "action": a.action,
                "actor": a.actor,
                "created_at": a.created_at.isoformat(),
            }
            for a in activities
        ],
        "pending_plans": [
            {
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "proposed_by": p.proposed_by,
                "created_at": p.created_at.isoformat(),
            }
            for p in pending_plans
        ],
        "recent_issues": [
            {
                "id": i.id,
                "title": i.title,
                "priority": i.priority,
                "status": i.status,
                "source": i.source,
                "created_at": i.created_at.isoformat(),
            }
            for i in recent_issues
        ],
        "agent_workload": agent_workload,
        "unassigned_p0_issues": [
            {"id": i.id, "title": i.title, "status": i.status}
            for i in unassigned_p0_issues
        ],
    }
