"""
系统监控 API
提供健康检查、性能指标、业务统计等监控数据
"""
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from src.core.dependencies import get_db
from src.routes.auth import get_current_user
from src.models.issue import Issue, IssueStatus, IssuePriority
from src.models.plan import Plan, PlanStatus
from src.models.activity_log import ActivityLog
from src.models.comment import Comment

router = APIRouter(dependencies=[Depends(get_current_user)])
public_router = APIRouter()


@public_router.get("/config")
async def get_system_config():
    """系统配置（公开，无需认证）"""
    import os
    ai_enabled = os.getenv("PM_COPILOT_ENABLED", "false").lower() == "true"
    try:
        from src.routes.copilot import get_copilot
        copilot_ready = get_copilot() is not None
    except Exception:
        copilot_ready = False
    return {
        "ai_enabled": ai_enabled and copilot_ready,
        "features": {
            "copilot_chat": ai_enabled and copilot_ready,
            "ai_scan": ai_enabled and copilot_ready,
            "risk_alert_auto": ai_enabled and copilot_ready,
        },
    }


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
        func.sum(case((Issue.status == IssueStatus.OPEN, 1), else_=0)).label("open"),
        func.sum(case((Issue.status == IssueStatus.IN_PROGRESS, 1), else_=0)).label("in_progress"),
        func.sum(case((Issue.status == IssueStatus.REVIEW, 1), else_=0)).label("review"),
        func.sum(case((Issue.status == IssueStatus.CLOSED, 1), else_=0)).label("closed"),
        func.sum(case((Issue.priority == IssuePriority.P0, 1), else_=0)).label("p0"),
        func.sum(case((Issue.priority == IssuePriority.P1, 1), else_=0)).label("p1"),
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
        func.sum(case((Plan.status == PlanStatus.PENDING, 1), else_=0)).label("pending"),
        func.sum(case((Plan.status == PlanStatus.IN_PROGRESS, 1), else_=0)).label("active"),
        func.sum(case((Plan.status == PlanStatus.DONE, 1), else_=0)).label("completed"),
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


