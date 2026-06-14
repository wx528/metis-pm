from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db
from src.routes.auth import get_current_user
from src.models.project import Project
from src.models.milestone import Milestone
from src.models.issue import Issue
from src.schemas.graph import GraphNode, GraphEdge, GraphResponse

router = APIRouter(dependencies=[Depends(get_current_user)])

COLOR_PALETTE = [
    "#ff6b6b", "#51cf66", "#4a9eff", "#ffd43b",
    "#cc5de8", "#20c997", "#ff922b", "#845ef7"
]

PRIORITY_SIZE = {
    "P0": 20,
    "P1": 16,
    "P2": 12,
    "P3": 8,
}

STATUS_OPACITY = {
    "open": 0.9,
    "in_progress": 0.9,
    "review": 0.85,
    "deferred": 0.7,
    "closed": 0.4,
    "cancelled": 0.4,
}


def assign_label_colors(labels: list[str]) -> dict[str, str]:
    sorted_labels = sorted(set(labels))
    return {
        label: COLOR_PALETTE[i % len(COLOR_PALETTE)]
        for i, label in enumerate(sorted_labels)
    }


@router.get("", response_model=GraphResponse)
async def get_project_graph(
    slug: str,
    status: Optional[str] = Query(None, description="逗号分隔的状态筛选"),
    issue_type: Optional[str] = Query(None, description="逗号分隔的类型筛选"),
    labels: Optional[str] = Query(None, description="逗号分隔的标签筛选"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Project).where(Project.slug == slug)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stmt = select(Milestone).where(Milestone.project_id == project.id)
    result = await db.execute(stmt)
    milestones = result.scalars().all()

    stmt = select(Issue).where(Issue.project_id == project.id)

    if status:
        status_list = [s.strip() for s in status.split(",")]
        stmt = stmt.where(Issue.status.in_(status_list))

    if issue_type:
        type_list = [t.strip() for t in issue_type.split(",")]
        stmt = stmt.where(Issue.issue_type.in_(type_list))

    if labels:
        label_list = [l.strip() for l in labels.split(",")]
        for label in label_list:
            stmt = stmt.where(Issue.labels.contains(label))

    result = await db.execute(stmt)
    issues = result.scalars().all()

    all_labels = []
    for issue in issues:
        if issue.labels:
            all_labels.extend([l.strip() for l in issue.labels.split(",") if l.strip()])
    label_colors = assign_label_colors(all_labels)

    nodes: list[GraphNode] = []

    for ms in milestones:
        nodes.append(GraphNode(
            id=f"ms-{ms.id}",
            type="milestone",
            title=ms.title or f"Milestone {ms.id}",
            size=30,
            color="#4a9eff",
            opacity=0.3,
        ))

    for issue in issues:
        issue_labels = []
        if issue.labels:
            issue_labels = [l.strip() for l in issue.labels.split(",") if l.strip()]

        color = label_colors.get(issue_labels[0], "#888888") if issue_labels else "#888888"
        size = PRIORITY_SIZE.get(str(issue.priority), 12)
        opacity = STATUS_OPACITY.get(str(issue.status), 0.9)

        nodes.append(GraphNode(
            id=f"issue-{issue.id}",
            type="issue",
            title=issue.title,
            issue_id=issue.id,
            priority=str(issue.priority),
            status=str(issue.status),
            issue_type=str(issue.issue_type),
            labels=issue_labels,
            milestone_id=issue.milestone_id,
            parent_id=issue.parent_id,
            size=size,
            color=color,
            opacity=opacity,
        ))

    edges: list[GraphEdge] = []
    issue_id_set = {issue.id for issue in issues}
    for issue in issues:
        if issue.parent_id and issue.parent_id in issue_id_set:
            edges.append(GraphEdge(source=f"issue-{issue.id}", target=f"issue-{issue.parent_id}"))

    return GraphResponse(nodes=nodes, edges=edges, labels=label_colors)
