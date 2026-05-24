from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, case
from sqlalchemy.orm import selectinload

from src.core.dependencies import get_db
from src.core.activity import log_activity
from src.core.notification import create_notification
from src.models.plan import Plan, PlanStatus
from src.models.plan_item import PlanItem, PlanItemStatus
from src.models.notification import NotificationType
from src.schemas.plan import (
    PlanCreate, PlanUpdate, PlanRead, PlanReadWithItems, PlanReadWithStats,
    PlanItemCreate, PlanItemUpdate, PlanItemRead,
)
from src.routes.auth import get_current_user

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
            proposed_by_name=p.proposed_by_name,
            approved_by=p.approved_by,
            approved_at=p.approved_at,
            reject_reason=p.reject_reason,
            current_milestone_id=p.current_milestone_id,
            created_at=p.created_at,
            updated_at=p.updated_at,
            item_count=row.total or 0,
            item_done_count=row.done or 0,
        ))
    return out


@router.post("", response_model=PlanRead, status_code=201)
async def create_plan(data: PlanCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    plan = Plan(**data.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    await log_activity(
        db, entity_type="plan", entity_id=plan.id,
        actor=user["sub"],
        action="created",
        new_value={"title": plan.title, "status": plan.status, "proposed_by": plan.proposed_by},
        project_id=plan.project_id,
    )

    # Plan pending_approval → 通知 admin 审批
    if plan.status == PlanStatus.PENDING_APPROVAL:
        await create_notification(
            db, recipient="admin",
            type=NotificationType.APPROVAL_NEEDED,
            title=f"Plan #{plan.id} 等待审批",
            body=plan.title,
            entity_type="plan", entity_id=plan.id,
            created_by=user["sub"],
            project_id=plan.project_id,
        )

        # 给提议者发确认通知
        proposer = plan.proposed_by_name or plan.proposed_by
        if proposer and proposer != "admin" and proposer != "user":
            await create_notification(
                db, recipient=proposer,
                type=NotificationType.INFO,
                title=f"Plan #{plan.id} 已提交，等待审批",
                body=plan.title,
                entity_type="plan", entity_id=plan.id,
                created_by="system",
                project_id=plan.project_id,
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
async def update_plan(plan_id: int, data: PlanUpdate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    old_values = {k: getattr(plan, k) for k in ["title", "description", "status", "current_milestone_id"]}

    update_data = data.model_dump(exclude_unset=True)

    # 如果从 abandoned 重新提交为 pending_approval，清除 reject_reason
    if update_data.get("status") == PlanStatus.PENDING_APPROVAL and plan.status == PlanStatus.ABANDONED:
        plan.reject_reason = None
        plan.approved_by = None
        plan.approved_at = None

    for key, value in update_data.items():
        setattr(plan, key, value)

    await db.commit()
    await db.refresh(plan)

    await log_activity(
        db, entity_type="plan", entity_id=plan.id,
        action="updated", actor=user["sub"],
        old_value=old_values,
        new_value={k: getattr(plan, k) for k in old_values.keys()},
        project_id=plan.project_id,
    )

    # 重新提交审批时通知 admin
    if update_data.get("status") == PlanStatus.PENDING_APPROVAL and old_values.get("status") == PlanStatus.ABANDONED:
        await create_notification(
            db, recipient="admin",
            type=NotificationType.APPROVAL_NEEDED,
            title=f"Plan #{plan.id} 重新提交审批",
            body=plan.title,
            entity_type="plan", entity_id=plan.id,
            created_by=user["sub"],
            project_id=plan.project_id,
        )

    return plan


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(plan_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    await log_activity(
        db, entity_type="plan", entity_id=plan.id,
        action="deleted", actor=user["sub"],
        old_value={"title": plan.title},
        project_id=plan.project_id,
    )

    await db.delete(plan)
    await db.commit()
    return None


# ── Approval ───────────────────────────────────────

@router.post("/{plan_id}/approve", response_model=PlanRead)
async def approve_plan(plan_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != PlanStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Only pending_approval plans can be approved")

    old_status = plan.status
    plan.status = PlanStatus.ACTIVE
    plan.approved_by = user["sub"]
    plan.approved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(plan)

    await log_activity(
        db, entity_type="plan", entity_id=plan.id,
        action="approved", actor=user["sub"],
        old_value={"status": old_status},
        new_value={"status": plan.status, "approved_by": plan.approved_by},
        project_id=plan.project_id,
    )

    # 通知 plan 提议者审批通过
    recipient = plan.proposed_by_name or plan.proposed_by
    if recipient and recipient != "user":
        await create_notification(
            db, recipient=recipient,
            type=NotificationType.INFO,
            title=f"Plan #{plan.id} 已审批通过",
            body=plan.title,
            entity_type="plan", entity_id=plan.id,
            created_by=user["sub"],
            project_id=plan.project_id,
        )

    # 检查并触发 on_plan_approved 工作流
    try:
        from src.core.workflow_engine import check_and_trigger_workflows
        await check_and_trigger_workflows(
            db, trigger_type="on_plan_approved",
            project_id=plan.project_id,
            context={"plan_id": plan.id, "plan_title": plan.title},
        )
    except Exception:
        pass

    return plan


@router.post("/{plan_id}/reject", response_model=PlanRead)
async def reject_plan(plan_id: int, reason: Optional[str] = Body(None, embed=True), db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != PlanStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Only pending_approval plans can be rejected")

    old_status = plan.status
    plan.status = PlanStatus.ABANDONED
    plan.reject_reason = reason

    await db.commit()
    await db.refresh(plan)

    await log_activity(
        db, entity_type="plan", entity_id=plan.id,
        action="rejected", actor=user["sub"],
        old_value={"status": old_status},
        new_value={"status": plan.status, "reject_reason": reason},
        project_id=plan.project_id,
    )

    # 通知 plan 提议者被拒绝
    recipient = plan.proposed_by_name or plan.proposed_by
    if recipient and recipient != "user":
        await create_notification(
            db, recipient=recipient,
            type=NotificationType.INFO,
            title=f"Plan #{plan.id} 被拒绝",
            body=f"{plan.title} - 原因: {reason or '无'}",
            entity_type="plan", entity_id=plan.id,
            created_by=user["sub"],
            project_id=plan.project_id,
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
async def create_plan_item(plan_id: int, data: PlanItemCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status not in (PlanStatus.ACTIVE, PlanStatus.COMPLETED):
        raise HTTPException(status_code=400, detail=f"Plan 状态为 '{plan.status}'，无法添加进度项。只有 active 或 completed 状态的 Plan 才能更新进度。")

    item = PlanItem(plan_id=plan_id, **data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)

    await log_activity(
        db, entity_type="plan_item", entity_id=item.id,
        action="created", actor=user["sub"],
        new_value={"title": item.title, "plan_id": plan_id},
        project_id=plan.project_id,
    )
    return item


@router.put("/{plan_id}/items/{item_id}", response_model=PlanItemRead)
async def update_plan_item(
    plan_id: int, item_id: int, data: PlanItemUpdate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)
):
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

    # 获取 plan 的 project_id
    plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = plan_result.scalar_one_or_none()

    await log_activity(
        db, entity_type="plan_item", entity_id=item.id,
        action=action, actor=user["sub"],
        old_value={"status": old_status},
        new_value={"status": item.status, "completed_by": item.completed_by},
        project_id=plan.project_id if plan else None,
    )
    return item


@router.delete("/{plan_id}/items/{item_id}", status_code=204)
async def delete_plan_item(plan_id: int, item_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(PlanItem).where(PlanItem.id == item_id, PlanItem.plan_id == plan_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="PlanItem not found")

    # 获取 plan 的 project_id
    plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = plan_result.scalar_one_or_none()

    await log_activity(
        db, entity_type="plan_item", entity_id=item.id,
        action="deleted", actor=user["sub"],
        old_value={"title": item.title},
        project_id=plan.project_id if plan else None,
    )

    await db.delete(item)
    await db.commit()
    return None
