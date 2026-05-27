from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.core.dependencies import get_db
from src.core.activity import log_activity
from src.models.project_registration import ProjectRegistration, RegistrationStatus
from src.schemas.project_registration import (
    ProjectRegistrationCreate, ProjectRegistrationUpdate,
    ProjectRegistrationRead, ProjectRegistrationListResponse,
)
from src.routes.auth import get_current_user, require_role

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=ProjectRegistrationListResponse)
async def list_registrations(
    status: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    tech_stack: Optional[str] = Query(None),
    registered_by: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """列出项目登记"""
    query = select(ProjectRegistration)
    count_query = select(func.count(ProjectRegistration.id))

    if status:
        query = query.where(ProjectRegistration.status == status)
        count_query = count_query.where(ProjectRegistration.status == status)
    if language:
        query = query.where(ProjectRegistration.language.ilike(f"%{language}%"))
        count_query = count_query.where(ProjectRegistration.language.ilike(f"%{language}%"))
    if tech_stack:
        query = query.where(ProjectRegistration.tech_stack.ilike(f"%{tech_stack}%"))
        count_query = count_query.where(ProjectRegistration.tech_stack.ilike(f"%{tech_stack}%"))
    if registered_by:
        query = query.where(ProjectRegistration.registered_by == registered_by)
        count_query = count_query.where(ProjectRegistration.registered_by == registered_by)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(ProjectRegistration.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return ProjectRegistrationListResponse(total=total, items=items)


@router.post("", response_model=ProjectRegistrationRead, status_code=201)
async def create_registration(
    data: ProjectRegistrationCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """登记项目"""
    # 检查路径是否已登记
    existing = await db.execute(
        select(ProjectRegistration).where(ProjectRegistration.path == data.path)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Path '{data.path}' already registered")

    reg = ProjectRegistration(**data.model_dump())
    reg.registered_by = user["sub"]
    db.add(reg)
    await db.commit()
    await db.refresh(reg)

    await log_activity(
        db, entity_type="project_registration", entity_id=reg.id,
        actor=user["sub"], action="registered",
        new_value={"name": reg.name, "path": reg.path},
    )
    return reg


@router.get("/{reg_id}", response_model=ProjectRegistrationRead)
async def get_registration(reg_id: int, db: AsyncSession = Depends(get_db)):
    """获取项目登记详情"""
    result = await db.execute(select(ProjectRegistration).where(ProjectRegistration.id == reg_id))
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Project registration not found")
    return reg


@router.put("/{reg_id}", response_model=ProjectRegistrationRead)
async def update_registration(
    reg_id: int,
    data: ProjectRegistrationUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新项目登记"""
    result = await db.execute(select(ProjectRegistration).where(ProjectRegistration.id == reg_id))
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Project registration not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(reg, key, value)
    await db.commit()
    await db.refresh(reg)

    await log_activity(
        db, entity_type="project_registration", entity_id=reg.id,
        actor=user["sub"], action="updated",
        new_value=update_data,
    )
    return reg


@router.delete("/{reg_id}", status_code=204)
async def delete_registration(
    reg_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除项目登记"""
    result = await db.execute(select(ProjectRegistration).where(ProjectRegistration.id == reg_id))
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Project registration not found")

    await log_activity(
        db, entity_type="project_registration", entity_id=reg.id,
        actor=user["sub"], action="deleted",
        old_value={"name": reg.name, "path": reg.path},
    )
    await db.delete(reg)
    await db.commit()
    return None
