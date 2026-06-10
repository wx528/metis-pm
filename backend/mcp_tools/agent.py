"""Agent tools module

Agent role tools for Issue/Plan/Workflow operations.
"""
from datetime import datetime, timezone
from typing import Optional

from mcp_common import API_BASE, _api_request, _current_sub


def register_tools(mcp, require_role, safe_tool):
    """Register Agent role tools"""

# ═══════════════════════════════════════════════════════

@mcp.tool()
@require_role("agent", "admin")
async def get_my_recent_actions(limit: int = 20) -> str:
    """查看当前 Agent 的最近操作历史。帮助回忆"我之前干了什么"，避免重复操作。"""
    agent_name = await _current_sub()
    resp = await _api_request("GET", f"{API_BASE}/activity-logs", params={"actor": agent_name, "limit": limit})
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    items = resp.json()
    if not items:
        return f"No recent actions found for {agent_name}."
    lines = [f"Recent actions by {agent_name} ({len(items)})"]
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
        lines.append(f"  [{ts}] {a['entity_type']}#{a['entity_id']} {a['action']}{detail}")
    return "\n".join(lines)


@mcp.tool()
@require_role("agent", "admin")
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


@mcp.tool()
@require_role("agent", "admin")
async def create_issue(
    title: str,
    description: str = "",
    priority: str = "P2",
    issue_type: str = "task",
    project_id: Optional[int] = None,
    milestone_id: Optional[int] = None,
    labels: str = "",
) -> str:
    """创建 issue，source 自动标记为 ai_agent"""
    agent_name = await _current_sub()
    payload = {
        "title": title,
        "description": description,
        "priority": priority,
        "issue_type": issue_type,
        "source": "ai_agent",
        "created_by": agent_name,
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
    desc_info = f"\n  描述: {data['description']}" if data.get('description') else ""
    labels_info = f"\n  标签: {data['labels']}" if data.get('labels') else ""
    assignee_info = f"\n  负责人: {data['assignee']}" if data.get('assignee') else ""
    milestone_info = f"\n  里程碑: #{data['milestone_id']}" if data.get('milestone_id') else ""
    return f"Issue #{data['id']} created: [{data['priority']}] {data['title']} (status={data['status']}, source={data['source']}){project_info}{desc_info}{labels_info}{assignee_info}{milestone_info}\n  created_at={data.get('created_at','?')}"


@mcp.tool()
@require_role("agent", "admin")
async def claim_issue(issue_id: int) -> str:
    """认领 Issue：将 Issue 分配给自己并设为 in_progress。避免多 Agent 重复处理。"""
    agent_name = await _current_sub()
    resp = await _api_request("PUT", f"{API_BASE}/issues/{issue_id}", json={"assignee": agent_name, "status": "in_progress"})
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Issue #{data['id']} claimed by {agent_name}\n  标题: {data['title']} | 状态: {data['status']} | 负责人: {data.get('assignee', '?')} | updated_at={data.get('updated_at', '?')}"


@mcp.tool()
@require_role("agent", "admin")
async def update_issue(
    issue_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    assignee: Optional[str] = None,
    labels: Optional[str] = None,
    milestone_id: Optional[int] = None,
    issue_type: Optional[str] = None,
) -> str:
    """更新 Issue 的标题、描述、负责人、标签、里程碑、类型等字段。只传需要修改的字段，未传的字段保持不变。"""
    payload = {}
    if title is not None:
        payload["title"] = title
    if description is not None:
        payload["description"] = description
    if assignee is not None:
        payload["assignee"] = assignee
    if labels is not None:
        payload["labels"] = labels
    if milestone_id is not None:
        payload["milestone_id"] = milestone_id
    if issue_type is not None:
        payload["issue_type"] = issue_type
    if not payload:
        return "Error: 至少提供一个要修改的字段"
    resp = await _api_request("PUT", f"{API_BASE}/issues/{issue_id}", json=payload)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    d = resp.json()
    changes = ", ".join(f"{k}={v}" for k, v in payload.items())
    return f"Issue #{d['id']} updated ({changes})\n  标题: {d['title']} | 状态: {d['status']} | 优先级: {d['priority']} | 负责人: {d.get('assignee') or '未分配'} | updated_at={d.get('updated_at','?')}"


@mcp.tool()
@require_role("agent", "admin")
async def update_issue_priority(issue_id: int, priority: str) -> str:
    """更新 issue 优先级: P0/P1/P2/P3"""
    resp = await _api_request("PUT", f"{API_BASE}/issues/{issue_id}", json={"priority": priority})
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Issue #{data['id']} updated\n  标题: {data['title']} | 状态: {data['status']} | 优先级: {data['priority']} | updated_at={data.get('updated_at','?')}"


@mcp.tool()
@require_role("agent", "mate", "admin")
async def update_issue_status(issue_id: int, status: str) -> str:
    """更新 issue 状态: open/in_progress/review/deferred/closed/cancelled"""
    resp = await _api_request("PUT", f"{API_BASE}/issues/{issue_id}", json={"status": status})
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Issue #{data['id']} updated\n  标题: {data['title']} | 状态: {data['status']} | 优先级: {data['priority']} | updated_at={data.get('updated_at','?')}"


@mcp.tool()
@require_role("agent", "admin")
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
@require_role("agent", "admin")
async def undefer_issue(issue_id: int) -> str:
    """取消暂缓，将 deferred issue 恢复为 open 状态"""
    resp = await _api_request("POST", f"{API_BASE}/issues/{issue_id}/undefer")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Issue #{data['id']} undeferred → {data['status']}\n  标题: {data['title']} | 优先级: {data['priority']}"


@mcp.tool()
@require_role("agent", "admin")
async def propose_plan(title: str, description: str = "", project_id: Optional[int] = None) -> str:
    """提议一个新计划（状态为 pending_approval，等待用户审批）"""
    agent_name = await _current_sub()
    payload = {
        "title": title,
        "description": description,
        "proposed_by": "ai_agent",
        "proposed_by_name": agent_name,
        "status": "pending_approval",
    }
    if project_id:
        payload["project_id"] = project_id
    resp = await _api_request("POST", f"{API_BASE}/plans", json=payload)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    desc_info = f"\n  描述: {data['description']}" if data.get('description') else ""
    project_info = f"\n  project_id={data['project_id']}" if data.get('project_id') else ""
    return f"Plan #{data['id']} proposed: {data['title']} (status={data['status']}, waiting for approval){desc_info}{project_info}\n  created_at={data.get('created_at','?')}"


@mcp.tool()
@require_role("agent", "admin")
async def revise_plan(plan_id: int, title: Optional[str] = None, description: Optional[str] = None) -> str:
    """修改被拒绝的 Plan 并重新提交审批。只有 abandoned(rejected) 状态的 Plan 才能修改。"""
    plan_resp = await _api_request("GET", f"{API_BASE}/plans/{plan_id}")
    if plan_resp.status_code >= 400:
        return f"Error: Plan #{plan_id} not found ({plan_resp.status_code})"
    plan_data = plan_resp.json()
    plan_status = plan_data.get("status", "")
    if plan_status != "abandoned":
        return f"Error: Plan #{plan_id} 状态为 '{plan_status}'，无法修改。只有被拒绝(abandoned)的 Plan 才能修改重新提交。"

    update_payload = {"status": "pending_approval"}
    if title:
        update_payload["title"] = title
    if description:
        update_payload["description"] = description

    resp = await _api_request("PUT", f"{API_BASE}/plans/{plan_id}", json=update_payload)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Plan #{plan_id} 已修改并重新提交审批 (status={data['status']})"


@mcp.tool()
@require_role("agent", "admin")
async def update_plan_progress(plan_id: int, item_title: str, status: str = "done") -> str:
    """更新计划项进度。如果 plan_item 不存在则自动创建。仅 approved(active) 状态的 Plan 才能更新进度。"""
    agent_name = await _current_sub()

    plan_resp = await _api_request("GET", f"{API_BASE}/plans/{plan_id}")
    if plan_resp.status_code >= 400:
        return f"Error: Plan #{plan_id} not found ({plan_resp.status_code})"
    plan_data = plan_resp.json()
    plan_status = plan_data.get("status", "")
    if plan_status not in ("active", "completed"):
        return f"Error: Plan #{plan_id} 状态为 '{plan_status}'，无法更新进度。只有 approved(active) 或 completed 状态的 Plan 才能更新进度。"

    resp = await _api_request("GET", f"{API_BASE}/plans/{plan_id}/items")
    if resp.status_code >= 400:
        return f"Error getting plan items: {resp.status_code}"
    items = resp.json()

    target_item = None
    for item in items:
        if item["title"] == item_title:
            target_item = item
            break

    if target_item:
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
        resp = await _api_request(
            "POST",
            f"{API_BASE}/plans/{plan_id}/items",
            json={"title": item_title, "status": status},
        )
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        return f"PlanItem '{item_title}' created with status {status}"


@mcp.tool()
@require_role("agent", "admin")
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


@mcp.tool()
@require_role("agent", "admin")
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
@require_role("agent", "admin")
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


@mcp.tool()
@require_role("agent", "admin")
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
@require_role("agent", "admin")
async def trigger_workflow(workflow_id: int) -> str:
    """手动触发工作流"""
    resp = await _api_request("POST", f"{API_BASE}/workflows/{workflow_id}/trigger")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Workflow triggered! Run #{data['id']} (status={data['status']})"


@mcp.tool()
@require_role("agent", "admin")
async def set_agent_memory(key: str, value: str) -> str:
    """保存 Agent 记忆（持久化，跨会话保留）。key 相同则更新。用于记住工作状态、用户偏好、待办事项等。"""
    resp = await _api_request("POST", f"{API_BASE}/agent-memories", json={"key": key, "value": value})
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Memory saved: {data['key']} = {data['value'][:100]}{'...' if len(data.get('value', '')) > 100 else ''}"


@mcp.tool()
@require_role("agent", "admin")
async def get_agent_memory(key_prefix: str = "", limit: int = 50) -> str:
    """查询 Agent 记忆。key_prefix 可选，按前缀筛选。返回当前 Agent 保存的所有记忆。"""
    params = {"limit": limit}
    if key_prefix:
        params["key_prefix"] = key_prefix
    resp = await _api_request("GET", f"{API_BASE}/agent-memories", params=params)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    items = resp.json()
    if not items:
        return "No memories found."
    lines = [f"Total: {len(items)} memories"]
    for item in items:
        val = item.get('value', '') or ''
        val_preview = val[:80] + "..." if len(val) > 80 else val
        lines.append(f"  [{item['key']}] = {val_preview}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
