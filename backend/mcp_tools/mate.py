"""Mate tools module

First Mate role tools for oversight and coordination.
"""
from typing import Optional

from mcp_common import API_BASE, _api_request, _current_sub


def register_tools(mcp, require_role, safe_tool):
    """Register tools"""
    # ═══════════════════════════════════════════════════════

    @mcp.tool()
    @require_role("mate", "admin")
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
            lines.append(f"  Plan #{item['id']} {item['title']} (by {item.get('proposed_by','?')}){desc_preview}")
            lines.append(f"    创建: {item.get('created_at','?')}")
        return "\n".join(lines)


    @mcp.tool()
    @require_role("mate", "admin")
    async def approve_plan(plan_id: int) -> str:
        """审批通过 Plan。Plan 状态变为 active，提议 Agent 会收到通知。"""
        resp = await _api_request("POST", f"{API_BASE}/plans/{plan_id}/approve")
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        d = resp.json()
        return f"Plan #{d['id']} APPROVED ✅\n  标题: {d['title']} | 状态: {d['status']} | 审批者: {d.get('approved_by', '?')} | 审批时间: {d.get('approved_at', '?')}"


    @mcp.tool()
    @require_role("mate", "admin")
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
    @require_role("mate", "admin")
    async def reject_plan(plan_id: int, reason: str = "") -> str:
        """拒绝 Plan，必须填写拒绝原因。提议 Agent 会收到通知和拒绝原因。"""
        if not reason:
            return "Error: 拒绝 Plan 必须填写原因，帮助 Agent 理解问题并改进"
        resp = await _api_request("POST", f"{API_BASE}/plans/{plan_id}/reject", json={"reason": reason})
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        d = resp.json()
        return f"Plan #{d['id']} REJECTED ❌\n  标题: {d['title']} | 状态: {d['status']} | 拒绝原因: {d.get('reject_reason', reason)}"


    @mcp.tool()
    @require_role("mate", "admin")
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
    @require_role("mate", "admin")
    async def set_issue_priority(issue_id: int, priority: str) -> str:
        """调整 Issue 优先级: P0/P1/P2/P3"""
        resp = await _api_request("PUT", f"{API_BASE}/issues/{issue_id}", json={"priority": priority})
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        d = resp.json()
        return f"Issue #{d['id']} priority set to {priority}\n  标题: {d['title']} | 状态: {d['status']} | 优先级: {d['priority']}"


    @mcp.tool()
    @require_role("mate", "admin")
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


    # ═══════════════════════════════════════════════════════
    #  Tester Only
