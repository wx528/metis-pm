"""
Project Manager MCP Server
AI Coding Agent 通过 MCP 协议与本系统交互的工具入口

配置方式（CodeBuddy/Cline MCP 配置）：
{
  "mcpServers": {
    "project-manager": {
      "command": "python",
      "args": ["D:/AI-learning/tce_tiku/project_mananger_system/backend/mcp_server.py"],
      "env": {
        "PM_API_URL": "http://localhost:8000/api/v1",
        "PM_AGENT_PASSWORD": "CHANGE-ME"
      }
    }
  }
}

PM_AGENT_PASSWORD: 在 .env 的 AGENT_PASSWORDS 中配置，格式为 "agent_name:password"
例如 AGENT_PASSWORDS=cline:CHANGE-ME,buddy:buddy-2026
MCP Server 启动时会自动用 agent 密码登录获取 token
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import asyncio
from datetime import datetime, timezone
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

API_BASE = os.environ.get("PM_API_URL", "http://localhost:8000/api/v1")
AGENT_PASSWORD = os.environ.get("PM_AGENT_PASSWORD", "")
_token_cache: dict = {}


async def _ensure_token() -> str:
    global _token_cache
    if _token_cache.get("token"):
        return _token_cache["token"]
    if not AGENT_PASSWORD:
        raise RuntimeError("PM_AGENT_PASSWORD not set. Configure it in MCP settings.")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/auth/login",
            json={"password": AGENT_PASSWORD},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Login failed ({resp.status_code}): {resp.text}")
        data = resp.json()
        _token_cache["token"] = data["token"]
        _token_cache["sub"] = data.get("sub", "unknown")
        _token_cache["role"] = data.get("role", "unknown")
        return _token_cache["token"]


async def get_headers() -> dict:
    token = await _ensure_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


mcp = FastMCP("project-manager")


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
            _token_cache.clear()
            return "ERROR: Token invalid or expired (401). Will re-login on next call."
        else:
            return f"ERROR: API returned {resp.status_code}. Is the backend running?"


# ── Issues ─────────────────────────────────────────

@mcp.tool()
async def create_issue(
    title: str,
    description: str = "",
    priority: str = "P2",
    issue_type: str = "task",
    milestone_id: Optional[int] = None,
    labels: str = "",
) -> str:
    """创建 issue，source 自动标记为当前 agent 身份"""
    headers = await get_headers()
    agent_name = _token_cache.get("sub", "ai_agent")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/issues",
            headers=headers,
            json={
                "title": title,
                "description": description,
                "priority": priority,
                "issue_type": issue_type,
                "source": "ai_agent",
                "milestone_id": milestone_id,
                "labels": labels,
            },
        )
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        data = resp.json()
        return f"Issue #{data['id']} created: [{data['priority']}] {data['title']} (status={data['status']})"


@mcp.tool()
async def list_issues(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    source: Optional[str] = None,
    milestone_id: Optional[int] = None,
    deferred_only: bool = False,
    limit: int = 20,
) -> str:
    """查询 issues 列表"""
    params = {"limit": limit}
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

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/issues", headers=await get_headers(), params=params)
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
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{API_BASE}/issues/{issue_id}",
            headers=await get_headers(),
            json={"status": status},
        )
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        data = resp.json()
        return f"Issue #{data['id']} status updated to {data['status']}"


@mcp.tool()
async def update_issue_priority(issue_id: int, priority: str) -> str:
    """更新 issue 优先级: P0/P1/P2/P3"""
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{API_BASE}/issues/{issue_id}",
            headers=await get_headers(),
            json={"priority": priority},
        )
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        data = resp.json()
        return f"Issue #{data['id']} priority updated to {data['priority']}"


@mcp.tool()
async def defer_issue(issue_id: int, milestone_id: int, reason: str = "") -> str:
    """将 issue 暂缓到指定 milestone"""
    async with httpx.AsyncClient() as client:
        params = {"deferred_to_milestone_id": milestone_id}
        if reason:
            params["deferred_reason"] = reason
        resp = await client.post(
            f"{API_BASE}/issues/{issue_id}/defer",
            headers=await get_headers(),
            params=params,
        )
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        data = resp.json()
        return f"Issue #{data['id']} deferred to milestone #{data['deferred_to_milestone_id']}: {data.get('deferred_reason', '')}"


@mcp.tool()
async def add_issue_comment(issue_id: int, content: str) -> str:
    """为 issue 添加评论"""
    headers = await get_headers()
    agent_name = _token_cache.get("sub", "ai_agent")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/issues/{issue_id}/comments",
            headers=headers,
            json={"content": content, "author": agent_name},
        )
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        data = resp.json()
        return f"Comment added to Issue #{issue_id}"


# ── Plans ──────────────────────────────────────────

@mcp.tool()
async def propose_plan(title: str, description: str = "") -> str:
    """提议一个新计划（状态为 pending_approval，等待用户审批）"""
    headers = await get_headers()
    agent_name = _token_cache.get("sub", "ai_agent")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/plans",
            headers=headers,
            json={
                "title": title,
                "description": description,
                "proposed_by": agent_name,
                "status": "pending_approval",
            },
        )
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        data = resp.json()
        return f"Plan #{data['id']} proposed: {data['title']} (status={data['status']}, waiting for approval)"


@mcp.tool()
async def list_plans(status: Optional[str] = None) -> str:
    """查询计划列表"""
    params = {}
    if status:
        params["status"] = status
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/plans", headers=await get_headers(), params=params)
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
    headers = await get_headers()
    agent_name = _token_cache.get("sub", "ai_agent")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/plans/{plan_id}/items", headers=headers)
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
            resp = await client.put(
                f"{API_BASE}/plans/{plan_id}/items/{target_item['id']}",
                headers=headers,
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
            resp = await client.post(
                f"{API_BASE}/plans/{plan_id}/items",
                headers=headers,
                json={"title": item_title, "status": status},
            )
            if resp.status_code >= 400:
                return f"Error: {resp.status_code} - {resp.text}"
            return f"PlanItem '{item_title}' created with status {status}"


# ── Milestones ─────────────────────────────────────

@mcp.tool()
async def list_milestones() -> str:
    """查询里程碑/阶段列表"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/milestones", headers=await get_headers())
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


# ── Servers ────────────────────────────────────────

@mcp.tool()
async def list_servers() -> str:
    """查询服务器列表"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/servers", headers=await get_headers())
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
    """获取服务器凭据（IP、用户名、密码）。⚠️ 凭据将进入 AI 上下文，请谨慎使用。"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/servers/{server_id}/credentials", headers=await get_headers())
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        data = resp.json()
        return (
            f"⚠️ WARNING: Credentials are now in your AI context. Handle with care.\n"
            f"Server: {data['name']}\n"
            f"IP: {data.get('ip_address', 'N/A')}:{data.get('port', 'N/A')}\n"
            f"Username: {data.get('username', 'N/A')}\n"
            f"Password: {data.get('password', 'N/A')}\n"
            f"SSH Key: {'(present)' if data.get('ssh_key') else 'N/A'}\n"
            f"Status: see /servers/{server_id} for status info"
        )


def main():
    """Entry point for installed package."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
