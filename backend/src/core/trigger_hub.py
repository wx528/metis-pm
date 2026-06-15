import asyncio
import logging
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Callable

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
    """活跃触发中心：将高优先级触发事件转发给 Copilot 和/或 A2A Agent 处理。"""

    def __init__(self, copilot_ask_fn: Optional[Callable[[str], str]] = None, a2a_enabled: bool = False):
        self._copilot_ask_fn = copilot_ask_fn
        self._a2a_enabled = a2a_enabled

    def set_copilot_ask_fn(self, fn: Callable[[str], str]):
        self._copilot_ask_fn = fn

    def enable_a2a(self, enabled: bool = True):
        self._a2a_enabled = enabled

    def _dispatch_to_copilot(self, context: TriggerContext, prompt: str) -> bool:
        if not self._copilot_ask_fn:
            logger.debug("Trigger fired but no copilot_ask_fn configured: %s:%s",
                         context.trigger_type.value, context.source)
            return False
        try:
            if asyncio.iscoroutinefunction(self._copilot_ask_fn):
                # 异步函数：在后台线程中运行，避免阻塞当前调用
                import threading
                def _run():
                    asyncio.run(self._copilot_ask_fn(prompt))
                t = threading.Thread(target=_run, daemon=True)
                t.start()
            else:
                self._copilot_ask_fn(prompt)
            logger.info("Trigger dispatched to Copilot: %s:%s",
                        context.trigger_type.value, context.source)
            return True
        except Exception as e:
            logger.error("Trigger dispatch failed: %s", e)
            return False

    def _dispatch_to_a2a(self, context: TriggerContext, description: str, capability: str) -> bool:
        """通过 A2A 协议委派任务给外部 Agent"""
        if not self._a2a_enabled:
            return False
        try:
            from src.a2a.client import get_a2a_client
            client = get_a2a_client()
            coro = client.delegate_to_capability(capability, description, context.payload)
            # 尝试在已有事件循环中调度，否则在新线程中运行
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro)
            except RuntimeError:
                # 没有运行中的事件循环，在新线程中运行
                import threading
                def _run():
                    asyncio.run(coro)
                t = threading.Thread(target=_run, daemon=True)
                t.start()
            logger.info("Trigger dispatched to A2A agent: %s:%s (capability=%s)",
                        context.trigger_type.value, context.source, capability)
            return True
        except Exception as e:
            logger.error("A2A dispatch failed: %s", e)
            return False

    def fire(self, context: TriggerContext) -> bool:
        logger.debug("Trigger fired: %s:%s", context.trigger_type.value, context.source)
        return True

    def fire_scheduled(self, job_name: str, payload: Optional[dict] = None) -> bool:
        ctx = TriggerContext(TriggerType.SCHEDULED, job_name, payload or {}, priority=5)
        self.fire(ctx)
        prompt = f"[定时触发] {job_name}，请检查相关项目状态。"
        copilot_ok = self._dispatch_to_copilot(ctx, prompt)
        a2a_ok = self._dispatch_to_a2a(ctx, prompt, "project-overview")
        return copilot_ok or a2a_ok

    def fire_event(self, event_type: str, entity_id: str, payload: Optional[dict] = None) -> bool:
        priority = 7 if event_type in ("task_overdue", "risk_critical", "p0_issue_created") else 4
        ctx = TriggerContext(TriggerType.EVENT, f"{event_type}:{entity_id}", payload or {}, priority)
        self.fire(ctx)
        if priority >= 5:
            prompt = f"[事件触发] {event_type} (ID: {entity_id})，请评估是否需要采取行动。"
            copilot_ok = self._dispatch_to_copilot(ctx, prompt)
            # 映射事件类型到 A2A 能力标签
            capability_map = {
                "p0_issue_created": "issue-handling",
                "task_overdue": "issue-handling",
                "risk_critical": "risk-analysis",
            }
            a2a_capability = capability_map.get(event_type)
            a2a_ok = self._dispatch_to_a2a(ctx, prompt, a2a_capability) if a2a_capability else False
            return copilot_ok or a2a_ok
        return True

    def fire_request(self, source: str, query: str, user_id: Optional[str] = None) -> bool:
        ctx = TriggerContext(TriggerType.REQUEST, source, {"query": query, "user_id": user_id}, 6)
        self.fire(ctx)
        prompt = f"[用户请求 from {source}] {query}"
        return self._dispatch_to_copilot(ctx, prompt)

    def fire_state(self, metric_name: str, current_value: float, threshold: float) -> bool:
        priority = 9 if current_value > threshold * 1.5 else 7
        ctx = TriggerContext(TriggerType.STATE, metric_name, {"value": current_value, "threshold": threshold}, priority)
        self.fire(ctx)
        prompt = f"[状态告警] {metric_name} 当前值 {current_value} 超过阈值 {threshold}，请检查。"
        return self._dispatch_to_copilot(ctx, prompt)

    def fire_message(self, message_id: str, content: str, project_id: Optional[str] = None) -> bool:
        keywords = ["阻塞", "延期", "风险", "紧急", "bug", "故障"]
        matched = [k for k in keywords if k in content.lower()]
        if not matched:
            return False
        priority = 6 if "紧急" in matched or "故障" in matched else 3
        ctx = TriggerContext(TriggerType.MESSAGE, f"message:{message_id}", {"content": content, "keywords": matched, "project_id": project_id}, priority)
        self.fire(ctx)
        if priority >= 5:
            prompt = f"[消息触发] 检测到关键词 {matched}，内容：{content[:200]}"
            return self._dispatch_to_copilot(ctx, prompt)
        return True


class NoOpTriggerHub(TriggerHub):
    """降级触发中心：AI 禁用时所有触发静默返回 False。"""

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
