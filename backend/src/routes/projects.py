from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.core.dependencies import get_db
from src.core.activity import log_activity
from src.models.project import Project, ProjectStatus
from src.models.issue import Issue, IssueStatus
from src.models.plan import Plan
from src.models.milestone import Milestone
from src.models.server import Server
from src.schemas.project import ProjectCreate, ProjectUpdate, ProjectRead, ProjectReadWithStats
from src.routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


async def _get_project_by_slug(db: AsyncSession, slug: str) -> Project:
    """通过 slug 获取项目，不存在则 404"""
    result = await db.execute(select(Project).where(Project.slug == slug))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{slug}' not found")
    return project


async def _get_project_stats(db: AsyncSession, project_id: int) -> dict:
    """获取项目统计数据（单次查询优化）"""
    # 使用条件聚合，一次查询获取所有统计
    stats_result = await db.execute(
        select(
            func.count(Issue.id).label("issue_count"),
            func.count(Issue.id).filter(
                Issue.status.in_([IssueStatus.OPEN, IssueStatus.IN_PROGRESS, IssueStatus.REVIEW])
            ).label("open_issue_count"),
        ).where(Issue.project_id == project_id)
    )
    issue_stats = stats_result.one()

    plan_count = (await db.execute(
        select(func.count(Plan.id)).where(Plan.project_id == project_id)
    )).scalar() or 0

    milestone_count = (await db.execute(
        select(func.count(Milestone.id)).where(Milestone.project_id == project_id)
    )).scalar() or 0

    server_count = (await db.execute(
        select(func.count(Server.id)).where(Server.project_id == project_id)
    )).scalar() or 0

    return {
        "issue_count": issue_stats.issue_count or 0,
        "open_issue_count": issue_stats.open_issue_count or 0,
        "plan_count": plan_count,
        "milestone_count": milestone_count,
        "server_count": server_count,
    }


@router.get("", response_model=list[ProjectReadWithStats])
async def list_projects(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """列出所有项目（含统计）"""
    query = select(Project)
    if status:
        query = query.where(Project.status == status)
    query = query.order_by(Project.created_at.desc())
    result = await db.execute(query)
    projects = result.scalars().all()

    response = []
    for p in projects:
        stats = await _get_project_stats(db, p.id)
        response.append(ProjectReadWithStats(
            id=p.id,
            name=p.name,
            slug=p.slug,
            description=p.description,
            repo_url=p.repo_url,
            status=p.status,
            owner=p.owner,
            default_milestone_id=p.default_milestone_id,
            created_at=p.created_at,
            updated_at=p.updated_at,
            **stats,
        ))
    return response


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    # 检查 slug 唯一
    existing = await db.execute(select(Project).where(Project.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Project slug '{data.slug}' already exists")

    project = Project(**data.model_dump())
    if not project.owner:
        project.owner = user["sub"]
    db.add(project)
    await db.commit()
    await db.refresh(project)

    await log_activity(
        db, entity_type="project", entity_id=project.id,
        actor=user["sub"], action="created",
        new_value={"name": project.name, "slug": project.slug},
    )
    return project


@router.get("/{slug}", response_model=ProjectReadWithStats)
async def get_project(slug: str, db: AsyncSession = Depends(get_db)):
    project = await _get_project_by_slug(db, slug)
    stats = await _get_project_stats(db, project.id)

    return ProjectReadWithStats(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        repo_url=project.repo_url,
        status=project.status,
        owner=project.owner,
        default_milestone_id=project.default_milestone_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        **stats,
    )


@router.put("/{slug}", response_model=ProjectRead)
async def update_project(slug: str, data: ProjectUpdate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    project = await _get_project_by_slug(db, slug)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)

    await log_activity(
        db, entity_type="project", entity_id=project.id,
        actor=user["sub"], action="updated",
        new_value=update_data,
    )
    return project


@router.delete("/{slug}", status_code=204)
async def delete_project(slug: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    project = await _get_project_by_slug(db, slug)

    # 检查关联数据，有数据时拒绝删除
    issue_count = (await db.execute(select(func.count(Issue.id)).where(Issue.project_id == project.id))).scalar() or 0
    plan_count = (await db.execute(select(func.count(Plan.id)).where(Plan.project_id == project.id))).scalar() or 0
    milestone_count = (await db.execute(select(func.count(Milestone.id)).where(Milestone.project_id == project.id))).scalar() or 0
    server_count = (await db.execute(select(func.count(Server.id)).where(Server.project_id == project.id))).scalar() or 0
    if issue_count or plan_count or milestone_count or server_count:
        details = []
        if issue_count: details.append(f"{issue_count} issues")
        if plan_count: details.append(f"{plan_count} plans")
        if milestone_count: details.append(f"{milestone_count} milestones")
        if server_count: details.append(f"{server_count} servers")
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete project with existing data: {', '.join(details)}. Please move or delete them first.",
        )

    await log_activity(
        db, entity_type="project", entity_id=project.id,
        actor=user["sub"], action="deleted",
        old_value={"name": project.name, "slug": project.slug},
    )
    await db.delete(project)
    await db.commit()
    return None
