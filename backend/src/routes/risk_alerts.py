from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.core.dependencies import get_db
from src.models.risk_alert import RiskAlert, RiskAlertLevel, RiskAlertSource, RiskAlertStatus
from src.schemas.risk_alert import RiskAlertCreate, RiskAlertUpdate, RiskAlertRead, RiskAlertListResponse
from src.routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

VALID_LEVELS = {l.value for l in RiskAlertLevel}
VALID_SOURCES = {s.value for s in RiskAlertSource}
VALID_STATUSES = {s.value for s in RiskAlertStatus}


@router.post("", response_model=RiskAlertRead, status_code=201)
async def create_risk_alert(
    data: RiskAlertCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if data.level not in VALID_LEVELS:
        raise HTTPException(400, f"Invalid level. Valid: {sorted(VALID_LEVELS)}")
    if data.source not in VALID_SOURCES:
        raise HTTPException(400, f"Invalid source. Valid: {sorted(VALID_SOURCES)}")

    alert = RiskAlert(
        title=data.title,
        description=data.description,
        level=RiskAlertLevel(data.level),
        source=RiskAlertSource(data.source),
        suggested_action=data.suggested_action,
        project_id=data.project_id,
        created_by=user["sub"],
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.get("", response_model=RiskAlertListResponse)
async def list_risk_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    level: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RiskAlert)
    count_stmt = select(func.count(RiskAlert.id))

    if level:
        stmt = stmt.where(RiskAlert.level == level)
        count_stmt = count_stmt.where(RiskAlert.level == level)
    if status:
        stmt = stmt.where(RiskAlert.status == status)
        count_stmt = count_stmt.where(RiskAlert.status == status)
    if source:
        stmt = stmt.where(RiskAlert.source == source)
        count_stmt = count_stmt.where(RiskAlert.source == source)
    if project_id:
        stmt = stmt.where(RiskAlert.project_id == project_id)
        count_stmt = count_stmt.where(RiskAlert.project_id == project_id)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(RiskAlert.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return RiskAlertListResponse(total=total, items=items)


@router.get("/{alert_id}", response_model=RiskAlertRead)
async def get_risk_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
):
    alert = await db.get(RiskAlert, alert_id)
    if not alert:
        raise HTTPException(404, "Risk alert not found")
    return alert


@router.put("/{alert_id}", response_model=RiskAlertRead)
async def update_risk_alert(
    alert_id: int,
    data: RiskAlertUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    alert = await db.get(RiskAlert, alert_id)
    if not alert:
        raise HTTPException(404, "Risk alert not found")

    update_data = data.model_dump(exclude_unset=True)
    if "level" in update_data and update_data["level"] not in VALID_LEVELS:
        raise HTTPException(400, f"Invalid level. Valid: {sorted(VALID_LEVELS)}")
    if "status" in update_data and update_data["status"] not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Valid: {sorted(VALID_STATUSES)}")

    for key, value in update_data.items():
        setattr(alert, key, value)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.post("/{alert_id}/resolve", response_model=RiskAlertRead)
async def resolve_risk_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    alert = await db.get(RiskAlert, alert_id)
    if not alert:
        raise HTTPException(404, "Risk alert not found")

    alert.status = RiskAlertStatus.RESOLVED
    alert.resolved_by = user["sub"]
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.delete("/{alert_id}", status_code=204)
async def delete_risk_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
):
    alert = await db.get(RiskAlert, alert_id)
    if not alert:
        raise HTTPException(404, "Risk alert not found")
    await db.delete(alert)
    await db.commit()
