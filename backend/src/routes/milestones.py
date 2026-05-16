from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, case

from src.core.dependencies import get_db
from src.core.activity import log_activity
from src.models.milestone import Milestone
from src.models.issue import Issue, IssueStatus
from src.schemas.milestone import MilestoneCreate, MilestoneUpdate, MilestoneRead, MilestoneReadWithStats
from src.routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=List[MilestoneReadWithStats])
async def list_milestones(
    db: AsyncSession = Depends(get_db),
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    phase: Optional[str] = Query(None),
):
    """里程碑列表（含统计）"""
    query = select(Milestone).order_by(desc(Milestone.created_at))
    if project_id:
        query = query.where(Milestone.project_id == project_id)
    if status:
        query = query.where(Milestone.status == status)
    if phase:
        query = query.where(Milestone.phase == phase)
    result = await db.execute(query)
    milestones = result.scalars().all()

    out = []
    for m in milestones:
        stats = await db.execute(
            select(
                func.count(Issue.id).label("total"),
                func.sum(case((Issue.status == IssueStatus.OPEN, 1), else_=0)).label("open"),
                func.sum(case((Issue.status == IssueStatus.CLOSED, 1), else_=0)).label("closed"),
                func.sum(case((Issue.status == IssueStatus.DEFERRED, 1), else_=0)).label("deferred"),
            ).where(Issue.milestone_id == m.id)
        )
        row = stats.one()
        out.append(MilestoneReadWithStats(
            id=m.id,
            project_id=m.project_id,
            title=m.title,
            description=m.description,
            phase=m.phase,
            status=m.status,
            due_date=m.due_date,
            created_at=m.created_at,
            updated_at=m.updated_at,
            total_issues=row.total or 0,
            open_issues=row.open or 0,
            closed_issues=row.closed or 0,
            deferred_issues=row.deferred or 0,
        ))
    return out


@router.post("", response_model=MilestoneRead, status_code=201)
async def create_milestone(data: MilestoneCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """创建里程碑"""
    milestone = Milestone(**data.model_dump())
    db.add(milestone)
    await db.commit()
    await db.refresh(milestone)

    await log_activity(
        db, entity_type="milestone", entity_id=milestone.id,
        actor=user["sub"], action="created",
        new_value={"title": milestone.title, "status": milestone.status},
        project_id=milestone.project_id,
    )
    return milestone


@router.get("/{milestone_id}", response_model=MilestoneReadWithStats)
async def get_milestone(milestone_id: int, db: AsyncSession = Depends(get_db)):
    """里程碑详情（含统计）"""
    result = await db.execute(select(Milestone).where(Milestone.id == milestone_id))
    milestone = result.scalar_one_or_none()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    # 用 case-when 聚合统计该里程碑下的 issues
    stats_result = await db.execute(
        select(
            func.count(Issue.id).label("total"),
            func.sum(case((Issue.status == IssueStatus.OPEN, 1), else_=0)).label("open"),
            func.sum(case((Issue.status == IssueStatus.CLOSED, 1), else_=0)).label("closed"),
            func.sum(case((Issue.status == IssueStatus.DEFERRED, 1), else_=0)).label("deferred"),
        ).where(Issue.milestone_id == milestone_id)
    )
    row = stats_result.one()

    # 构造返回数据，避免触发 lazy load
    return MilestoneReadWithStats(
        id=milestone.id,
        title=milestone.title,
        description=milestone.description,
        phase=milestone.phase,
        status=milestone.status,
        due_date=milestone.due_date,
        created_at=milestone.created_at,
        updated_at=milestone.updated_at,
        total_issues=row.total or 0,
        open_issues=row.open or 0,
        closed_issues=row.closed or 0,
        deferred_issues=row.deferred or 0,
    )


@router.put("/{milestone_id}", response_model=MilestoneRead)
async def update_milestone(milestone_id: int, data: MilestoneUpdate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """更新里程碑"""
    result = await db.execute(select(Milestone).where(Milestone.id == milestone_id))
    milestone = result.scalar_one_or_none()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(milestone, key, value)

    await db.commit()
    await db.refresh(milestone)

    await log_activity(
        db, entity_type="milestone", entity_id=milestone.id,
        actor=user["sub"], action="updated",
        new_value=update_data,
        project_id=milestone.project_id,
    )
    return milestone


@router.delete("/{milestone_id}", status_code=204)
async def delete_milestone(milestone_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """删除里程碑"""
    result = await db.execute(select(Milestone).where(Milestone.id == milestone_id))
    milestone = result.scalar_one_or_none()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    linked = await db.execute(
        select(func.count(Issue.id)).where(Issue.milestone_id == milestone_id)
    )
    if linked.scalar() > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete milestone with linked issues. Remove or reassign issues first.",
        )

    await log_activity(
        db, entity_type="milestone", entity_id=milestone.id,
        actor=user["sub"], action="deleted",
        old_value={"title": milestone.title, "status": milestone.status},
        project_id=milestone.project_id,
    )
    await db.delete(milestone)
    await db.commit()
    return None
