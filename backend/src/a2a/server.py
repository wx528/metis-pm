"""
A2A Server：PM 系统作为 A2A Agent 暴露能力

PM 系统发布 Agent Card，外部 Agent 可以通过 A2A 协议调用 PM 的能力：
  - 查询项目/Issue/计划状态
  - 创建 Issue
  - 审批计划
  - 等等

端点：
  GET  /.well-known/agent-card.json   — Agent Card
  POST /a2a/tasks                     — 创建任务
  GET  /a2a/tasks/{id}                — 查询任务状态
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("a2a.server")

router = APIRouter(prefix="/a2a", tags=["A2A"])


# ── Agent Card ──────────────────────────────────────────

AGENT_CARD = {
    "id": "metis-pm",
    "name": "Metis PM",
    "description": (
        "Project Management System with AI Copilot. "
        "Can manage projects, issues, plans, milestones, workflows, and risk alerts. "
        "Supports multi-agent collaboration via A2A protocol."
    ),
    "url": "",  # 运行时填充
    "version": "1.0.0",
    "framework": "custom",
    "skills": [
        {
            "id": "issue-management",
            "name": "Issue Management",
            "description": "Create, update, query, and manage project issues",
            "tags": ["issues", "tasks", "bugs", "features"],
        },
        {
            "id": "plan-management",
            "name": "Plan Management",
            "description": "Propose, approve, reject, and track execution plans",
            "tags": ["plans", "approval", "workflow"],
        },
        {
            "id": "risk-monitoring",
            "name": "Risk Monitoring",
            "description": "Monitor and alert on project risks, overdue tasks, and critical issues",
            "tags": ["risk", "alerts", "monitoring"],
        },
        {
            "id": "project-overview",
            "name": "Project Overview",
            "description": "Get project dashboard, statistics, and health status",
            "tags": ["dashboard", "statistics", "health"],
        },
        {
            "id": "agent-coordination",
            "name": "Agent Coordination",
            "description": "Coordinate multiple agents: assign tasks, track workload, review results",
            "tags": ["coordination", "assignment", "workload"],
        },
    ],
}


# ── Pydantic Models ─────────────────────────────────────

class A2AMessagePart(BaseModel):
    type: str = "text"
    text: str = ""


class A2AMessage(BaseModel):
    role: str = "user"
    parts: list[A2AMessagePart] = []


class A2ATaskCreate(BaseModel):
    id: Optional[str] = None
    initialMessage: A2AMessage
    metadata: Optional[dict] = None


class A2ATaskStatus(BaseModel):
    task_id: str
    status: str
    result: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


# ── 内存任务存储 ─────────────────────────────────────────

_tasks_store: dict[str, A2ATaskStatus] = {}


# ── Agent Card 端点 ─────────────────────────────────────

@router.get("/agent-card")
async def get_agent_card(request: Request):
    """返回 PM 系统的 Agent Card"""
    card = AGENT_CARD.copy()
    card["url"] = str(request.base_url).rstrip("/") + "/a2a"
    return card


# ── 任务端点 ─────────────────────────────────────────────

@router.post("/tasks")
async def create_task(task_req: A2ATaskCreate, request: Request):
    """
    外部 Agent 向 PM 系统委派任务

    PM 系统接收任务后，根据内容路由到对应的处理逻辑：
    - 查询类任务：直接从数据库获取并返回
    - 操作类任务：执行操作并返回结果
    """
    task_id = task_req.id or str(uuid.uuid4())

    # 提取任务描述
    description = ""
    if task_req.initialMessage and task_req.initialMessage.parts:
        description = " ".join(p.text for p in task_req.initialMessage.parts if p.text)

    logger.info("A2A task received: %s — %s", task_id, description[:100])

    # 创建任务记录
    task_status = A2ATaskStatus(
        task_id=task_id,
        status="working",
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    _tasks_store[task_id] = task_status

    # 异步处理任务（简化实现：同步执行，后续可改为后台任务）
    try:
        result = await _process_task(description, task_req.metadata or {})
        task_status.status = "completed"
        task_status.result = result
    except Exception as e:
        task_status.status = "failed"
        task_status.result = str(e)
        logger.error("A2A task %s failed: %s", task_id, e)

    task_status.updated_at = datetime.now(timezone.utc).isoformat()

    return {
        "id": task_id,
        "status": task_status.status,
        "result": task_status.result,
        "created_at": task_status.created_at,
        "updated_at": task_status.updated_at,
    }


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """查询任务状态"""
    task = _tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task.model_dump()


# ── 任务处理逻辑 ─────────────────────────────────────────

async def _process_task(description: str, metadata: dict) -> str:
    """
    处理 A2A 任务

    根据任务描述路由到对应的处理逻辑。
    当前实现为简化版，后续可接入 Copilot 进行智能处理。
    """
    from src.core.database import get_session
    from sqlalchemy import select, func
    from src.models.issue import Issue
    from src.models.project import Project
    from src.models.plan import Plan

    desc_lower = description.lower()

    async with get_session() as session:
        # 查询类任务
        if any(kw in desc_lower for kw in ["list", "show", "query", "status", "overview", "dashboard"]):
            if "issue" in desc_lower:
                result = await session.execute(
                    select(func.count()).select_from(Issue)
                )
                total = result.scalar() or 0
                return f"Total issues: {total}"

            elif "project" in desc_lower:
                result = await session.execute(
                    select(func.count()).select_from(Project)
                )
                total = result.scalar() or 0
                return f"Total projects: {total}"

            elif "plan" in desc_lower:
                result = await session.execute(
                    select(func.count()).select_from(Plan)
                )
                total = result.scalar() or 0
                return f"Total plans: {total}"

            else:
                return "Please specify what you'd like to query: issues, projects, or plans."

        # 默认响应
        return (
            f"Task received: '{description}'. "
            f"For complex operations, please use the MCP server interface. "
            f"Available skills: issue-management, plan-management, risk-monitoring, "
            f"project-overview, agent-coordination."
        )
