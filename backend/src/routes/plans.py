from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, case
from sqlalchemy.orm import selectinload

from src.core.dependencies import get_db
from src.models.plan import Plan, PlanStatus
from src.models.plan_item import PlanItem, PlanItemStatus
from src.schemas.plan import (
    PlanCreate, PlanUpdate, PlanRead, PlanReadWithItems, PlanReadWithStats,
    PlanItemCreate, PlanItemUpdate, PlanItemRead,
)
from src.routes.auth import get_current_user, require_role

router = APIRouter(dependencies=[Depends(get_current_user)])


# ── Plans ──────────────────────────────────────────

@router.get("", response_model=List[PlanReadWithStats])
async def list_plans(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
):
    """计划列表"""
    query = select(Plan).order_by(desc(Plan.created_at))
    if status:
        query = query.where(Plan.status == status)
    if project_id:
        query = query.where(Plan.project_id == project_id)
    result = await db.execute(query)
    plans = result.scalars().all()

    out = []
    for p in plans:
        stats = await db.execute(
            select(
                func.count(PlanItem.id).label("total"),
                func.sum(case((PlanItem.status == PlanItemStatus.DONE, 1), else_=0)).label("done"),
            ).where(PlanItem.plan_id == p.id)
        )
        row = stats.one()
        out.append(PlanReadWithStats(
            id=p.id,
            project_id=p.project_id,
            title=p.title,
            description=p.description,
            status=p.status,
            proposed_by=p.proposed_by,
            approved_by=p.approved_by,
            approved_at=p.approved_at,
            reject_reason=p.reject_reason,
            created_at=p.created_at,
            updated_at=p.updated_at,
            item_count=row.total or 0,
            item_done_count=row.done or 0,
        ))
    return out


@router.post("", response_model=PlanRead, status_code=201)
async def create_plan(data: PlanCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "agent"))):
    plan = Plan(**data.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.get("/{plan_id}", response_model=PlanReadWithItems)
async def get_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    """计划详情（含 plan_items）"""
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id).options(selectinload(Plan.plan_items))
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.put("/{plan_id}", response_model=PlanRead)
async def update_plan(plan_id: int, data: PlanUpdate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "agent"))):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    update_data = data.model_dump(exclude_unset=True)

    if update_data.get("status") == PlanStatus.PENDING and plan.status == PlanStatus.REJECTED:
        plan.reject_reason = None
        plan.approved_by = None
        plan.approved_at = None

    for key, value in update_data.items():
        setattr(plan, key, value)

    await db.commit()
    await db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(plan_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin"))):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    await db.delete(plan)
    await db.commit()
    return None


# ── Approval ───────────────────────────────────────

@router.post("/{plan_id}/approve", response_model=PlanRead)
async def approve_plan(plan_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "mate"))):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != PlanStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending plans can be approved")

    plan.status = PlanStatus.APPROVED
    plan.approved_by = user["sub"]
    plan.approved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(plan)
    return plan


@router.post("/{plan_id}/reject", response_model=PlanRead)
async def reject_plan(plan_id: int, reason: Optional[str] = Body(None, embed=True), db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "mate"))):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != PlanStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending plans can be rejected")

    plan.status = PlanStatus.REJECTED
    plan.reject_reason = reason

    await db.commit()
    await db.refresh(plan)
    return plan


# ── Plan Items ─────────────────────────────────────

@router.get("/{plan_id}/items", response_model=List[PlanItemRead])
async def list_plan_items(plan_id: int, db: AsyncSession = Depends(get_db)):
    """计划项列表"""
    result = await db.execute(
        select(PlanItem).where(PlanItem.plan_id == plan_id).order_by(PlanItem.sort_order)
    )
    return result.scalars().all()


@router.post("/{plan_id}/items", response_model=PlanItemRead, status_code=201)
async def create_plan_item(plan_id: int, data: PlanItemCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "agent"))):
    plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status not in (PlanStatus.APPROVED, PlanStatus.DONE):
        raise HTTPException(status_code=400, detail=f"Plan 状态为 '{plan.status}'，无法添加进度项。只有 approved 或 done 状态的 Plan 才能更新进度。")

    item = PlanItem(plan_id=plan_id, **data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.put("/{plan_id}/items/{item_id}", response_model=PlanItemRead)
async def update_plan_item(
    plan_id: int, item_id: int, data: PlanItemUpdate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "agent"))
):
    result = await db.execute(
        select(PlanItem).where(PlanItem.id == item_id, PlanItem.plan_id == plan_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="PlanItem not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{plan_id}/items/{item_id}", status_code=204)
async def delete_plan_item(plan_id: int, item_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin"))):
    result = await db.execute(
        select(PlanItem).where(PlanItem.id == item_id, PlanItem.plan_id == plan_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="PlanItem not found")

    await db.delete(item)
    await db.commit()
    return None
