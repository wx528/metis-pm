import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base, EnumColumn


class RiskAlertLevel(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskAlertSource(str, enum.Enum):
    MANUAL = "manual"
    COPILOT = "copilot"
    SYSTEM = "system"


class RiskAlertStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class RiskAlert(Base):
    __tablename__ = "risk_alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    level = Column(EnumColumn(RiskAlertLevel), default=RiskAlertLevel.MEDIUM, nullable=False)
    source = Column(EnumColumn(RiskAlertSource), default=RiskAlertSource.MANUAL, nullable=False)
    status = Column(EnumColumn(RiskAlertStatus), default=RiskAlertStatus.OPEN, nullable=False)
    suggested_action = Column(Text, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", foreign_keys=[project_id])
