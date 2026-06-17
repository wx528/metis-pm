from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.core.dependencies import get_db
from src.models.project import Project, ProjectStatus
from src.models.issue import Issue, IssueStatus
from src.models.plan import Plan
from src.schemas.project import ProjectCreate, ProjectUpdate, ProjectRead, ProjectReadWithStats
from src.routes.auth import get_current_user, require_role

router = APIRouter(dependencies=[Depends(get_current_user)])


async def _get_project_by_slug(db: AsyncSession, slug: str) -> Project:
    result = await db.execute(select(Project).where(Project.slug == slug))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{slug}' not found")
    return project


@router.get("", response_model=list[ProjectReadWithStats])
async def list_projects(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Project)
    if status:
        query = query.where(Project.status == status)
    query = query.order_by(Project.created_at.desc())
    result = await db.execute(query)
    projects = result.scalars().all()

    response = []
    for p in projects:
        issue_count = (await db.execute(
            select(func.count(Issue.id)).where(Issue.project_id == p.id)
        )).scalar() or 0
        open_issue_count = (await db.execute(
            select(func.count(Issue.id)).where(
                Issue.project_id == p.id,
                Issue.status.in_([IssueStatus.OPEN, IssueStatus.IN_PROGRESS])
            )
        )).scalar() or 0
        plan_count = (await db.execute(
            select(func.count(Plan.id)).where(Plan.project_id == p.id)
        )).scalar() or 0
        response.append(ProjectReadWithStats(
            id=p.id, name=p.name, slug=p.slug, description=p.description,
            status=p.status, created_at=p.created_at, updated_at=p.updated_at,
            issue_count=issue_count, open_issue_count=open_issue_count, plan_count=plan_count,
        ))
    return response


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "agent"))):
    existing = await db.execute(select(Project).where(Project.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Project slug '{data.slug}' already exists")
    project = Project(**data.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{slug}", response_model=ProjectReadWithStats)
async def get_project(slug: str, db: AsyncSession = Depends(get_db)):
    project = await _get_project_by_slug(db, slug)
    issue_count = (await db.execute(select(func.count(Issue.id)).where(Issue.project_id == project.id))).scalar() or 0
    open_issue_count = (await db.execute(select(func.count(Issue.id)).where(Issue.project_id == project.id, Issue.status.in_([IssueStatus.OPEN, IssueStatus.IN_PROGRESS])))).scalar() or 0
    plan_count = (await db.execute(select(func.count(Plan.id)).where(Plan.project_id == project.id))).scalar() or 0
    return ProjectReadWithStats(
        id=project.id, name=project.name, slug=project.slug, description=project.description,
        status=project.status, created_at=project.created_at, updated_at=project.updated_at,
        issue_count=issue_count, open_issue_count=open_issue_count, plan_count=plan_count,
    )


@router.put("/{slug}", response_model=ProjectRead)
async def update_project(slug: str, data: ProjectUpdate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "agent"))):
    project = await _get_project_by_slug(db, slug)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{slug}", status_code=204)
async def delete_project(slug: str, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin"))):
    project = await _get_project_by_slug(db, slug)
    issue_count = (await db.execute(select(func.count(Issue.id)).where(Issue.project_id == project.id))).scalar() or 0
    plan_count = (await db.execute(select(func.count(Plan.id)).where(Plan.project_id == project.id))).scalar() or 0
    if issue_count or plan_count:
        raise HTTPException(status_code=409, detail="Cannot delete project with existing issues or plans")
    await db.delete(project)
    await db.commit()
    return None