@router.get("/stuck-workflows")
async def get_stuck_workflows(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """检测卡住的工作流：长时间未变更状态的 Issue/Plan
    
    检测规则：
    - Issue 处于 in_progress/review 状态超过 N 小时未变更
    - Plan 处于 pending_approval/active 状态超过 N 小时未变更
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(hours=hours)
    
    # 1. 卡住的 Issue：状态为 in_progress 或 review，且最近更新时间早于 threshold
    stuck_issues_query = select(Issue).where(
        Issue.status.in_([IssueStatus.IN_PROGRESS, IssueStatus.REVIEW]),
        Issue.updated_at <= threshold,
    ).order_by(Issue.updated_at)
    
    stuck_issues_result = await db.execute(stuck_issues_query)
    stuck_issues = stuck_issues_result.scalars().all()
    
    # 2. 卡住的 Plan：pending 或 in_progress 且长时间未更新
    stuck_plans_query = select(Plan).where(
        Plan.status.in_([PlanStatus.PENDING, PlanStatus.IN_PROGRESS]),
        Plan.updated_at <= threshold,
    ).order_by(Plan.updated_at)
    
    stuck_plans_result = await db.execute(stuck_plans_query)
    stuck_plans = stuck_plans_result.scalars().all()
    
    def format_stuck_duration(updated_at):
        if not updated_at:
            return "未知"
        # 统一为 offset-aware 后再相减
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        delta = now - updated_at
        hours = delta.total_seconds() / 3600
        if hours < 24:
            return f"{hours:.1f} 小时"
        else:
            days = hours / 24
            return f"{days:.1f} 天"
    
    return {
        "threshold_hours": hours,
        "timestamp": now.isoformat(),
        "stuck_issues": [
            {
                "id": issue.id,
                "title": issue.title,
                "status": issue.status,
                "priority": issue.priority,
                "assignee": issue.assignee,
                "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
                "stuck_duration": format_stuck_duration(issue.updated_at),
            }
            for issue in stuck_issues
        ],
        "stuck_plans": [
            {
                "id": plan.id,
                "title": plan.title,
                "status": plan.status,
                "proposed_by": plan.proposed_by,
                "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
                "stuck_duration": format_stuck_duration(plan.updated_at),
            }
            for plan in stuck_plans
        ],
        "total_stuck": len(stuck_issues) + len(stuck_plans),
    }


@public_router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
):
    """服务健康检查（无需认证，供 Docker/K8s 使用）"""
    try:
        # 检查数据库连接
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════
#  死信队列管理
# ═══════════════════════════════════════════════════════

@router.get("/dead-letter")
async def list_dead_letter_messages(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """查看死信队列消息"""
    from sqlalchemy import text
    import json

    # 总数
    count_result = await db.execute(text("SELECT COUNT(*) FROM message_queue_dead_letter"))
    total = count_result.scalar() or 0

    # 分页查询
    result = await db.execute(text("""
        SELECT id, payload, original_status, retry_count, error, moved_at
        FROM message_queue_dead_letter
        ORDER BY moved_at DESC
        LIMIT :limit OFFSET :skip
    """), {"limit": limit, "skip": skip})
    rows = result.fetchall()

    items = []
    for row in rows:
        msg_id, payload, orig_status, retry_count, error, moved_at = row
        try:
            parsed = json.loads(payload) if isinstance(payload, str) else payload
        except Exception:
            parsed = {"raw": payload}
        items.append({
            "id": msg_id,
            "payload": parsed,
            "original_status": orig_status,
            "retry_count": retry_count,
            "error": error,
            "moved_at": moved_at.isoformat() if moved_at else None,
        })

    return {"total": total, "items": items}


@router.post("/dead-letter/{msg_id}/retry")
async def retry_dead_letter_message(
    msg_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """重试死信消息：移回主队列"""
    from sqlalchemy import text
    import json

    result = await db.execute(text(
        "SELECT id, payload, retry_count FROM message_queue_dead_letter WHERE id = :id"
    ), {"id": msg_id})
    row = result.fetchone()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Dead letter message not found")

    _, payload, retry_count = row

    # 移回主队列，重置重试计数
    await db.execute(text("""
        INSERT INTO message_queue (payload, status, retry_count, created_at)
        VALUES (:payload, 'pending', 0, :created_at)
    """), {
        "payload": payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # 从死信表删除
    await db.execute(text("DELETE FROM message_queue_dead_letter WHERE id = :id"), {"id": msg_id})
    await db.commit()

    return {"message": f"Dead letter message #{msg_id} moved back to queue", "retry_count": retry_count}


@router.delete("/dead-letter/{msg_id}")
async def delete_dead_letter_message(
    msg_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除死信消息"""
    from sqlalchemy import text

    result = await db.execute(text(
        "SELECT id FROM message_queue_dead_letter WHERE id = :id"
    ), {"id": msg_id})
    if not result.fetchone():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Dead letter message not found")

    await db.execute(text("DELETE FROM message_queue_dead_letter WHERE id = :id"), {"id": msg_id})
    await db.commit()
    return {"message": f"Dead letter message #{msg_id} deleted"}


@router.get("/queue-stats")
async def get_queue_stats(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """消息队列统计"""
    from sqlalchemy import text

    # 主队列统计
    main_result = await db.execute(text("""
        SELECT status, COUNT(*) as cnt FROM message_queue GROUP BY status
    """))
    main_stats = {row[0]: row[1] for row in main_result.fetchall()}

    # 死信数量
    dead_result = await db.execute(text("SELECT COUNT(*) FROM message_queue_dead_letter"))
    dead_count = dead_result.scalar() or 0

    return {
        "queue": {
            "pending": main_stats.get("pending", 0),
            "processing": main_stats.get("processing", 0),
            "total": sum(main_stats.values()),
        },
        "dead_letter": dead_count,
    }
