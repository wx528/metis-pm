from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from src.core.dependencies import get_db
from src.routes.auth import get_current_user
from src.models.activity_log import ActivityLog
from src.models.issue import Issue, IssueStatus
from src.models.comment import Comment

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/agents")
async def get_agent_status(
    project_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取各 Agent 角色的实时状态和待交接任务"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. 获取所有 activity_log 中的 identity（actor）列表
    actors_query = select(ActivityLog.actor).distinct()
    if project_id:
        actors_query = actors_query.where(ActivityLog.project_id == project_id)
    actors_result = await db.execute(actors_query)
    actors = [row[0] for row in actors_result.all() if row[0] and row[0] != "user"]

    # 2. 为每个 actor 计算状态
    agents = []
    for actor in actors:
        # 最近活动时间
        last_query = select(ActivityLog.created_at).where(ActivityLog.actor == actor)
        if project_id:
            last_query = last_query.where(ActivityLog.project_id == project_id)
        last_query = last_query.order_by(desc(ActivityLog.created_at)).limit(1)
        last_result = await db.execute(last_query)
        last_active = last_result.scalar()

        # 状态判断
        if last_active:
            delta = now - last_active
            if delta < timedelta(hours=1):
                status = "online"
            elif delta < timedelta(hours=4):
                status = "idle"
            else:
                status = "offline"
        else:
            status = "offline"
            last_active = None

        # 今日统计
        today_created = 0
        today_completed = 0
        today_reviewed = 0
        if last_active:
            stats_query = select(
                ActivityLog.action,
                func.count(ActivityLog.id),
            ).where(
                ActivityLog.actor == actor,
                ActivityLog.created_at >= today_start,
            )
            if project_id:
                stats_query = stats_query.where(ActivityLog.project_id == project_id)
            stats_query = stats_query.group_by(ActivityLog.action)
            stats_result = await db.execute(stats_query)
            stats_map = {row.action: row[1] for row in stats_result.all()}
            today_created = stats_map.get("created", 0)
            today_completed = stats_map.get("completed", 0)
            today_reviewed = stats_map.get("approved", 0) + stats_map.get("rejected", 0)

        # 待办任务数（简化：所有 open/in_progress issues）
        pending_tasks = 0
        pending_query = select(func.count(Issue.id)).where(
            Issue.status.in_([IssueStatus.OPEN, IssueStatus.IN_PROGRESS]),
        )
        if project_id:
            pending_query = pending_query.where(Issue.project_id == project_id)
        pending_result = await db.execute(pending_query)
        pending_tasks = pending_result.scalar() or 0

        # 推断角色
        role = "agent"
        if "mate" in actor.lower():
            role = "mate"
        elif "tester" in actor.lower():
            role = "tester"
        elif "registrar" in actor.lower():
            role = "registrar"

        agents.append({
            "role": role,
            "identity": actor,
            "last_active": last_active.isoformat() if last_active else None,
            "status": status,
            "today_created": today_created,
            "today_completed": today_completed,
            "today_reviewed": today_reviewed,
            "pending_tasks": pending_tasks,
        })

    # 3. 获取待交接任务（最近 24h 的 handover 评论）
    day_ago = now - timedelta(hours=24)
    handover_query = select(Comment).where(
        Comment.comment_type == "handover",
        Comment.created_at >= day_ago,
    ).order_by(desc(Comment.created_at)).limit(20)
    handover_result = await db.execute(handover_query)
    handover_comments = handover_result.scalars().all()

    pending_handovers = []
    import re
    for c in handover_comments:
        content = c.content or ""
        title_line = content.split("\n")[0] if content else ""
        issue_match = re.search(r'#(\d+)', title_line)
        issue_id = int(issue_match.group(1)) if issue_match else c.issue_id
        at_match = re.search(r'@(\w+)', content)
        to_role = at_match.group(1) if at_match else "unknown"

        pending_handovers.append({
            "issue_id": issue_id,
            "from_role": c.author or "unknown",
            "to_role": to_role,
            "title": title_line.replace("## ", "").strip(),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return {
        "agents": agents,
        "pending_handovers": pending_handovers,
    }
