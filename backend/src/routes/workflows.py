"""Phase 6 — 工作流 CRUD 路由"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from src.core.dependencies import get_db
from src.core.activity import log_activity
from src.models.workflow import Workflow, WorkflowStep, WorkflowRun, WorkflowStatus, WorkflowRunStatus
from src.schemas.workflow import (
    WorkflowCreate, WorkflowUpdate, WorkflowRead, WorkflowReadWithSteps,
    WorkflowStepCreate, WorkflowStepRead,
    WorkflowRunRead, WorkflowRunReadWithDetails,
)
from src.routes.auth import get_current_user, require_role

router = APIRouter(dependencies=[Depends(get_current_user)])


# ── Workflow CRUD ─────────────────────────────────

@router.get("", response_model=List[WorkflowReadWithSteps])
async def list_workflows(
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """工作流列表（含步骤概要）"""
    query = select(Workflow).order_by(desc(Workflow.created_at)).options(selectinload(Workflow.steps))
    if project_id:
        query = query.where(Workflow.project_id == project_id)
    if status:
        query = query.where(Workflow.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=WorkflowReadWithSteps, status_code=201)
async def create_workflow(
    data: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("admin", "agent")),
):
    """创建工作流（含步骤）"""
    workflow = Workflow(
        name=data.name,
        description=data.description,
        project_id=data.project_id,
        trigger=data.trigger,
        trigger_config=data.trigger_config,
        status=data.status,
        created_by=user["sub"],
    )
    db.add(workflow)
    await db.flush()  # 获取 workflow.id

    for i, step_data in enumerate(data.steps):
        step = WorkflowStep(
            workflow_id=workflow.id,
            step_type=step_data.step_type,
            name=step_data.name,
            config=step_data.config,
            sort_order=step_data.sort_order or i,
            timeout_seconds=step_data.timeout_seconds,
            on_failure=step_data.on_failure,
        )
        db.add(step)

    await db.commit()
    await db.refresh(workflow)

    # 重新查询以获取 steps
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow.id).options(selectinload(Workflow.steps))
    )
    workflow = result.scalar_one()

    await log_activity(
        db, entity_type="workflow", entity_id=workflow.id,
        actor=user["sub"], action="created",
        new_value={"name": workflow.name, "trigger": workflow.trigger},
        project_id=workflow.project_id,
    )
    return workflow


# ── Workflow Runs (must be before /{workflow_id} to avoid route conflict) ──

@router.get("/runs", response_model=List[WorkflowRunReadWithDetails])
async def list_workflow_runs(
    workflow_id: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """工作流执行记录"""
    query = select(WorkflowRun).order_by(desc(WorkflowRun.started_at))
    if workflow_id:
        query = query.where(WorkflowRun.workflow_id == workflow_id)
    if status:
        query = query.where(WorkflowRun.status == status)
    query = query.limit(limit)
    result = await db.execute(query)
    runs = result.scalars().all()

    out = []
    for run in runs:
        wf = await db.execute(select(Workflow.name).where(Workflow.id == run.workflow_id))
        wf_name = wf.scalar()
        out.append(WorkflowRunReadWithDetails(
            id=run.id,
            workflow_id=run.workflow_id,
            triggered_by=run.triggered_by,
            status=run.status,
            current_step_index=run.current_step_index,
            context=run.context,
            error_message=run.error_message,
            started_at=run.started_at,
            completed_at=run.completed_at,
            workflow_name=wf_name,
        ))
    return out


@router.get("/runs/{run_id}", response_model=WorkflowRunRead)
async def get_workflow_run(run_id: int, db: AsyncSession = Depends(get_db)):
    """工作流执行详情"""
    result = await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run


@router.get("/{workflow_id}", response_model=WorkflowReadWithSteps)
async def get_workflow(workflow_id: int, db: AsyncSession = Depends(get_db)):
    """工作流详情（含步骤）"""
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id).options(selectinload(Workflow.steps))
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.put("/{workflow_id}", response_model=WorkflowRead)
async def update_workflow(
    workflow_id: int,
    data: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("admin", "agent")),
):
    """更新工作流"""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(workflow, key, value)
    await db.commit()
    await db.refresh(workflow)

    await log_activity(
        db, entity_type="workflow", entity_id=workflow.id,
        actor=user["sub"], action="updated",
        new_value=update_data,
        project_id=workflow.project_id,
    )
    return workflow


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("admin")),
):
    """删除工作流"""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    await log_activity(
        db, entity_type="workflow", entity_id=workflow.id,
        actor=user["sub"], action="deleted",
        old_value={"name": workflow.name},
        project_id=workflow.project_id,
    )
    await db.delete(workflow)
    await db.commit()
    return None


# ── Workflow Steps ────────────────────────────────

@router.post("/{workflow_id}/steps", response_model=WorkflowStepRead, status_code=201)
async def add_workflow_step(
    workflow_id: int,
    data: WorkflowStepCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("admin", "agent")),
):
    """添加工作流步骤"""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Workflow not found")

    step = WorkflowStep(
        workflow_id=workflow_id,
        step_type=data.step_type,
        name=data.name,
        config=data.config,
        sort_order=data.sort_order,
        timeout_seconds=data.timeout_seconds,
        on_failure=data.on_failure,
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


@router.delete("/{workflow_id}/steps/{step_id}", status_code=204)
async def delete_workflow_step(
    workflow_id: int,
    step_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("admin")),
):
    """删除工作流步骤"""
    result = await db.execute(
        select(WorkflowStep).where(
            WorkflowStep.id == step_id,
            WorkflowStep.workflow_id == workflow_id,
        )
    )
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    await db.delete(step)
    await db.commit()
    return None


@router.post("/{workflow_id}/trigger", response_model=WorkflowRunRead, status_code=201)
async def trigger_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("admin", "agent")),
):
    """手动触发工作流"""
    from src.core.workflow_engine import WorkflowEngine
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id).options(selectinload(Workflow.steps))
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow.status != WorkflowStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Workflow is not active")

    engine = WorkflowEngine(db)
    run = await engine.trigger(workflow, triggered_by=user["sub"])
    return run


@router.post("/runs/{run_id}/resume", response_model=WorkflowRunRead)
async def resume_workflow_run(
    run_id: int,
    approved: bool = True,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("admin", "mate")),
):
    """恢复暂停的工作流执行（审批通过/拒绝）"""
    from src.core.workflow_engine import WorkflowEngine
    result = await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    if run.status != WorkflowRunStatus.WAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Workflow run is not waiting for approval")

    engine = WorkflowEngine(db)
    run = await engine.resume(run, approved=approved, approved_by=user["sub"])
    return run
