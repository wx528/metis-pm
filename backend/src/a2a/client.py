"""
A2A Client：PM 系统通过 A2A 协议主动向外部 Agent 委派任务

核心流程：
  1. TriggerHub 触发高优先级事件
  2. A2AClient 查找能处理该事件的外部 Agent
  3. 通过 A2A 协议发送任务请求
  4. 跟踪任务状态，收集结果

A2A 协议核心概念 (v1.0):
  - Task: 一次委派的工作单元，有生命周期 (submitted → working → completed/failed)
  - Message: Agent 之间的通信单元
  - Agent Card: Agent 的能力描述（/.well-known/agent-card.json）

传输方式:
  - HTTP POST /tasks (创建任务)
  - GET /tasks/{id} (查询状态)
  - SSE /tasks/{id}/stream (流式进度)
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx

from src.a2a.registry import AgentCard, AgentRegistry, get_registry

logger = logging.getLogger("a2a.client")

# A2A 任务状态
TASK_SUBMITTED = "submitted"
TASK_WORKING = "working"
TASK_COMPLETED = "completed"
TASK_FAILED = "failed"
TASK_CANCELLED = "cancelled"


class A2ATask:
    """A2A 任务"""

    def __init__(self, task_id: str, agent_id: str, description: str, payload: dict):
        self.task_id = task_id
        self.agent_id = agent_id
        self.description = description
        self.payload = payload
        self.status = TASK_SUBMITTED
        self.result: Optional[str] = None
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "description": self.description,
            "status": self.status,
            "result": self.result,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class A2AClient:
    """
    A2A 客户端：向外部 Agent 发送任务

    使用方式:
      client = A2AClient()
      task = await client.delegate_task(
          agent_id="code-reviewer",
          description="Review the fix for P0 issue #42",
          payload={"issue_id": 42, "priority": "P0"},
      )
    """

    def __init__(self, registry: Optional[AgentRegistry] = None, timeout: float = 30.0):
        self._registry = registry or get_registry()
        self._timeout = timeout
        self._active_tasks: dict[str, A2ATask] = {}

    async def delegate_task(
        self,
        agent_id: str,
        description: str,
        payload: Optional[dict] = None,
        skill_id: Optional[str] = None,
    ) -> A2ATask:
        """
        向指定 Agent 委派任务

        Args:
            agent_id: 目标 Agent ID
            description: 任务描述（自然语言）
            payload: 任务附加上下文
            skill_id: 指定调用的技能 ID

        Returns:
            A2ATask 实例
        """
        agent = self._registry.get(agent_id)
        if not agent:
            raise ValueError(f"Agent '{agent_id}' not found in registry")

        if agent.status != "active":
            raise ValueError(f"Agent '{agent_id}' is not active (status={agent.status})")

        task_id = str(uuid.uuid4())
        task = A2ATask(task_id, agent_id, description, payload or {})

        # 构建 A2A 请求体
        a2a_payload = {
            "id": task_id,
            "initialMessage": {
                "role": "user",
                "parts": [
                    {
                        "type": "text",
                        "text": description,
                    }
                ],
            },
            "metadata": {
                "source": "metis-pm",
                "skill_id": skill_id,
                **(payload or {}),
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{agent.url}/tasks",
                    json=a2a_payload,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code in (200, 201, 202):
                    resp_data = resp.json()
                    task.status = resp_data.get("status", TASK_WORKING)
                    task.updated_at = datetime.now(timezone.utc).isoformat()
                    logger.info(
                        "Task %s delegated to %s, status=%s",
                        task_id, agent_id, task.status,
                    )
                else:
                    task.status = TASK_FAILED
                    task.result = f"A2A request failed: {resp.status_code} {resp.text}"
                    logger.error(
                        "Task %s delegation failed: %s %s",
                        task_id, resp.status_code, resp.text[:200],
                    )
                    self._registry.mark_error(agent_id)
        except httpx.ConnectError as e:
            task.status = TASK_FAILED
            task.result = f"Connection error: {e}"
            logger.error("Task %s connection failed: %s", task_id, e)
            self._registry.mark_error(agent_id)
        except httpx.TimeoutException as e:
            task.status = TASK_FAILED
            task.result = f"Timeout: {e}"
            logger.error("Task %s timeout: %s", task_id, e)
        except Exception as e:
            task.status = TASK_FAILED
            task.result = f"Unexpected error: {e}"
            logger.error("Task %s unexpected error: %s", task_id, e)

        self._active_tasks[task_id] = task
        return task

    async def delegate_to_capability(
        self,
        capability: str,
        description: str,
        payload: Optional[dict] = None,
    ) -> list[A2ATask]:
        """
        按能力查找 Agent 并委派任务

        找到所有匹配能力的活跃 Agent，向第一个发送任务。
        如果需要广播，可以修改为向所有匹配 Agent 发送。

        Args:
            capability: 能力标签，如 "issue-handling", "risk-analysis"
            description: 任务描述
            payload: 任务附加上下文

        Returns:
            创建的任务列表
        """
        agents = self._registry.find_by_capability(capability)
        if not agents:
            logger.warning("No active agent found for capability: %s", capability)
            return []

        # 选择第一个匹配的 Agent（后续可扩展为负载均衡策略）
        agent = agents[0]
        task = await self.delegate_task(agent.agent_id, description, payload)
        return [task]

    async def get_task_status(self, agent_id: str, task_id: str) -> Optional[dict]:
        """查询任务状态"""
        agent = self._registry.get(agent_id)
        if not agent:
            return None

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{agent.url}/tasks/{task_id}")
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error("Failed to get task status: %s", e)

        return None

    async def discover_agent(self, url: str) -> Optional[AgentCard]:
        """
        发现 Agent：获取 Agent Card 并注册

        Args:
            url: Agent 的基础 URL

        Returns:
            解析后的 AgentCard，失败返回 None
        """
        card_url = f"{url}/.well-known/agent-card.json"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(card_url)
                if resp.status_code == 200:
                    card_data = resp.json()
                    card = AgentCard.from_card_json(card_data, url=url)
                    self._registry.register(card)
                    logger.info("Discovered agent: %s at %s", card.name, url)
                    return card
                else:
                    logger.warning("Failed to fetch agent card from %s: %s", card_url, resp.status_code)
        except Exception as e:
            logger.error("Failed to discover agent at %s: %s", url, e)

        return None

    def get_active_tasks(self) -> list[A2ATask]:
        return [t for t in self._active_tasks.values() if t.status in (TASK_SUBMITTED, TASK_WORKING)]

    def get_all_tasks(self) -> list[A2ATask]:
        return list(self._active_tasks.values())


# 全局单例
_client: Optional[A2AClient] = None


def get_a2a_client() -> A2AClient:
    global _client
    if _client is None:
        _client = A2AClient()
    return _client
