import logging
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("copilot.trigger")


class TriggerType(Enum):
    SCHEDULED = "scheduled"
    EVENT = "event"
    REQUEST = "request"
    STATE = "state"
    MESSAGE = "message"


@dataclass
class TriggerContext:
    trigger_type: TriggerType
    source: str
    payload: dict = field(default_factory=dict)
    priority: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TriggerHub:
    def fire(self, context: TriggerContext) -> bool:
        logger.debug(f"Trigger fired: {context.trigger_type.value}:{context.source}")
        return True

    def fire_scheduled(self, job_name: str, payload: Optional[dict] = None) -> bool:
        return self.fire(TriggerContext(TriggerType.SCHEDULED, job_name, payload or {}))

    def fire_event(self, event_type: str, entity_id: str, payload: Optional[dict] = None) -> bool:
        priority = 7 if event_type in ("task_overdue", "risk_critical") else 4
        return self.fire(TriggerContext(TriggerType.EVENT, f"{event_type}:{entity_id}", payload or {}, priority))

    def fire_request(self, source: str, query: str, user_id: Optional[str] = None) -> bool:
        return self.fire(TriggerContext(TriggerType.REQUEST, source, {"query": query, "user_id": user_id}, 6))

    def fire_state(self, metric_name: str, current_value: float, threshold: float) -> bool:
        priority = 9 if current_value > threshold * 1.5 else 7
        return self.fire(TriggerContext(TriggerType.STATE, metric_name, {"value": current_value, "threshold": threshold}, priority))

    def fire_message(self, message_id: str, content: str, project_id: Optional[str] = None) -> bool:
        keywords = ["阻塞", "延期", "风险", "紧急", "bug", "故障"]
        matched = [k for k in keywords if k in content.lower()]
        if not matched:
            return False
        priority = 6 if "紧急" in matched or "故障" in matched else 3
        return self.fire(TriggerContext(TriggerType.MESSAGE, f"message:{message_id}", {"content": content, "keywords": matched, "project_id": project_id}, priority))


class NoOpTriggerHub(TriggerHub):
    def fire(self, context: TriggerContext) -> bool:
        return False

    def fire_scheduled(self, job_name: str, payload: Optional[dict] = None) -> bool:
        return False

    def fire_event(self, event_type: str, entity_id: str, payload: Optional[dict] = None) -> bool:
        return False

    def fire_request(self, source: str, query: str, user_id: Optional[str] = None) -> bool:
        return False

    def fire_state(self, metric_name: str, current_value: float, threshold: float) -> bool:
        return False

    def fire_message(self, message_id: str, content: str, project_id: Optional[str] = None) -> bool:
        return False


_trigger_hub: Optional[TriggerHub] = None


def get_trigger_hub() -> TriggerHub:
    global _trigger_hub
    if _trigger_hub is None:
        _trigger_hub = NoOpTriggerHub()
    return _trigger_hub


def set_trigger_hub(hub: TriggerHub):
    global _trigger_hub
    _trigger_hub = hub
