from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from src.core.dependencies import get_db
from src.models.feedback import Feedback, FeedbackCategory, FeedbackStatus
from src.schemas.feedback import (
    FeedbackCreate, FeedbackUpdate, FeedbackRead, FeedbackListResponse,
)
from src.routes.auth import get_current_user, require_role

router = APIRouter()

# 有效优先级
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
# 有效分类/状态（从枚举派生，避免硬编码）
VALID_CATEGORIES = {c.value for c in FeedbackCategory}
VALID_STATUSES = {s.value for s in FeedbackStatus}


# ═══════════════════════════════════════════════════════
#  Agent 提交意见（所有角色可用）
# ═══════════════════════════════════════════════════════

@router.post("", response_model=FeedbackRead, status_code=201)
async def submit_feedback(
    data: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Agent 提交意见/反馈"""
    # 验证 category
    if data.category not in VALID_CATEGORIES:
        raise HTTPException(400, f"Invalid category. Valid: {sorted(VALID_CATEGORIES)}")
    # 验证 priority
    if data.priority not in VALID_PRIORITIES:
        raise HTTPException(400, f"Invalid priority. Valid: {sorted(VALID_PRIORITIES)}")

    feedback = Feedback(
        title=data.title,
        content=data.content,
        category=FeedbackCategory(data.category),
        priority=data.priority,
        submitted_by=user["sub"],
        submitted_by_role=user.get("role"),
        project_id=data.project_id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback


# ═══════════════════════════════════════════════════════
#  列表查询（所有角色可看自己的，admin 可看全部）
# ═══════════════════════════════════════════════════════

@router.get("", response_model=FeedbackListResponse)
async def list_feedbacks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    submitted_by: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出反馈意见。Agent 只能看自己的，admin 可看全部"""
    query = select(Feedback)
    count_query = select(func.count(Feedback.id))

    # 非 admin 只能看自己提交的
    if user.get("role") != "admin":
        query = query.where(Feedback.submitted_by == user["sub"])
        count_query = count_query.where(Feedback.submitted_by == user["sub"])
    elif submitted_by:
        query = query.where(Feedback.submitted_by == submitted_by)
        count_query = count_query.where(Feedback.submitted_by == submitted_by)

    if category:
        query = query.where(Feedback.category == category)
        count_query = count_query.where(Feedback.category == category)
    if status:
        query = query.where(Feedback.status == status)
        count_query = count_query.where(Feedback.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(Feedback.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return FeedbackListResponse(total=total, items=items)


# ═══════════════════════════════════════════════════════
#  统计（admin）— 必须在 /{feedback_id} 之前注册
# ═══════════════════════════════════════════════════════

@router.get("/stats/summary")
async def feedback_stats(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("admin")),
):
    """反馈统计摘要（仅 admin）"""
    # 按状态统计
    status_counts = {}
    for status in FeedbackStatus:
        result = await db.execute(
            select(func.count(Feedback.id)).where(Feedback.status == status)
        )
        status_counts[status.value] = result.scalar() or 0

    # 按分类统计
    category_counts = {}
    for cat in FeedbackCategory:
        result = await db.execute(
            select(func.count(Feedback.id)).where(Feedback.category == cat)
        )
        category_counts[cat.value] = result.scalar() or 0

    # 按提交者统计
    result = await db.execute(
        select(Feedback.submitted_by, func.count(Feedback.id))
        .group_by(Feedback.submitted_by)
        .order_by(desc(func.count(Feedback.id)))
    )
    by_submitter = [{"submitter": row[0], "count": row[1]} for row in result.all()]

    return {
        "total": sum(status_counts.values()),
        "by_status": status_counts,
        "by_category": category_counts,
        "by_submitter": by_submitter,
    }


# ═══════════════════════════════════════════════════════
#  详情
# ═══════════════════════════════════════════════════════

@router.get("/{feedback_id}", response_model=FeedbackRead)
async def get_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取反馈详情"""
    feedback = await db.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(404, "Feedback not found")
    # 非 admin 只能看自己的
    if user.get("role") != "admin" and feedback.submitted_by != user["sub"]:
        raise HTTPException(403, "No permission")
    return feedback


# ═══════════════════════════════════════════════════════
#  更新（admin 可改状态/回复，Agent 可改自己的内容）
# ═══════════════════════════════════════════════════════

@router.put("/{feedback_id}", response_model=FeedbackRead)
async def update_feedback(
    feedback_id: int,
    data: FeedbackUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新反馈。Admin 可修改状态和回复，Agent 可修改自己的标题/内容"""
    feedback = await db.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(404, "Feedback not found")

    is_admin = user.get("role") == "admin"
    is_owner = feedback.submitted_by == user["sub"]

    if not is_admin and not is_owner:
        raise HTTPException(403, "No permission")

    update_data = data.model_dump(exclude_unset=True)

    if is_admin:
        # Admin 可以修改所有字段
        if "admin_reply" in update_data:
            reply_content = update_data["admin_reply"]
            if reply_content is not None and reply_content != "":
                feedback.admin_reply = reply_content
                feedback.replied_by = user["sub"]
                feedback.replied_at = datetime.now(timezone.utc)
            elif reply_content == "":
                # 空字符串清除回复
                feedback.admin_reply = None
                feedback.replied_by = None
                feedback.replied_at = None
        if "status" in update_data:
            if update_data["status"] not in VALID_STATUSES:
                raise HTTPException(400, f"Invalid status. Valid: {sorted(VALID_STATUSES)}")
            feedback.status = FeedbackStatus(update_data["status"])
        if "priority" in update_data:
            if update_data["priority"] not in VALID_PRIORITIES:
                raise HTTPException(400, f"Invalid priority. Valid: {sorted(VALID_PRIORITIES)}")
            feedback.priority = update_data["priority"]
        if "category" in update_data:
            if update_data["category"] not in VALID_CATEGORIES:
                raise HTTPException(400, f"Invalid category. Valid: {sorted(VALID_CATEGORIES)}")
            feedback.category = FeedbackCategory(update_data["category"])
    else:
        # Agent 只能改标题/内容/分类
        for field in ("title", "content", "category"):
            if field in update_data:
                if field == "category":
                    if update_data[field] not in VALID_CATEGORIES:
                        raise HTTPException(400, f"Invalid category. Valid: {sorted(VALID_CATEGORIES)}")
                    feedback.category = FeedbackCategory(update_data[field])
                else:
                    setattr(feedback, field, update_data[field])

    await db.commit()
    await db.refresh(feedback)
    return feedback


# ═══════════════════════════════════════════════════════
#  删除（仅 admin）
# ═══════════════════════════════════════════════════════

@router.delete("/{feedback_id}", status_code=204)
async def delete_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("admin")),
):
    """删除反馈（仅 admin）"""
    feedback = await db.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(404, "Feedback not found")
    await db.delete(feedback)
    await db.commit()
