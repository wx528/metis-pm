"""
Project Manager MCP Server - First Mate (大副)
管理类 Agent：审批 Plan、分配 Issue、监督项目进度

=== Streamable HTTP 模式配置 ===
{
  "mcpServers": {
    "project-manager-mate": {
      "url": "http://localhost:9001/mcp",
      "headers": {
        "X-PM-Password": "CHANGE-ME"
      }
    }
  }
}

大副角色职责：
  - 审批/拒绝 Agent 提交的 Plan
  - 分配 Issue 给特定 Agent
  - 监督项目全局进度
  - 调整优先级和里程碑

大副不负责：创建 Issue、提议 Plan、更新进度（这些是工人的活）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timezone
from typing import Optional

from mcp.server.fastmcp import FastMCP

from mcp_common import (
    API_BASE, _api_request, _current_sub, get_headers,
    PasswordMiddleware,
)

mcp = FastMCP("project-manager-mate")


# ── 连接 ────────────────────────────────────────────

@mcp.tool()
async def check_connection() -> str:
    """测试大副 MCP Server 与后端 API 的连接是否正常"""
    try:
        headers = await get_headers()
    except RuntimeError as e:
        return f"ERROR: {e}"
    from mcp_common import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/auth/me", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return f"Connected OK. Identity: {data.get('sub', '?')} (role={data.get('role', '?')}) [First Mate]"
        elif resp.status_code == 401:
            return "ERROR: Token invalid or expired (401). Will re-login on next call."
        else:
            return f"ERROR: API returned {resp.status_code}. Is the backend running?"


# ── 全局概览 ────────────────────────────────────────

@mcp.tool()
async def get_context() -> str:
    """获取项目全局概览：统计、紧急告警、待审批计划、活跃 Agent、最近活动。大副的核心工具，一眼掌握全局。"""
    resp = await _api_request("GET", f"{API_BASE}/dashboard")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    dash = resp.json()

    lines = ["=== 项目全局概览 ==="]

    issues = dash.get("issues", {})
    plans = dash.get("plans", {})
    servers = dash.get("servers", {})
    lines.append(f"Issues: {issues.get('total',0)} total | P0: {issues.get('p0',0)} | P1: {issues.get('p1',0)} | Open: {issues.get('open',0)} | In Progress: {issues.get('in_progress',0)} | Deferred: {issues.get('deferred',0)} | AI Agent: {issues.get('ai_agent',0)}")
    lines.append(f"Plans: {plans.get('total',0)} total | Pending Approval: {plans.get('pending_approval',0)} | Active: {plans.get('active',0)} | Abandoned: {plans.get('abandoned',0)}")

    alerts = []
    if issues.get("p0", 0) > 0:
        alerts.append(f"⚠️ {issues['p0']} 个 P0 紧急 Issue 需要立即处理")
    if plans.get("pending_approval", 0) > 0:
        alerts.append(f"📋 {plans['pending_approval']} 个 Plan 等待审批")
    if servers.get("offline", 0) > 0:
        alerts.append(f"🔴 {servers['offline']} 台服务器离线")
    unassigned_p0 = dash.get("unassigned_p0_issues", [])
    if unassigned_p0:
        alerts.append(f"🚨 {len(unassigned_p0)} 个 P0 Issue 无负责人！")
    if alerts:
        lines.append("")
        lines.append("=== 紧急告警 ===")
        lines.extend(alerts)

    pending_plans = dash.get("pending_plans", [])
    if pending_plans:
        lines.append("")
        lines.append("=== 待审批计划 ===")
        for p in pending_plans:
            desc_preview = f" — {p['description'][:80]}..." if p.get("description") and len(p["description"]) > 80 else (f" — {p['description']}" if p.get("description") else "")
            lines.append(f"  Plan #{p['id']}: {p['title']}{desc_preview} (by {p.get('proposed_by_name') or p.get('proposed_by','?')})")

    recent = dash.get("recent_activities", [])
    if recent:
        lines.append("")
        lines.append("=== 最近活动 ===")
        for a in recent[:10]:
            lines.append(f"  [{a['entity_type']}#{a['entity_id']}] {a['action']} by {a.get('actor','?')}")

    active_agents = dash.get("active_agents", [])
    if active_agents:
        lines.append("")
        lines.append("=== 活跃 Agent (1h) ===")
        for ag in active_agents:
            lines.append(f"  {ag['name']} (最近操作: {ag.get('last_action','?')})")

    agent_workload = dash.get("agent_workload", [])
    if agent_workload:
        lines.append("")
        lines.append("=== Agent 工作负载 ===")
        for w in agent_workload:
            lines.append(f"  {w['assignee']}: {w['total']} issues ({w['in_progress']} in_progress, {w['open']} open)")

    unassigned_p0 = dash.get("unassigned_p0_issues", [])
    if unassigned_p0:
        lines.append("")
        lines.append("=== 无负责人 P0 Issue ===")
        for iss in unassigned_p0:
            lines.append(f"  Issue #{iss['id']} {iss['title']} [{iss.get('status','?')}]")

    return "\n".join(lines)


# ── Plan 审批 ──────────────────────────────────────

@mcp.tool()
async def list_pending_plans(limit: int = 20) -> str:
    """查看所有待审批的 Plan 列表（含描述、提议者、创建时间）"""
    resp = await _api_request("GET", f"{API_BASE}/plans", params={"status": "pending_approval", "limit": limit})
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    items = resp.json()
    if not items:
        return "No pending plans. All clear!"
    lines = [f"Pending plans: {len(items)}"]
    for item in items:
        desc_preview = ""
        if item.get("description"):
            d = item["description"]
            desc_preview = f"\n    描述: {d[:120]}..." if len(d) > 120 else f"\n    描述: {d}"
        lines.append(f"  Plan #{item['id']} {item['title']} (by {item.get('proposed_by_name') or item.get('proposed_by','?')}){desc_preview}")
        lines.append(f"    创建: {item.get('created_at','?')}")
    return "\n".join(lines)


@mcp.tool()
async def get_plan_detail(plan_id: int) -> str:
    """查看 Plan 完整详情（含审批信息、拒绝原因、进度项列表），审批前务必先查看详情"""
    resp = await _api_request("GET", f"{API_BASE}/plans/{plan_id}")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    d = resp.json()
    lines = [
        f"Plan #{d['id']} [{d['status']}] {d['title']}",
        f"  提议者: {d.get('proposed_by_name') or d.get('proposed_by', '?')} | 项目: #{d.get('project_id', '?')}",
    ]
    if d.get('description'):
        lines.append(f"  描述: {d['description']}")
    if d.get('approved_by'):
        lines.append(f"  审批: by {d['approved_by']} at {d.get('approved_at', '?')}")
    if d.get('reject_reason'):
        lines.append(f"  拒绝原因: {d['reject_reason']}")
    lines.append(f"  创建: {d.get('created_at', '?')} | 更新: {d.get('updated_at', '?')}")
    items_resp = await _api_request("GET", f"{API_BASE}/plans/{plan_id}/items")
    if items_resp.status_code < 400:
        items = items_resp.json()
        if items:
            lines.append(f"  进度项 ({len(items)}):")
            for item in items[:10]:
                status_icon = "✅" if item.get("status") == "done" else "⬜"
                lines.append(f"    {status_icon} {item['title']} ({item.get('status', '?')})")
    return "\n".join(lines)


@mcp.tool()
async def approve_plan(plan_id: int) -> str:
    """审批通过 Plan。Plan 状态变为 active，提议 Agent 会收到通知。"""
    resp = await _api_request("POST", f"{API_BASE}/plans/{plan_id}/approve")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    d = resp.json()
    return f"Plan #{d['id']} APPROVED ✅\n  标题: {d['title']} | 状态: {d['status']} | 审批者: {d.get('approved_by', '?')} | 审批时间: {d.get('approved_at', '?')}"


@mcp.tool()
async def list_active_plans_progress() -> str:
    """查看所有活跃 Plan 的进度概览（完成百分比、待办项数），快速掌握执行情况。"""
    resp = await _api_request("GET", f"{API_BASE}/plans", params={"status": "active", "limit": 50})
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    plans = resp.json()
    if not plans:
        return "No active plans."
    lines = [f"Active plans: {len(plans)}"]
    for p in plans:
        items_resp = await _api_request("GET", f"{API_BASE}/plans/{p['id']}/items")
        if items_resp.status_code < 400:
            items = items_resp.json()
            total = len(items)
            done = sum(1 for i in items if i.get("status") == "done")
            pct = f"{done * 100 // total}%" if total > 0 else "N/A"
            lines.append(f"  Plan #{p['id']} {p['title']}: {done}/{total} done ({pct})")
        else:
            lines.append(f"  Plan #{p['id']} {p['title']}: (无法获取进度)")
    return "\n".join(lines)


@mcp.tool()
async def reject_plan(plan_id: int, reason: str = "") -> str:
    """拒绝 Plan，必须填写拒绝原因。提议 Agent 会收到通知和拒绝原因。"""
    if not reason:
        return "Error: 拒绝 Plan 必须填写原因，帮助 Agent 理解问题并改进"
    resp = await _api_request("POST", f"{API_BASE}/plans/{plan_id}/reject", json={"reason": reason})
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    d = resp.json()
    return f"Plan #{d['id']} REJECTED ❌\n  标题: {d['title']} | 状态: {d['status']} | 拒绝原因: {d.get('reject_reason', reason)}"


# ── Issue 管理 ──────────────────────────────────────

@mcp.tool()
async def list_issues(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    unassigned: bool = False,
    created_by: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "created_at_desc",
) -> str:
    """查询 Issue 列表。支持按状态/优先级/负责人/创建者筛选。unassigned=True 筛选无负责人 Issue。sort_by: created_at_desc/asc, updated_at_desc/asc, priority_asc/desc。"""
    params = {"limit": limit, "skip": offset, "sort_by": sort_by}
    if status:
        params["status"] = status
    if priority:
        params["priority"] = priority
    if assignee:
        params["assignee"] = assignee
    if unassigned:
        params["unassigned"] = "true"
    if created_by:
        params["created_by"] = created_by

    resp = await _api_request("GET", f"{API_BASE}/issues", params=params)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    items = data.get("items", [])
    if not items:
        return "No issues found."
    lines = [f"Total: {data['total']} issues"]
    for item in items:
        desc_preview = ""
        if item.get("description"):
            d = item["description"]
            desc_preview = f"\n    描述: {d[:80]}..." if len(d) > 80 else f"\n    描述: {d}"
        assignee_info = f"\n    负责人: {item['assignee']}" if item.get("assignee") else "\n    负责人: 未分配"
        by_info = f", by {item['created_by']}" if item.get('created_by') else ""
        lines.append(f"  #{item['id']} [{item['priority']}] {item['title']} ({item['status']}, source={item['source']}{by_info}){desc_preview}{assignee_info}")
    return "\n".join(lines)


@mcp.tool()
async def get_issue_detail(issue_id: int) -> str:
    """查看 Issue 完整详情（含评论列表、关联里程碑、推迟信息）"""
    resp = await _api_request("GET", f"{API_BASE}/issues/{issue_id}")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    d = resp.json()
    lines = [
        f"Issue #{d['id']} [{d['priority']}] {d['title']}",
        f"  状态: {d['status']} | 类型: {d.get('issue_type', '?')} | 来源: {d.get('source', '?')}",
        f"  创建者: {d.get('created_by', '?')} | 负责人: {d.get('assignee') or '未分配'}",
        f"  项目: #{d.get('project_id', '?')} | 里程碑: #{d.get('milestone_id') or '无'}",
    ]
    if d.get('labels'):
        lines.append(f"  标签: {d['labels']}")
    if d.get('description'):
        lines.append(f"  描述: {d['description']}")
    if d.get('deferred_to_milestone_id'):
        lines.append(f"  推迟到: milestone #{d['deferred_to_milestone_id']}")
        if d.get('deferred_reason'):
            lines.append(f"  推迟原因: {d['deferred_reason']}")
    lines.append(f"  创建: {d.get('created_at','?')} | 更新: {d.get('updated_at','?')}")

    comments_resp = await _api_request("GET", f"{API_BASE}/issues/{issue_id}/comments", params={"limit": 10})
    if comments_resp.status_code < 400:
        comments = comments_resp.json()
        if comments:
            lines.append(f"  评论 ({len(comments)}):")
            for c in comments[:5]:
                reply = f" ↩#{c['parent_id']}" if c.get("parent_id") else ""
                lines.append(f"    #{c['id']} [{c.get('author','?')}]{reply} {c['content'][:100]}")
    return "\n".join(lines)


@mcp.tool()
async def assign_issue(issue_id: int, assignee: str, auto_start: bool = True) -> str:
    """分配 Issue 给指定 Agent。auto_start=True 时自动将状态设为 in_progress（默认开启）。"""
    payload = {"assignee": assignee}
    if auto_start:
        payload["status"] = "in_progress"
    resp = await _api_request("PUT", f"{API_BASE}/issues/{issue_id}", json=payload)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    d = resp.json()
    status_note = " → in_progress" if auto_start else ""
    return f"Issue #{d['id']} assigned to {assignee}{status_note}\n  标题: {d['title']} | 状态: {d['status']} | 优先级: {d['priority']} | 负责人: {d.get('assignee') or '未分配'}"


@mcp.tool()
async def set_issue_priority(issue_id: int, priority: str) -> str:
    """调整 Issue 优先级: P0/P1/P2/P3"""
    resp = await _api_request("PUT", f"{API_BASE}/issues/{issue_id}", json={"priority": priority})
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    d = resp.json()
    return f"Issue #{d['id']} priority set to {priority}\n  标题: {d['title']} | 状态: {d['status']} | 优先级: {d['priority']}"


@mcp.tool()
async def update_issue_status(issue_id: int, status: str) -> str:
    """更新 Issue 状态: open/in_progress/review/deferred/closed/cancelled"""
    resp = await _api_request("PUT", f"{API_BASE}/issues/{issue_id}", json={"status": status})
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    d = resp.json()
    return f"Issue #{d['id']} status → {status}\n  标题: {d['title']} | 优先级: {d['priority']} | 负责人: {d.get('assignee') or '未分配'}"


@mcp.tool()
async def add_issue_comment(issue_id: int, content: str) -> str:
    """给 Issue 添加管理评论（如审批意见、指导说明），评论自动标记为 management 类型"""
    agent_name = await _current_sub()
    resp = await _api_request("POST", f"{API_BASE}/issues/{issue_id}/comments", json={"content": content, "author": agent_name, "comment_type": "management"})
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Comment #{data['id']} added to Issue #{issue_id} by {agent_name} (management)"


# ── 通知 ────────────────────────────────────────────

@mcp.tool()
async def check_notifications(unread_only: bool = False, limit: int = 10, since: str = "") -> str:
    """检查通知。since 可选，格式 ISO8601，只返回该时间之后的通知。"""
    params = {"limit": limit}
    if unread_only:
        params["unread_only"] = "true"
    if since:
        params["since"] = since
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


# ── Agent 活动 ──────────────────────────────────────

@mcp.tool()
async def get_agent_activities(agent_name: Optional[str] = None, limit: int = 20) -> str:
    """查看 Agent 操作历史。不指定 agent_name 则查看所有 Agent 的最近活动。"""
    params = {"limit": limit}
    if agent_name:
        params["actor"] = agent_name
    resp = await _api_request("GET", f"{API_BASE}/activity-logs", params=params)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    items = resp.json()
    if not items:
        return f"No recent activities{' for ' + agent_name if agent_name else ''}."
    who = agent_name or "all agents"
    lines = [f"Recent activities by {who} ({len(items)}):"]
    for a in items:
        ts = a.get("created_at", "?")
        if ts and len(ts) > 19:
            ts = ts[:19]
        detail = ""
        if a.get("new_value"):
            nv = str(a["new_value"])
            if len(nv) > 60:
                nv = nv[:60] + "..."
            detail = f" → {nv}"
        lines.append(f"  [{ts}] {a['entity_type']}#{a['entity_id']} {a['action']} by {a.get('actor','?')}{detail}")
    return "\n".join(lines)


# ── 项目 & 里程碑 ──────────────────────────────────

@mcp.tool()
async def list_projects() -> str:
    """列出所有项目（含统计）"""
    resp = await _api_request("GET", f"{API_BASE}/projects")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    items = resp.json()
    if not items:
        return "No projects found."
    lines = [f"Total: {len(items)} projects"]
    for item in items:
        status = item.get("status", "?")
        stats = f" ({item.get('issue_count',0)} issues, {item.get('plan_count',0)} plans, {item.get('milestone_count',0)} milestones)"
        owner = f" owner={item['owner']}" if item.get('owner') else ""
        lines.append(f"  #{item['id']} [{status}] {item['name']} (slug={item['slug']}){stats}{owner}")
    return "\n".join(lines)


@mcp.tool()
async def list_milestones(project_id: Optional[int] = None) -> str:
    """查看里程碑列表（含统计）"""
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
        stats = f" (issues: {item.get('issue_count',0)}, open: {item.get('open_count',0)}, closed: {item.get('closed_count',0)}, deferred: {item.get('deferred_count',0)})"
        phase = f" [{item['phase']}]" if item.get('phase') else ""
        lines.append(f"  #{item['id']} {item['title']}{phase} — {item.get('status','?')}{stats}")
    return "\n".join(lines)


# ── 启动 ────────────────────────────────────────────

MCP_PORT = int(os.environ.get("MCP_PORT", "9001"))
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "streamable-http")


def main():
    if MCP_TRANSPORT == "streamable-http":
        mcp.settings.host = MCP_HOST
        mcp.settings.port = MCP_PORT
        app = PasswordMiddleware(mcp.streamable_http_app())
        import uvicorn
        uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
    elif MCP_TRANSPORT == "sse":
        mcp.settings.host = MCP_HOST
        mcp.settings.port = MCP_PORT
        app = PasswordMiddleware(mcp.sse_app())
        import uvicorn
        uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
