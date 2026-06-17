"""Phase 5 — 统计 API：Agent 产出、Issue 解决时长、Plan 完成率、Agent 活跃度"""
from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_

from src.core.dependencies import get_db
from src.models.issue import Issue, IssueStatus, IssueType, IssueSource
from src.models.plan import Plan, PlanStatus
from src.models.plan_item import PlanItem, PlanItemStatus
from src.models.activity_log import ActivityLog
from src.routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/agent-productivity")
async def agent_productivity(
    project_id: int = Query(...),
    period: str = Query("all", pattern="^(week|month|all)$"),
    db: AsyncSession = Depends(get_db),
):
    """Agent 产出统计：按 actor 统计创建/完成的 Issue 数"""
    since = _get_period_start(period)

    # 按 actor 统计创建的 Issue
    created_query = select(
        ActivityLog.actor,
        func.count(ActivityLog.id).label("created"),
    ).where(
        ActivityLog.project_id == project_id,
        ActivityLog.entity_type == "issue",
        ActivityLog.action == "created",
    )
    if since:
        created_query = created_query.where(ActivityLog.created_at >= since)
    created_query = created_query.group_by(ActivityLog.actor)
    created_result = await db.execute(created_query)
    created_map = {row.actor: row.created for row in created_result.all()}

    # 按 actor 统计完成的 Issue（通过 closed_at 非空的 Issue 关联 activity_log）
    # 用 Issue 表直接统计更可靠
    completed_by_actor = select(
        ActivityLog.actor,
        func.count(ActivityLog.id).label("completed"),
    ).where(
        ActivityLog.project_id == project_id,
        ActivityLog.entity_type == "issue",
        ActivityLog.action == "status_changed",
    )
    if since:
        completed_by_actor = completed_by_actor.where(ActivityLog.created_at >= since)
    completed_by_actor = completed_by_actor.group_by(ActivityLog.actor)
    completed_result = await db.execute(completed_by_actor)
    completed_map = {}
    for row in completed_result.all():
        # 过滤：只统计真正 close 的（通过 new_value 判断）
        completed_map[row.actor] = row.completed

    # 合并所有 actor
    all_actors = set(created_map.keys()) | set(completed_map.keys())
    agents = []
    for actor in sorted(all_actors):
        agents.append({
            "actor": actor,
            "created": created_map.get(actor, 0),
            "completed": completed_map.get(actor, 0),
        })

    # 如果没有任何数据，从 issue 表获取 source 统计
    if not agents:
        source_query = select(
            Issue.source,
            func.count(Issue.id).label("count"),
        ).where(Issue.project_id == project_id)
        if since:
            source_query = source_query.where(Issue.created_at >= since)
        source_query = source_query.group_by(Issue.source)
        source_result = await db.execute(source_query)
        for row in source_result.all():
            agents.append({"actor": row.source, "created": row.count, "completed": 0})

    return {"period": period, "agents": agents}


