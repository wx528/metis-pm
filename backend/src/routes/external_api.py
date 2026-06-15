"""外部 API — 供外部 Agent 通过 Bearer Token 提交产品意见和 Issue。

认证方式：在 .env 中配置 API_TOKENS_JSON，外部 Agent 使用 Bearer Token 认证。
与内部 JWT 认证完全独立，仅可访问 /external/* 端点。

提交产品意见时必须指定产品名称和版本，确保信息准确可追溯。
"""

import logging
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.dependencies import get_db
from src.core.activity import log_activity
from src.core.notification import create_notification
from src.core.trigger_hub import get_trigger_hub
from src.models.feedback import Feedback, FeedbackCategory, FeedbackStatus
from src.models.issue import Issue, IssueType, IssueStatus, IssuePriority, IssueSource
from src.models.notification import NotificationType
from src.models.project import Project
from src.routes.auth import verify_api_token

logger = logging.getLogger("external_api")
router = APIRouter()


# ── 请求模型 ──────────────────────────────────────────────

class ExternalFeedbackRequest(BaseModel):
    """外部 Agent 提交产品意见"""
    product_name: str = Field(..., min_length=1, max_length=200, description="产品名称（必填）")
    product_version: str = Field(..., min_length=1, max_length=100, description="产品版本（必填，如 v1.2.3）")
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    category: str = Field(default="other", description="分类: bug/feature_request/improvement/ux/workflow/other")
    priority: str = Field(default="P2", pattern=r"^P[0-3]$")


class ExternalIssueRequest(BaseModel):
    """外部 Agent 提交 Issue"""
    product_name: str = Field(..., min_length=1, max_length=200, description="产品名称（必填）")
    product_version: str = Field(..., min_length=1, max_length=100, description="产品版本（必填，如 v1.2.3）")
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    issue_type: str = Field(default="bug", description="类型: bug/feature/task/improvement/documentation/idea")
    priority: str = Field(default="P2", pattern=r"^P[0-3]$")
    labels: Optional[str] = None


# ── 响应模型 ──────────────────────────────────────────────

class ExternalFeedbackResponse(BaseModel):
    id: int
    product_name: str
    product_version: str
    title: str
    category: str
    status: str
    priority: str
    submitted_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class ExternalIssueResponse(BaseModel):
    id: int
    product_name: Optional[str] = None
    product_version: Optional[str] = None
    title: str
    issue_type: str
    status: str
    priority: str
    source: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── 辅助函数 ──────────────────────────────────────────────

VALID_CATEGORIES = {c.value for c in FeedbackCategory}
VALID_ISSUE_TYPES = {t.value for t in IssueType}


async def _resolve_project_id(db: AsyncSession, product_name: str) -> Optional[int]:
    """根据产品名称模糊匹配项目 ID"""
    result = await db.execute(
        select(Project).where(Project.name.ilike(f"%{product_name}%")).limit(1)
    )
    project = result.scalar_one_or_none()
    return project.id if project else None


# ── 端点 ──────────────────────────────────────────────────

