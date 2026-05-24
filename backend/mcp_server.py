"""
Project Manager MCP Server
AI Coding Agent 通过 MCP 协议与本系统交互的工具入口

=== stdio 模式配置（CodeBuddy/Cline） ===
{
  "mcpServers": {
    "project-manager": {
      "command": "python",
      "args": ["D:/AI-learning/project-manager-system/backend/mcp_server.py"],
      "env": {
        "PM_API_URL": "http://localhost:8098/api/v1",
        "PM_AGENT_PASSWORD": "CHANGE-ME"
      }
    }
  }
}

=== Streamable HTTP 模式配置（Hermes 等远程 Agent） ===
{
  "mcpServers": {
    "project-manager": {
      "url": "http://localhost:9000/mcp",
      "headers": {
        "X-PM-Password": "CHANGE-ME"
      }
    }
  }
}

密码对应 .env 的 AGENT_PASSWORDS，格式 "agent_name:password"
例如 AGENT_PASSWORDS=trae:CHANGE-ME,hermes-agent:CHANGE-ME

HTTP 模式通过 X-PM-Password 请求头传递密码，每个客户端可以有独立身份。
无密码头时使用启动时的 PM_AGENT_PASSWORD 作为默认身份。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import asyncio
from datetime import datetime, timezone
from typing import Optional
from contextvars import ContextVar

import httpx
from mcp.server.fastmcp import FastMCP

API_BASE = os.environ.get("PM_API_URL", "http://localhost:8000/api/v1")
AGENT_PASSWORD = os.environ.get("PM_AGENT_PASSWORD", "")

_request_password: ContextVar[str] = ContextVar("_request_password", default="")


def _get_password() -> str:
    return _request_password.get() or AGENT_PASSWORD


_token_cache: dict[str, dict] = {}


def _cache_key(password: str) -> str:
    return password


async def _ensure_token() -> str:
    password = _get_password()
    key = _cache_key(password)
    if _token_cache.get(key, {}).get("token"):
        return _token_cache[key]["token"]
    return await _login(password)


async def _login(password: str = "") -> str:
    password = password or _get_password()
    if not password:
        raise RuntimeError("No agent password. Set PM_AGENT_PASSWORD env (stdio) or X-PM-Password header (HTTP).")
    key = _cache_key(password)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/auth/login",
            json={"password": password},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Login failed ({resp.status_code}): {resp.text}")
        data = resp.json()
        _token_cache[key] = {
            "token": data["token"],
            "sub": data.get("sub", "unknown"),
            "role": data.get("role", "unknown"),
        }
        return _token_cache[key]["token"]


async def _api_request(method: str, url: str, *, max_retries: int = 1, **kwargs) -> httpx.Response:
    password = _get_password()
    headers = kwargs.pop("headers", None) or await get_headers()
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, headers=headers, **kwargs)
        if resp.status_code == 401 and max_retries > 0:
            key = _cache_key(password)
            _token_cache.pop(key, None)
            headers = await get_headers()
            resp = await client.request(method, url, headers=headers, **kwargs)
        return resp


async def get_headers() -> dict:
    token = await _ensure_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


mcp = FastMCP("project-manager")


class PasswordMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope.get("headers", []))
            pw = headers.get(b"x-pm-password", b"").decode()
            if pw:
                _request_password.set(pw)
        await self.app(scope, receive, send)


def _current_sub() -> str:
    password = _get_password()
    key = _cache_key(password)
    return _token_cache.get(key, {}).get("sub", "ai_agent")


@mcp.tool()
async def check_connection() -> str:
    """测试 MCP Server 与后端 API 的连接是否正常"""
    try:
        headers = await get_headers()
    except RuntimeError as e:
        return f"ERROR: {e}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/auth/me", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return f"Connected OK. Identity: {data.get('sub', '?')} (role={data.get('role', '?')})"
        elif resp.status_code == 401:
            key = _cache_key(_get_password())
            _token_cache.pop(key, None)
            return "ERROR: Token invalid or expired (401). Will re-login on next call."
        else:
            return f"ERROR: API returned {resp.status_code}. Is the backend running?"


# ── Projects ────────────────────────────────────────

@mcp.tool()
async def list_projects() -> str:
    """列出所有项目（含统计）"""
    resp = await _api_request("GET", f"{API_BASE}/projects")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    items = resp.json()
    if not items:
        return "No projects found. Create one with create_project tool."
    lines = [f"Total: {len(items)} projects"]
    for item in items:
        status = item.get("status", "?")
        stats = f" ({item.get('issue_count',0)} issues, {item.get('plan_count',0)} plans, {item.get('milestone_count',0)} milestones, {item.get('server_count',0)} servers)"
        lines.append(f"  #{item['id']} [{status}] {item['name']} (slug={item['slug']}){stats}")
    return "\n".join(lines)


@mcp.tool()
async def create_project(
    name: str,
    slug: str,
    description: str = "",
    repo_url: str = "",
) -> str:
    """创建新项目。slug 只允许小写字母、数字和连字符，如 my-project-1"""
    payload = {
        "name": name,
        "slug": slug,
    }
    if description:
        payload["description"] = description
    if repo_url:
        payload["repo_url"] = repo_url
    resp = await _api_request("POST", f"{API_BASE}/projects", json=payload)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Project #{data['id']} created: {data['name']} (slug={data['slug']}, status={data['status']})"


# ── Issues ─────────────────────────────────────────

@mcp.tool()
async def create_issue(
    title: str,
    description: str = "",
    priority: str = "P2",
    issue_type: str = "task",
    project_id: Optional[int] = None,
    milestone_id: Optional[int] = None,
    labels: str = "",
) -> str:
    """创建 issue，source 自动标记为当前 agent 身份"""
    agent_name = _current_sub()
    payload = {
        "title": title,
        "description": description,
        "priority": priority,
        "issue_type": issue_type,
        "source": "ai_agent",
        "milestone_id": milestone_id,
        "labels": labels,
    }
    if project_id:
        payload["project_id"] = project_id
    resp = await _api_request("POST", f"{API_BASE}/issues", json=payload)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    project_info = f" (project_id={data.get('project_id')})" if data.get('project_id') else ""
    return f"Issue #{data['id']} created: [{data['priority']}] {data['title']} (status={data['status']}){project_info}"


@mcp.tool()
async def list_issues(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    source: Optional[str] = None,
    milestone_id: Optional[int] = None,
    deferred_only: bool = False,
    limit: int = 20,
) -> str:
    """查询 issues 列表"""
    params = {"limit": limit}
    if project_id:
        params["project_id"] = project_id
    if status:
        params["status"] = status
    if priority:
        params["priority"] = priority
    if source:
        params["source"] = source
    if milestone_id:
        params["milestone_id"] = milestone_id
    if deferred_only:
        params["deferred_only"] = "true"

    resp = await _api_request("GET", f"{API_BASE}/issues", params=params)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    items = data.get("items", [])
    if not items:
        return "No issues found."
    lines = [f"Total: {data['total']} issues"]
    for item in items:
        lines.append(f"  #{item['id']} [{item['priority']}] {item['title']} ({item['status']}, source={item['source']})")
    return "\n".join(lines)


@mcp.tool()
async def update_issue_status(issue_id: int, status: str) -> str:
    """更新 issue 状态: open/in_progress/review/deferred/closed/cancelled"""
    resp = await _api_request("PUT", f"{API_BASE}/issues/{issue_id}", json={"status": status})
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Issue #{data['id']} status updated to {data['status']}"


@mcp.tool()
async def update_issue_priority(issue_id: int, priority: str) -> str:
    """更新 issue 优先级: P0/P1/P2/P3"""
    resp = await _api_request("PUT", f"{API_BASE}/issues/{issue_id}", json={"priority": priority})
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Issue #{data['id']} priority updated to {data['priority']}"


@mcp.tool()
async def defer_issue(issue_id: int, milestone_id: int, reason: str = "") -> str:
    """将 issue 暂缓到指定 milestone"""
    params = {"deferred_to_milestone_id": milestone_id}
    if reason:
        params["deferred_reason"] = reason
    resp = await _api_request("POST", f"{API_BASE}/issues/{issue_id}/defer", params=params)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Issue #{data['id']} deferred to milestone #{data['deferred_to_milestone_id']}: {data.get('deferred_reason', '')}"


@mcp.tool()
async def add_issue_comment(issue_id: int, content: str) -> str:
    """为 issue 添加评论"""
    agent_name = _current_sub()
    resp = await _api_request("POST", f"{API_BASE}/issues/{issue_id}/comments", json={"content": content, "author": agent_name})
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    return f"Comment added to Issue #{issue_id}"


# ── Plans ──────────────────────────────────────────

@mcp.tool()
async def propose_plan(title: str, description: str = "", project_id: Optional[int] = None) -> str:
    """提议一个新计划（状态为 pending_approval，等待用户审批）"""
    payload = {
        "title": title,
        "description": description,
        "proposed_by": "ai_agent",
        "status": "pending_approval",
    }
    if project_id:
        payload["project_id"] = project_id
    resp = await _api_request("POST", f"{API_BASE}/plans", json=payload)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Plan #{data['id']} proposed: {data['title']} (status={data['status']}, waiting for approval)"


@mcp.tool()
async def list_plans(status: Optional[str] = None, project_id: Optional[int] = None) -> str:
    """查询计划列表"""
    params = {}
    if status:
        params["status"] = status
    if project_id:
        params["project_id"] = project_id
    resp = await _api_request("GET", f"{API_BASE}/plans", params=params)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    items = resp.json()
    if not items:
        return "No plans found."
    lines = [f"Total: {len(items)} plans"]
    for item in items:
        lines.append(f"  #{item['id']} [{item['status']}] {item['title']} (proposed_by={item['proposed_by']})")
    return "\n".join(lines)


@mcp.tool()
async def update_plan_progress(plan_id: int, item_title: str, status: str = "done") -> str:
    """更新计划项进度。如果 plan_item 不存在则自动创建。"""
    agent_name = _current_sub()
    resp = await _api_request("GET", f"{API_BASE}/plans/{plan_id}/items")
    if resp.status_code >= 400:
        return f"Error getting plan items: {resp.status_code}"
    items = resp.json()

    # 查找匹配的 item
    target_item = None
    for item in items:
        if item["title"] == item_title:
            target_item = item
            break

    if target_item:
        # 更新现有 item
        resp = await _api_request(
            "PUT",
            f"{API_BASE}/plans/{plan_id}/items/{target_item['id']}",
            json={
                "status": status,
                "completed_by": agent_name if status == "done" else None,
                "completed_at": datetime.now(timezone.utc).isoformat() if status == "done" else None,
            },
        )
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        return f"PlanItem '{item_title}' updated to {status}"
    else:
        # 创建新 item
        resp = await _api_request(
            "POST",
            f"{API_BASE}/plans/{plan_id}/items",
            json={"title": item_title, "status": status},
        )
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        return f"PlanItem '{item_title}' created with status {status}"


# ── Milestones ─────────────────────────────────────

@mcp.tool()
async def list_milestones(project_id: Optional[int] = None) -> str:
    """查询里程碑/阶段列表"""
    params = {}
    if project_id:
        params["project_id"] = project_id
    resp = await _api_request("GET", f"{API_BASE}/milestones", params=params)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    items = resp.json()
    if not items:
        return "No milestones found."
    lines = [f"Total: {len(items)} milestones"]
    for item in items:
        phase = f" ({item['phase']})" if item.get('phase') else ""
        desc = f"\n    描述: {item['description']}" if item.get('description') else ""
        due = f"\n    截止: {item['due_date']}" if item.get('due_date') else ""
        stats = f"\n    统计: {item.get('total_issues',0)} issues ({item.get('open_issues',0)} open, {item.get('closed_issues',0)} closed, {item.get('deferred_issues',0)} deferred)"
        lines.append(f"  #{item['id']} [{item['status']}] {item['title']}{phase}{desc}{due}{stats}")
    return "\n".join(lines)


@mcp.tool()
async def create_milestone(
    title: str,
    phase: str = "",
    description: str = "",
    project_id: Optional[int] = None,
    due_date: str = "",
) -> str:
    """创建里程碑/阶段。phase 如 phase-1/MVP 等，due_date 格式 YYYY-MM-DD"""
    payload = {"title": title}
    if phase:
        payload["phase"] = phase
    if description:
        payload["description"] = description
    if project_id:
        payload["project_id"] = project_id
    if due_date:
        payload["due_date"] = due_date
    resp = await _api_request("POST", f"{API_BASE}/milestones", json=payload)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    phase_info = f" (phase={data['phase']})" if data.get('phase') else ""
    return f"Milestone #{data['id']} created: {data['title']}{phase_info} (status={data['status']})"


# ── Servers ────────────────────────────────────────

@mcp.tool()
async def list_servers(project_id: Optional[int] = None) -> str:
    """查询服务器列表"""
    params = {}
    if project_id:
        params["project_id"] = project_id
    resp = await _api_request("GET", f"{API_BASE}/servers", params=params)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    items = resp.json()
    if not items:
        return "No servers found."
    lines = [f"Total: {len(items)} servers"]
    for item in items:
        lines.append(f"  #{item['id']} [{item['status']}] {item['name']} ({item['ip_address'] or 'no IP'})")
    return "\n".join(lines)


@mcp.tool()
async def get_server_credentials(server_id: int) -> str:
    """获取服务器凭据元信息（不含明文密码/密钥，仅返回是否已设置及长度等摘要信息）。如需查看完整凭据，请通过 Web UI 以 admin 身份访问。"""
    resp = await _api_request("GET", f"{API_BASE}/servers/{server_id}")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    pwd_info = "已设置" if data.get("has_password") else "未设置"
    ssh_info = "已设置" if data.get("has_ssh_key") else "未设置"
    return (
        f"Server: {data['name']}\n"
        f"IP: {data.get('ip_address', 'N/A')}:{data.get('port', 'N/A')}\n"
        f"Username: {data.get('username', 'N/A')}\n"
        f"Password: {pwd_info}\n"
        f"SSH Key: {ssh_info}\n"
        f"Status: {data.get('status', 'N/A')}\n"
        f"\n提示: 出于安全考虑，凭据明文不会进入 AI 上下文。请通过 Web UI (admin) 查看完整凭据。"
    )


# ── Notifications ───────────────────────────────────

@mcp.tool()
async def check_notifications(unread_only: bool = False, limit: int = 10) -> str:
    """检查当前 Agent 的通知"""
    params = {"limit": limit}
    if unread_only:
        params["unread_only"] = "true"
    resp = await _api_request("GET", f"{API_BASE}/notifications", params=params)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    items = data.get("items", [])
    if not items:
        return "No notifications."
    lines = [f"Total: {data['total']} notifications (showing {len(items)})"]
    for item in items:
        read_mark = "✓" if item.get("read") else "●"
        lines.append(f"  {read_mark} [{item['type']}] {item['title']}")
        if item.get("body"):
            lines.append(f"    {item['body']}")
    return "\n".join(lines)


@mcp.tool()
async def mark_notification_read(notification_id: int) -> str:
    """标记通知已读"""
    resp = await _api_request("PUT", f"{API_BASE}/notifications/{notification_id}/read")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    return f"Notification #{notification_id} marked as read"


# ── Workflows ──────────────────────────────────────

@mcp.tool()
async def list_workflows(project_id: Optional[int] = None) -> str:
    """列出工作流"""
    params = {}
    if project_id:
        params["project_id"] = project_id
    resp = await _api_request("GET", f"{API_BASE}/workflows", params=params)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    items = resp.json()
    if not items:
        return "No workflows found."
    lines = [f"Total: {len(items)} workflows"]
    for item in items:
        trigger = item.get('trigger', '?')
        status = item.get('status', '?')
        steps_count = len(item.get('steps', [])) if 'steps' in item else '?'
        lines.append(f"  #{item['id']} [{status}] {item['name']} (trigger={trigger}, steps={steps_count})")
    return "\n".join(lines)


@mcp.tool()
async def create_workflow(
    name: str,
    trigger: str = "manual",
    project_id: Optional[int] = None,
    description: str = "",
    steps: str = "",
) -> str:
    """创建工作流。trigger: on_issue_created/on_plan_approved/manual。steps 为 JSON 数组字符串，每项含 step_type 和 config。"""
    payload = {
        "name": name,
        "description": description,
        "trigger": trigger,
    }
    if project_id:
        payload["project_id"] = project_id
    if steps:
        import json
        try:
            payload["steps"] = json.loads(steps)
        except json.JSONDecodeError:
            return "Error: steps must be a valid JSON array string"

    resp = await _api_request("POST", f"{API_BASE}/workflows", json=payload)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    step_info = f" with {len(data.get('steps', []))} steps" if data.get('steps') else ""
    return f"Workflow #{data['id']} created: {data['name']} (trigger={data['trigger']}){step_info}"


@mcp.tool()
async def trigger_workflow(workflow_id: int) -> str:
    """手动触发工作流"""
    resp = await _api_request("POST", f"{API_BASE}/workflows/{workflow_id}/trigger")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Workflow triggered! Run #{data['id']} (status={data['status']})"


@mcp.tool()
async def list_workflow_runs(workflow_id: Optional[int] = None, limit: int = 10) -> str:
    """查看工作流执行记录"""
    params = {"limit": limit}
    if workflow_id:
        params["workflow_id"] = workflow_id
    resp = await _api_request("GET", f"{API_BASE}/workflows/runs", params=params)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    items = resp.json()
    if not items:
        return "No workflow runs found."
    lines = [f"Total: {len(items)} runs"]
    for item in items:
        wf_name = item.get('workflow_name', '?')
        lines.append(f"  Run #{item['id']} [{item['status']}] {wf_name} (step {item['current_step_index']}, by {item.get('triggered_by', '?')})")
    return "\n".join(lines)


MCP_PORT = int(os.environ.get("MCP_PORT", "9000"))
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio")


def main():
    if MCP_TRANSPORT == "sse":
        mcp.settings.host = MCP_HOST
        mcp.settings.port = MCP_PORT
        app = PasswordMiddleware(mcp.sse_app())
        import uvicorn
        uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
    elif MCP_TRANSPORT == "streamable-http":
        mcp.settings.host = MCP_HOST
        mcp.settings.port = MCP_PORT
        app = PasswordMiddleware(mcp.streamable_http_app())
        import uvicorn
        uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
