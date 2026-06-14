"""
A2A 管理 API：注册、发现、管理外部 Agent

端点：
  GET    /api/v1/a2a/agents          — 列出已注册的 Agent
  POST   /api/v1/a2a/agents          — 手动注册 Agent
  DELETE /api/v1/a2a/agents/{id}     — 注销 Agent
  POST   /api/v1/a2a/discover        — 发现指定 URL 的 Agent
  GET    /api/v1/a2a/tasks           — 查看 A2A 任务列表
  POST   /api/v1/a2a/delegate        — 手动委派任务给 Agent
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.a2a.registry import AgentCard, AgentSkill, get_registry
from src.a2a.client import get_a2a_client

logger = logging.getLogger("a2a.api")
router = APIRouter()


# ── Pydantic Models ─────────────────────────────────────

class AgentRegisterRequest(BaseModel):
    agent_id: str
    name: str
    url: str
    description: str = ""
    framework: str = ""
    auth_type: str = ""
    skills: list[dict] = []


class AgentDiscoverRequest(BaseModel):
    url: str


class DelegateTaskRequest(BaseModel):
    agent_id: Optional[str] = None
    capability: Optional[str] = None
    description: str
    payload: Optional[dict] = None


# ── 端点 ────────────────────────────────────────────────

@router.get("/agents")
async def list_agents():
    """列出所有已注册的 A2A Agent"""
    registry = get_registry()
    agents = registry.list_all()
    return {"total": len(agents), "items": [a.to_dict() for a in agents]}


@router.post("/agents")
async def register_agent(req: AgentRegisterRequest):
    """手动注册一个外部 A2A Agent"""
    registry = get_registry()
    if registry.get(req.agent_id):
        raise HTTPException(status_code=409, detail=f"Agent '{req.agent_id}' already registered")

    skills = [AgentSkill(**s) for s in req.skills]
    card = AgentCard(
        agent_id=req.agent_id,
        name=req.name,
        description=req.description,
        url=req.url,
        card_url=f"{req.url}/.well-known/agent-card.json",
        skills=skills,
        framework=req.framework,
        auth_type=req.auth_type,
    )
    registry.register(card)
    return {"message": f"Agent '{req.name}' registered", "agent_id": req.agent_id}


@router.delete("/agents/{agent_id}")
async def unregister_agent(agent_id: str):
    """注销一个外部 A2A Agent"""
    registry = get_registry()
    if not registry.unregister(agent_id):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return {"message": f"Agent '{agent_id}' unregistered"}


@router.post("/discover")
async def discover_agent(req: AgentDiscoverRequest):
    """发现指定 URL 的 A2A Agent（获取其 Agent Card）"""
    client = get_a2a_client()
    card = await client.discover_agent(req.url)
    if not card:
        raise HTTPException(status_code=502, detail=f"Failed to discover agent at {req.url}")
    return card.to_dict()


@router.get("/tasks")
async def list_tasks():
    """查看 A2A 任务列表"""
    client = get_a2a_client()
    tasks = client.get_all_tasks()
    return {"total": len(tasks), "items": [t.to_dict() for t in tasks]}


@router.post("/delegate")
async def delegate_task(req: DelegateTaskRequest):
    """手动委派任务给 A2A Agent"""
    client = get_a2a_client()

    if req.agent_id:
        task = await client.delegate_task(req.agent_id, req.description, req.payload)
    elif req.capability:
        tasks = await client.delegate_to_capability(req.capability, req.description, req.payload)
        if not tasks:
            raise HTTPException(status_code=404, detail=f"No agent found for capability '{req.capability}'")
        task = tasks[0]
    else:
        raise HTTPException(status_code=400, detail="Must provide either agent_id or capability")

    return task.to_dict()