@router.post("/feedbacks", response_model=ExternalFeedbackResponse, status_code=201)
async def external_submit_feedback(
    data: ExternalFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    caller: dict = Depends(verify_api_token),
):
    """外部 Agent 提交产品意见。必须指定产品名称和版本。"""
    if data.category not in VALID_CATEGORIES:
        raise HTTPException(400, f"Invalid category. Valid: {sorted(VALID_CATEGORIES)}")

    # 尝试关联项目
    project_id = await _resolve_project_id(db, data.product_name)

    feedback = Feedback(
        title=data.title,
        content=data.content,
        category=FeedbackCategory(data.category),
        priority=data.priority,
        submitted_by=caller["sub"],
        submitted_by_role=caller.get("role", "external"),
        project_id=project_id,
        product_name=data.product_name,
        product_version=data.product_version,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    await log_activity(
        db, entity_type="feedback", entity_id=feedback.id,
        actor=caller["sub"], action="created_via_api",
        new_value={"title": feedback.title, "product": data.product_name, "version": data.product_version},
        project_id=project_id,
    )

    # P0/P1 通知 admin
    if data.priority in ("P0", "P1"):
        get_trigger_hub().fire_event("p0_feedback_created", str(feedback.id), {
            "feedback_id": feedback.id,
            "product": data.product_name,
            "version": data.product_version,
            "priority": data.priority,
        })
        await create_notification(
            db, recipient="admin",
            type=NotificationType.TASK_CREATED,
            title=f"[外部] {caller['sub']} 提交了 {data.priority} 产品意见",
            body=f"[{data.product_name}@{data.product_version}] {data.title}",
            entity_type="feedback", entity_id=feedback.id,
            created_by=caller["sub"],
            project_id=project_id,
        )

    logger.info("External feedback #%d created by %s for %s@%s",
                feedback.id, caller["sub"], data.product_name, data.product_version)
    # 显式返回 dict（避免 ORM 对象在 Session 关闭后被访问时触发 lazy load）
    return ExternalFeedbackResponse(
        id=feedback.id,
        product_name=feedback.product_name,
        product_version=feedback.product_version,
        title=feedback.title,
        category=str(feedback.category),
        status=str(feedback.status),
        priority=feedback.priority,
        submitted_by=feedback.submitted_by,
        created_at=feedback.created_at,
    )


@router.post("/issues", response_model=ExternalIssueResponse, status_code=201)
async def external_submit_issue(
    data: ExternalIssueRequest,
    db: AsyncSession = Depends(get_db),
    caller: dict = Depends(verify_api_token),
):
    """外部 Agent 提交 Issue。必须指定产品名称和版本。"""
    if data.issue_type not in VALID_ISSUE_TYPES:
        raise HTTPException(400, f"Invalid issue_type. Valid: {sorted(VALID_ISSUE_TYPES)}")

    # 尝试关联项目
    project_id = await _resolve_project_id(db, data.product_name)

    # 将产品信息写入 description
    product_header = f"**产品**: {data.product_name}  \n**版本**: {data.product_version}  \n\n---\n\n"
    full_description = product_header + (data.description or "")

    issue = Issue(
        project_id=project_id,
        title=data.title,
        description=full_description,
        issue_type=IssueType(data.issue_type),
        status=IssueStatus.OPEN,
        priority=IssuePriority(data.priority),
        source=IssueSource.AI_AGENT,
        created_by=caller["sub"],
        labels=data.labels,
    )
    db.add(issue)
    await db.commit()
    await db.refresh(issue)

    await log_activity(
        db, entity_type="issue", entity_id=issue.id,
        actor=caller["sub"], action="created_via_api",
        new_value={"title": issue.title, "product": data.product_name, "version": data.product_version},
        project_id=project_id,
    )

    # P0/P1 通知 admin
    if data.priority in ("P0", "P1"):
        get_trigger_hub().fire_event("p0_issue_created", str(issue.id), {
            "issue_id": issue.id,
            "product": data.product_name,
            "version": data.product_version,
            "priority": data.priority,
        })
        await create_notification(
            db, recipient="admin",
            type=NotificationType.TASK_CREATED,
            title=f"[外部] {caller['sub']} 提交了 {data.priority} Issue",
            body=f"[{data.product_name}@{data.product_version}] {data.title}",
            entity_type="issue", entity_id=issue.id,
            created_by=caller["sub"],
            project_id=project_id,
        )

    logger.info("External issue #%d created by %s for %s@%s",
                issue.id, caller["sub"], data.product_name, data.product_version)

    # 返回显式 dict（不挂载临时属性到 ORM 对象，避免污染 Session）
    return ExternalIssueResponse(
        id=issue.id,
        product_name=data.product_name,
        product_version=data.product_version,
        title=issue.title,
        issue_type=str(issue.issue_type),
        status=str(issue.status),
        priority=str(issue.priority),
        source=str(issue.source),
        created_by=issue.created_by,
        created_at=issue.created_at,
    )


@router.get("/products/search")
async def search_products(
    q: str = "",
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    caller: dict = Depends(verify_api_token),
):
    """搜索产品/项目名称，供外部 Agent 查询正确的产品名称"""
    query = select(Project.id, Project.name, Project.slug)
    if q:
        query = query.where(Project.name.ilike(f"%{q}%"))
    query = query.limit(limit)
    result = await db.execute(query)
    return [{"id": row[0], "name": row[1], "slug": row[2]} for row in result.all()]
