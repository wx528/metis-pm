import os
import httpx
from pm_copilot_engine import registry

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/api/v1")
API_KEY = os.getenv("API_KEY", "metis-pm-default-key-change-me")
ROLE = "agent"

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


async def _api(method: str, path: str, **kwargs) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, f"{BACKEND_URL}{path}", headers=HEADERS, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}


@registry.tool(toolset="agent")
async def list_my_issues(project_id: int | None = None, status: str | None = None) -> str:
    """列出分配给我的 Issue。

    Args:
        project_id: 项目 ID（可选）
        status: 状态筛选 open/in_progress/resolved/closed（可选）
    """
    params = {"assignee_role": ROLE}
    if project_id:
        params["project_id"] = project_id
    if status:
        params["status"] = status
    result = await _api("GET", "/issues", params=params)
    items = result.get("items", [])
    if not items:
        return "没有分配给你的 Issue。"
    lines = [f"共 {result['total']} 个 Issue："]
    for i in items:
        lines.append(f"  #{i['id']} [{i['priority']}] {i['title']} ({i['status']})")
    return "\n".join(lines)


@registry.tool(toolset="agent")
async def get_issue(issue_id: int) -> str:
    """查看 Issue 详情。

    Args:
        issue_id: Issue ID
    """
    result = await _api("GET", f"/issues/{issue_id}")
    comments = result.get("comments", [])
    lines = [
        f"#{result['id']} {result['title']}",
        f"状态: {result['status']} | 优先级: {result['priority']} | 类型: {result['issue_type']}",
        f"描述: {result.get('description', '无')}",
    ]
    if comments:
        lines.append(f"\n评论 ({len(comments)}):")
        for c in comments:
            lines.append(f"  [{c['author_role']}] {c['content']}")
    return "\n".join(lines)


@registry.tool(toolset="agent")
async def update_issue_status(issue_id: int, status: str) -> str:
    """更新 Issue 状态。

    Args:
        issue_id: Issue ID
        status: 新状态 open/in_progress/resolved/closed
    """
    result = await _api("PUT", f"/issues/{issue_id}", json={"status": status})
    return f"Issue #{issue_id} 状态已更新为 {status}"


@registry.tool(toolset="agent")
async def add_comment(issue_id: int, content: str) -> str:
    """在 Issue 上添加评论。

    Args:
        issue_id: Issue ID
        content: 评论内容
    """
    await _api("POST", f"/issues/{issue_id}/comments", json={"content": content, "author_role": ROLE})
    return f"已在 Issue #{issue_id} 添加评论"


@registry.tool(toolset="agent")
async def propose_plan(project_id: int, title: str, description: str = "") -> str:
    """提出执行计划。

    Args:
        project_id: 项目 ID
        title: 计划标题
        description: 计划描述
    """
    result = await _api("POST", "/plans", json={
        "title": title, "description": description,
        "project_id": project_id, "proposed_by": ROLE,
    })
    return f"已创建 Plan #{result['id']}: {result['title']}"


@registry.tool(toolset="agent")
async def update_plan_progress(plan_id: int, item_title: str, status: str) -> str:
    """更新计划进度。

    Args:
        plan_id: Plan ID
        item_title: 进度项标题
        status: 状态 todo/in_progress/done
    """
    await _api("POST", f"/plans/{plan_id}/items", json={
        "title": item_title, "status": status,
    })
    return f"Plan #{plan_id} 进度已更新: {item_title} -> {status}"


@registry.tool(toolset="agent")
async def list_plans(project_id: int | None = None) -> str:
    """查看项目计划列表。

    Args:
        project_id: 项目 ID（可选）
    """
    params = {}
    if project_id:
        params["project_id"] = project_id
    result = await _api("GET", "/plans", params=params)
    if not result:
        return "暂无计划。"
    lines = ["计划列表："]
    for p in result:
        lines.append(f"  #{p['id']} [{p['status']}] {p['title']} ({p.get('item_done_count', 0)}/{p.get('item_count', 0)})")
    return "\n".join(lines)


@registry.tool(toolset="agent")
async def notify_role(target_role: str, message: str, project_id: int | None = None) -> str:
    """通知其他角色。

    Args:
        target_role: 目标角色 agent/mate/tester/admin
        message: 通知内容
        project_id: 项目 ID（可选）
    """
    await _api("POST", "/notifications", json={
        "target_role": target_role, "message": message, "project_id": project_id,
    })
    return f"已通知 {target_role}: {message}"


def register_tools():
    pass
