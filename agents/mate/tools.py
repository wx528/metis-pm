import os
import httpx
from pm_copilot_engine import registry

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/api/v1")
API_KEY = os.getenv("API_KEY", "metis-pm-default-key-change-me")
ROLE = "mate"

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


async def _api(method: str, path: str, **kwargs) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, f"{BACKEND_URL}{path}", headers=HEADERS, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}


@registry.tool(toolset="mate")
async def list_pending_plans(project_id: int | None = None) -> str:
    """查看待审批的计划。

    Args:
        project_id: 项目 ID（可选）
    """
    params = {"status": "pending"}
    if project_id:
        params["project_id"] = project_id
    result = await _api("GET", "/plans", params=params)
    if not result:
        return "没有待审批的计划。"
    lines = [f"待审批计划 ({len(result)}):"]
    for p in result:
        lines.append(f"  #{p['id']} {p['title']} (by {p.get('proposed_by', 'unknown')})")
    return "\n".join(lines)


@registry.tool(toolset="mate")
async def approve_plan(plan_id: int) -> str:
    """批准计划。

    Args:
        plan_id: Plan ID
    """
    result = await _api("POST", f"/plans/{plan_id}/approve")
    return f"Plan #{plan_id} 已批准"


@registry.tool(toolset="mate")
async def reject_plan(plan_id: int, reason: str = "") -> str:
    """驳回计划。

    Args:
        plan_id: Plan ID
        reason: 驳回原因
    """
    await _api("POST", f"/plans/{plan_id}/reject", json={"reason": reason})
    return f"Plan #{plan_id} 已驳回: {reason}"


@registry.tool(toolset="mate")
async def assign_issue(issue_id: int, role: str = "agent") -> str:
    """分配 Issue 给指定角色。

    Args:
        issue_id: Issue ID
        role: 目标角色 agent/tester（默认 agent）
    """
    await _api("PUT", f"/issues/{issue_id}", json={"assignee_role": role})
    return f"Issue #{issue_id} 已分配给 {role}"


@registry.tool(toolset="mate")
async def get_project_overview(project_id: int) -> str:
    """查看项目全局状态。

    Args:
        project_id: 项目 ID
    """
    result = await _api("GET", f"/projects/{project_id}")
    return (
        f"项目: {result['name']}\n"
        f"Issue 总数: {result.get('issue_count', 0)} | "
        f"进行中: {result.get('open_issue_count', 0)} | "
        f"Plan 数: {result.get('plan_count', 0)}"
    )


def register_tools():
    pass