@router.get("/issue-resolution")
async def issue_resolution(
    project_id: int = Query(...),
    period: str = Query("all", pattern="^(week|month|all)$"),
    db: AsyncSession = Depends(get_db),
):
    """Issue 解决时长统计：平均值、中位数、P90，按类型分组"""
    since = _get_period_start(period)

    query = select(
        Issue.issue_type,
        Issue.created_at,
        Issue.closed_at,
    ).where(
        Issue.project_id == project_id,
        Issue.status == IssueStatus.CLOSED,
        Issue.closed_at.isnot(None),
    )
    if since:
        query = query.where(Issue.closed_at >= since)

    result = await db.execute(query)
    rows = result.all()

    # 按类型分组计算
    by_type: dict[str, list[float]] = {}
    for row in rows:
        if row.closed_at and row.created_at:
            hours = (row.closed_at - row.created_at).total_seconds() / 3600
            by_type.setdefault(row.issue_type, []).append(hours)

    type_stats = []
    for issue_type, hours_list in sorted(by_type.items()):
        hours_list.sort()
        n = len(hours_list)
        type_stats.append({
            "issue_type": issue_type,
            "count": n,
            "avg_hours": round(sum(hours_list) / n, 1) if n else 0,
            "median_hours": round(hours_list[n // 2], 1) if n else 0,
            "p90_hours": round(hours_list[int(n * 0.9)], 1) if n >= 10 else round(hours_list[-1], 1) if n else 0,
        })

    # 总体统计
    all_hours = sorted(h for hours in hours_list for h in [hours]) if by_type else []
    # Flatten
    all_hours_flat = []
    for hours_list in by_type.values():
        all_hours_flat.extend(hours_list)
    all_hours_flat.sort()
    n_total = len(all_hours_flat)

    overall = {
        "count": n_total,
        "avg_hours": round(sum(all_hours_flat) / n_total, 1) if n_total else 0,
        "median_hours": round(all_hours_flat[n_total // 2], 1) if n_total else 0,
        "p90_hours": round(all_hours_flat[int(n_total * 0.9)], 1) if n_total >= 10 else round(all_hours_flat[-1], 1) if n_total else 0,
    }

    return {"period": period, "overall": overall, "by_type": type_stats}


@router.get("/plan-completion")
async def plan_completion(
    project_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Plan 完成率统计"""
    # 获取项目下所有 Plan 及其 PlanItem 统计
    plans_query = select(
        Plan.id,
        Plan.title,
        Plan.status,
        func.count(PlanItem.id).label("total_items"),
        func.sum(case((PlanItem.status == PlanItemStatus.DONE, 1), else_=0)).label("done_items"),
    ).outerjoin(
        PlanItem, Plan.id == PlanItem.plan_id
    ).where(
        Plan.project_id == project_id,
    ).group_by(Plan.id).order_by(Plan.created_at.desc())

    result = await db.execute(plans_query)
    rows = result.all()

    plans = []
    total_items = 0
    total_done = 0
    for row in rows:
        t = row.total_items or 0
        d = row.done_items or 0
        total_items += t
        total_done += d
        plans.append({
            "id": row.id,
            "title": row.title,
            "status": row.status,
            "total_items": t,
            "done_items": d,
            "completion_rate": round(d / t * 100, 1) if t > 0 else 0,
        })

    # 按状态分组统计
    status_query = select(
        Plan.status,
        func.count(Plan.id).label("count"),
    ).where(Plan.project_id == project_id).group_by(Plan.status)
    status_result = await db.execute(status_query)
    by_status = {row.status: row.count for row in status_result.all()}

    return {
        "total_plans": len(plans),
        "overall_completion_rate": round(total_done / total_items * 100, 1) if total_items > 0 else 0,
        "total_items": total_items,
        "total_done_items": total_done,
        "by_status": by_status,
        "plans": plans,
    }


@router.get("/agent-activity")
async def agent_activity(
    project_id: int = Query(...),
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Agent 活跃度：每日操作次数、操作类型分布"""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # 每日操作次数
    daily_query = select(
        func.date(ActivityLog.created_at).label("date"),
        ActivityLog.actor,
        func.count(ActivityLog.id).label("count"),
    ).where(
        ActivityLog.project_id == project_id,
        ActivityLog.created_at >= since,
    ).group_by(
        func.date(ActivityLog.created_at),
        ActivityLog.actor,
    ).order_by(func.date(ActivityLog.created_at))

    daily_result = await db.execute(daily_query)
    daily_data = {}
    actors = set()
    for row in daily_result.all():
        date_str = str(row.date)
        actors.add(row.actor)
        if date_str not in daily_data:
            daily_data[date_str] = {}
        daily_data[date_str][row.actor] = row.count

    # 操作类型分布
    action_query = select(
        ActivityLog.actor,
        ActivityLog.action,
        func.count(ActivityLog.id).label("count"),
    ).where(
        ActivityLog.project_id == project_id,
        ActivityLog.created_at >= since,
    ).group_by(ActivityLog.actor, ActivityLog.action)
    action_result = await db.execute(action_query)
    action_distribution: dict[str, dict[str, int]] = {}
    for row in action_result.all():
        action_distribution.setdefault(row.actor, {})[row.action] = row.count

    # 构建每日时序数据
    daily_list = []
    for date_str in sorted(daily_data.keys()):
        entry = {"date": date_str}
        for actor in sorted(actors):
            entry[actor] = daily_data[date_str].get(actor, 0)
        daily_list.append(entry)

    return {
        "days": days,
        "actors": sorted(actors),
        "daily_activity": daily_list,
        "action_distribution": action_distribution,
    }


def _get_period_start(period: str) -> Optional[datetime]:
    """根据 period 参数计算起始时间"""
    now = datetime.now(timezone.utc)
    if period == "week":
        return now - timedelta(weeks=1)
    elif period == "month":
        return now - timedelta(days=30)
    return None  # all


@router.get("/burndown")
async def burndown_data(
    project_id: int = Query(...),
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    """燃尽图数据：统计每日剩余Issue数量"""
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    # 获取项目创建时间作为起点
    project_query = select(Issue.created_at).where(
        Issue.project_id == project_id
    ).order_by(Issue.created_at.asc()).limit(1)
    project_result = await db.execute(project_query)
    first_issue = project_result.scalar()

    if not first_issue:
        return {
            "days": days,
            "total_issues": 0,
            "data": [],
            "ideal": [],
        }

    # 获取项目起始日期
    project_start = first_issue.replace(hour=0, minute=0, second=0, microsecond=0)
    if project_start < start_date:
        project_start = start_date

    # 计算总Issue数
    total_query = select(func.count(Issue.id)).where(
        Issue.project_id == project_id,
        Issue.created_at >= project_start,
    )
    total_result = await db.execute(total_query)
    total_issues = total_result.scalar() or 0

    # 获取每天关闭的Issue数量
    closed_query = select(
        func.date(Issue.closed_at).label("date"),
        func.count(Issue.id).label("count"),
    ).where(
        Issue.project_id == project_id,
        Issue.status == IssueStatus.CLOSED,
        Issue.closed_at.isnot(None),
        Issue.closed_at >= project_start,
    ).group_by(
        func.date(Issue.closed_at)
    ).order_by(func.date(Issue.closed_at))

    closed_result = await db.execute(closed_query)
    closed_by_date = {str(row.date): row.count for row in closed_result.all()}

    # 构建燃尽数据
    data = []
    ideal = []
    cumulative_closed = 0

    for i in range((now - project_start).days + 1):
        current_date = project_start + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")

        # 累计关闭数
        cumulative_closed += closed_by_date.get(date_str, 0)
        remaining = max(0, total_issues - cumulative_closed)

        data.append({
            "date": date_str,
            "remaining": remaining,
        })

        # 理想燃尽线
        if i == 0:
            ideal.append({"date": date_str, "remaining": total_issues})
        else:
            days_elapsed = i
            days_total = (now - project_start).days
            if days_total > 0:
                ideal_remaining = max(0, total_issues * (1 - days_elapsed / days_total))
                ideal.append({"date": date_str, "remaining": round(ideal_remaining, 1)})
            else:
                ideal.append({"date": date_str, "remaining": 0})

    return {
        "days": days,
        "total_issues": total_issues,
        "data": data,
        "ideal": ideal,
    }


@router.get("/health")
async def project_health(
    project_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """项目健康度评估：多维度指标计算"""

    # 1. Issue 健康度
    # - 关闭率
    issue_stats_query = select(
        func.count(Issue.id).label("total"),
        func.sum(case((Issue.status == IssueStatus.CLOSED, 1), else_=0)).label("closed"),
        func.sum(case((Issue.status == IssueStatus.OPEN, 1), else_=0)).label("open"),
        func.sum(case((Issue.status == IssueStatus.IN_PROGRESS, 1), else_=0)).label("in_progress"),
        func.sum(case((Issue.priority == IssuePriority.P0, 1), else_=0)).label("p0"),
        func.sum(case((Issue.priority == IssuePriority.P1, 1), else_=0)).label("p1"),
    ).where(Issue.project_id == project_id)

    issue_result = await db.execute(issue_stats_query)
    issue_stats = issue_result.one()

    total_issues = issue_stats.total or 0
    closed_issues = issue_stats.closed or 0
    open_issues = issue_stats.open or 0
    in_progress = issue_stats.in_progress or 0
    p0_issues = issue_stats.p0 or 0
    p1_issues = issue_stats.p1 or 0

    # Issue 关闭率得分 (0-100)
    close_rate = (closed_issues / total_issues * 100) if total_issues > 0 else 100
    issue_score = min(100, close_rate)

    # P0/P1 未关闭扣分
    critical_unresolved = p0_issues + p1_issues
    if critical_unresolved > 0:
        issue_score = max(0, issue_score - critical_unresolved * 5)

    # 2. Plan 健康度
    plan_stats_query = select(
        func.count(Plan.id).label("total"),
        func.sum(case((Plan.status == PlanStatus.DONE, 1), else_=0)).label("completed"),
        func.sum(case((Plan.status == PlanStatus.IN_PROGRESS, 1), else_=0)).label("active"),
        func.sum(case((Plan.status == PlanStatus.PENDING, 1), else_=0)).label("pending"),
    ).where(Plan.project_id == project_id)

    plan_result = await db.execute(plan_stats_query)
    plan_stats = plan_result.one()

    total_plans = plan_stats.total or 0
    completed_plans = plan_stats.completed or 0
    pending_plans = plan_stats.pending or 0

    # Plan 完成率得分
    plan_close_rate = (completed_plans / total_plans * 100) if total_plans > 0 else 100
    plan_score = min(100, plan_close_rate)

    # 待审批Plan扣分
    if pending_plans > 0:
        plan_score = max(0, plan_score - pending_plans * 10)

    # 3. 活跃度得分（基于最近7天活动）
    recent_activity_query = select(func.count(ActivityLog.id)).where(
        ActivityLog.project_id == project_id,
        ActivityLog.created_at >= datetime.now(timezone.utc) - timedelta(days=7),
    )
    activity_result = await db.execute(recent_activity_query)
    recent_activities = activity_result.scalar() or 0

    # 活跃度得分：每天至少10个活动为满分
    activity_score = min(100, recent_activities / 7 * 10)

    # 4. 综合健康度
    overall_score = round(
        issue_score * 0.4 +
        plan_score * 0.3 +
        activity_score * 0.3
    )

    # 健康等级
    if overall_score >= 80:
        level = "excellent"
        color = "#52c41a"
    elif overall_score >= 60:
        level = "good"
        color = "#1890ff"
    elif overall_score >= 40:
        level = "warning"
        color = "#faad14"
    else:
        level = "critical"
        color = "#ff4d4f"

    # 建议
    suggestions = []
    if p0_issues > 0:
        suggestions.append(f"有 {p0_issues} 个 P0 紧急Issue待处理")
    if pending_plans > 0:
        suggestions.append(f"有 {pending_plans} 个Plan待审批")
    if recent_activities < 10:
        suggestions.append("最近7天活跃度较低")
    if close_rate < 50 and total_issues > 10:
        suggestions.append(f"Issue关闭率偏低 ({close_rate:.1f}%)")

    return {
        "overall_score": overall_score,
        "level": level,
        "color": color,
        "dimensions": {
            "issue": {
                "score": round(issue_score, 1),
                "details": {
                    "total": total_issues,
                    "closed": closed_issues,
                    "open": open_issues,
                    "in_progress": in_progress,
                    "p0": p0_issues,
                    "p1": p1_issues,
                    "close_rate": round(close_rate, 1),
                }
            },
            "plan": {
                "score": round(plan_score, 1),
                "details": {
                    "total": total_plans,
                    "completed": completed_plans,
                    "pending": pending_plans,
                    "close_rate": round(plan_close_rate, 1),
                }
            },
            "activity": {
                "score": round(activity_score, 1),
                "details": {
                    "recent_7days": recent_activities,
                }
            },
        },
        "suggestions": suggestions,
    }
