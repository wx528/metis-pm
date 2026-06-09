"""
系统监控 API
提供健康检查、性能指标、业务统计等监控数据
"""
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.core.dependencies import get_db
from src.routes.auth import get_current_user
from src.models.issue import Issue, IssueStatus, IssuePriority
from src.models.plan import Plan, PlanStatus
from src.models.activity_log import ActivityLog
from src.models.comment import Comment

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/system")
async def get_system_metrics(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取系统监控指标（用于 Dashboard 展示）"""
    now = datetime.now(timezone.utc)
    hour_ago = now - timedelta(hours=1)
    day_ago = now - timedelta(hours=24)

    # 1. Issue 统计
    issues_query = select(
        func.count(Issue.id).label("total"),
        func.sum(func.case((Issue.status == IssueStatus.OPEN, 1), else_=0)).label("open"),
        func.sum(func.case((Issue.status == IssueStatus.IN_PROGRESS, 1), else_=0)).label("in_progress"),
        func.sum(func.case((Issue.status == IssueStatus.REVIEW, 1), else_=0)).label("review"),
        func.sum(func.case((Issue.status == IssueStatus.CLOSED, 1), else_=0)).label("closed"),
        func.sum(func.case((Issue.priority == IssuePriority.P0, 1), else_=0)).label("p0"),
        func.sum(func.case((Issue.priority == IssuePriority.P1, 1), else_=0)).label("p1"),
    )
    issues_result = await db.execute(issues_query)
    issues_row = issues_result.one()

    # 2. 今日活跃统计
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    today_created = await db.execute(
        select(func.count(ActivityLog.id))
        .where(ActivityLog.action == "created", ActivityLog.created_at >= today_start)
    )
    today_completed = await db.execute(
        select(func.count(ActivityLog.id))
        .where(ActivityLog.action == "status_changed", ActivityLog.created_at >= today_start)
    )
    
    # 3. Plan 统计
    plans_query = select(
        func.count(Plan.id).label("total"),
        func.sum(func.case((Plan.status == PlanStatus.PENDING_APPROVAL, 1), else_=0)).label("pending"),
        func.sum(func.case((Plan.status == PlanStatus.ACTIVE, 1), else_=0)).label("active"),
        func.sum(func.case((Plan.status == PlanStatus.COMPLETED, 1), else_=0)).label("completed"),
    )
    plans_result = await db.execute(plans_query)
    plans_row = plans_result.one()

    # 4. 最近 1 小时活动
    recent_activity = await db.execute(
        select(func.count(ActivityLog.id))
        .where(ActivityLog.created_at >= hour_ago)
    )

    # 5. Handover 统计
    handover_count = await db.execute(
        select(func.count(Comment.id))
        .where(Comment.comment_type == "handover", Comment.created_at >= day_ago)
    )

    # 6. Agent 活跃度（最近 1 小时有活动的 identity）
    active_agents = await db.execute(
        select(func.count(func.distinct(ActivityLog.actor)))
        .where(ActivityLog.created_at >= hour_ago, ActivityLog.actor != "user")
    )

    return {
        "timestamp": now.isoformat(),
        "issues": {
            "total": issues_row.total or 0,
            "open": issues_row.open or 0,
            "in_progress": issues_row.in_progress or 0,
            "review": issues_row.review or 0,
            "closed": issues_row.closed or 0,
            "p0": issues_row.p0 or 0,
            "p1": issues_row.p1 or 0,
        },
        "plans": {
            "total": plans_row.total or 0,
            "pending_approval": plans_row.pending or 0,
            "active": plans_row.active or 0,
            "completed": plans_row.completed or 0,
        },
        "activity": {
            "today_created": today_created.scalar() or 0,
            "today_completed": today_completed.scalar() or 0,
            "recent_1h": recent_activity.scalar() or 0,
            "active_agents": active_agents.scalar() or 0,
        },
        "collaboration": {
            "handovers_24h": handover_count.scalar() or 0,
        },
    }
