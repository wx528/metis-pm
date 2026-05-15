from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from src.core.dependencies import get_db
from src.core.activity import log_activity
from src.models.plan import Plan, PlanStatus
from src.models.plan_item import PlanItem, PlanItemStatus
from src.schemas.plan import (
    PlanCreate, PlanUpdate, PlanRead, PlanReadWithItems,
    PlanItemCreate, PlanItemUpdate, PlanItemRead,
)
from src.routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


# ── Plans ──────────────────────────────────────────

@router.get("", response_model=List[PlanRead])
async def list_plans(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = Query(None),
):
    """计划列表"""
    query = select(Plan).order_by(desc(Plan.created_at))
    if status:
        query = query.where(Plan.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=PlanRead, status_code=201)
async def create_plan(data: PlanCreate, db: AsyncSession = Depends(get_db)):
    """创建计划"""
    plan = Plan(**data.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    await log_activity(
        db, entity_type="plan", entity_id=plan.id,
        action="created", actor=plan.proposed_by or "user",
        new_value={"title": plan.title, "status": plan.status, "proposed_by": plan.proposed_by},
    )
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
async def update_plan(plan_id: int, data: PlanUpdate, db: AsyncSession = Depends(get_db)):
    """更新计划"""
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    old_values = {k: getattr(plan, k) for k in ["title", "description", "status", "current_milestone_id"]}

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(plan, key, value)

    await db.commit()
    await db.refresh(plan)

    await log_activity(
        db, entity_type="plan", entity_id=plan.id,
        action="updated", actor="user",
        old_value=old_values,
        new_value={k: getattr(plan, k) for k in old_values.keys()},
    )
    return plan


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    """删除计划"""
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    await log_activity(
        db, entity_type="plan", entity_id=plan.id,
        action="deleted", actor="user",
        old_value={"title": plan.title},
    )

    await db.delete(plan)
    await db.commit()
    return None


# ── Approval ───────────────────────────────────────

@router.post("/{plan_id}/approve", response_model=PlanRead)
async def approve_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    """审批通过计划"""
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != PlanStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Only pending_approval plans can be approved")

    old_status = plan.status
    plan.status = PlanStatus.ACTIVE
    plan.approved_by = "user"
    plan.approved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(plan)

    await log_activity(
        db, entity_type="plan", entity_id=plan.id,
        action="approved", actor="user",
        old_value={"status": old_status},
        new_value={"status": plan.status, "approved_by": plan.approved_by},
    )
    return plan


@router.post("/{plan_id}/reject", response_model=PlanRead)
async def reject_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    """拒绝计划"""
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != PlanStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Only pending_approval plans can be rejected")

    old_status = plan.status
    plan.status = PlanStatus.ABANDONED
    plan.approved_by = "user"
    plan.approved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(plan)

    await log_activity(
        db, entity_type="plan", entity_id=plan.id,
        action="rejected", actor="user",
        old_value={"status": old_status},
        new_value={"status": plan.status, "approved_by": plan.approved_by},
    )
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
async def create_plan_item(plan_id: int, data: PlanItemCreate, db: AsyncSession = Depends(get_db)):
    """添加计划项"""
    plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    item = PlanItem(plan_id=plan_id, **data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)

    await log_activity(
        db, entity_type="plan_item", entity_id=item.id,
        action="created", actor="user",
        new_value={"title": item.title, "plan_id": plan_id},
    )
    return item


@router.put("/{plan_id}/items/{item_id}", response_model=PlanItemRead)
async def update_plan_item(
    plan_id: int, item_id: int, data: PlanItemUpdate, db: AsyncSession = Depends(get_db)
):
    """更新计划项"""
    result = await db.execute(
        select(PlanItem).where(PlanItem.id == item_id, PlanItem.plan_id == plan_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="PlanItem not found")

    old_status = item.status
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    await db.commit()
    await db.refresh(item)

    action = "updated"
    if "status" in update_data and update_data["status"] != old_status:
        action = "completed" if update_data["status"] == "done" else "status_changed"

    await log_activity(
        db, entity_type="plan_item", entity_id=item.id,
        action=action, actor=data.completed_by or "user",
        old_value={"status": old_status},
        new_value={"status": item.status, "completed_by": item.completed_by},
    )
    return item


@router.delete("/{plan_id}/items/{item_id}", status_code=204)
async def delete_plan_item(plan_id: int, item_id: int, db: AsyncSession = Depends(get_db)):
    """删除计划项"""
    result = await db.execute(
        select(PlanItem).where(PlanItem.id == item_id, PlanItem.plan_id == plan_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="PlanItem not found")

    await log_activity(
        db, entity_type="plan_item", entity_id=item.id,
        action="deleted", actor="user",
        old_value={"title": item.title},
    )

    await db.delete(item)
    await db.commit()
    return None
