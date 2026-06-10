"""Tester tools module

Internal Tester role tools for quality assurance.
"""
from mcp_common import API_BASE, _api_request, _current_sub


def register_tools(mcp, require_role, safe_tool):
    """Register Tester role tools"""

# ═══════════════════════════════════════════════════════

@mcp.tool()
@require_role("tester", "admin")
async def report_bug(
    title: str,
    description: str = "",
    priority: str = "P1",
    project_id: Optional[int] = None,
    labels: str = "",
) -> str:
    """提交 Bug 报告。source 自动标记为 human（代表真实用户反馈）。priority: P0(紧急)/P1(高)/P2(中)/P3(低)，默认 P1。"""
    tester_name = await _current_sub()
    payload = {
        "title": title,
        "description": description,
        "priority": priority,
        "source": "user",
        "issue_type": "bug",
        "created_by": tester_name,
    }
    if project_id:
        payload["project_id"] = project_id
    if labels:
        payload["labels"] = labels
    resp = await _api_request("POST", f"{API_BASE}/issues", json=payload)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Bug #{data['id']} reported: [{data['priority']}] {data['title']}\n  status={data['status']} | source={data['source']} | created_by={data.get('created_by', tester_name)}"


@mcp.tool()
@require_role("tester", "admin")
async def request_feature(
    title: str,
    description: str = "",
    priority: str = "P2",
    project_id: Optional[int] = None,
    labels: str = "",
) -> str:
    """提交功能需求。source 自动标记为 human。priority 默认 P2。"""
    tester_name = await _current_sub()
    payload = {
        "title": title,
        "description": description,
        "priority": priority,
        "source": "user",
        "issue_type": "feature",
        "created_by": tester_name,
    }
    if project_id:
        payload["project_id"] = project_id
    if labels:
        payload["labels"] = labels
    resp = await _api_request("POST", f"{API_BASE}/issues", json=payload)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"Feature request #{data['id']} submitted: [{data['priority']}] {data['title']}\n  status={data['status']} | source={data['source']} | created_by={data.get('created_by', tester_name)}"


@mcp.tool()
@require_role("tester", "admin")
async def verify_issue(issue_id: int, comment: str = "") -> str:
    """验证 Issue 修复通过，将状态从 review 改为 closed。可选添加验证评论。"""
    tester_name = await _current_sub()
    resp = await _api_request("GET", f"{API_BASE}/issues/{issue_id}")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    issue = resp.json()
    if issue["status"] != "review":
        return f"Issue #{issue_id} 当前状态为 {issue['status']}，只有 review 状态的 Issue 才能验证"
    if issue.get("created_by") != tester_name:
        return f"Issue #{issue_id} 不是你提交的（created_by={issue.get('created_by', '?')}），只有提交者才能验证"

    update_resp = await _api_request("PUT", f"{API_BASE}/issues/{issue_id}", json={"status": "closed"})
    if update_resp.status_code >= 400:
        return f"Error: {update_resp.status_code} - {update_resp.text}"
    d = update_resp.json()

    if comment:
        await _api_request("POST", f"{API_BASE}/issues/{issue_id}/comments", json={"content": f"✅ 验证通过: {comment}", "author": tester_name, "comment_type": "testing"})

    return f"Issue #{d['id']} VERIFIED ✅ → closed\n  标题: {d['title']} | 优先级: {d['priority']}"


@mcp.tool()
@require_role("tester", "admin")
async def reject_fix(issue_id: int, reason: str) -> str:
    """验证不通过，将 Issue 从 review 退回到 in_progress。必须填写退回原因。"""
    if not reason:
        return "Error: 退回修复必须填写原因，帮助开发者理解问题"
    tester_name = await _current_sub()
    resp = await _api_request("GET", f"{API_BASE}/issues/{issue_id}")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    issue = resp.json()
    if issue["status"] != "review":
        return f"Issue #{issue_id} 当前状态为 {issue['status']}，只有 review 状态的 Issue 才能退回"
    if issue.get("created_by") != tester_name:
        return f"Issue #{issue_id} 不是你提交的（created_by={issue.get('created_by', '?')}），只有提交者才能退回"

    update_resp = await _api_request("PUT", f"{API_BASE}/issues/{issue_id}", json={"status": "in_progress"})
    if update_resp.status_code >= 400:
        return f"Error: {update_resp.status_code} - {update_resp.text}"
    d = update_resp.json()

    await _api_request("POST", f"{API_BASE}/issues/{issue_id}/comments", json={"content": f"❌ 验证不通过: {reason}", "author": tester_name, "comment_type": "testing"})

    return f"Issue #{d['id']} REJECTED ❌ → in_progress\n  标题: {d['title']} | 退回原因: {reason}"


@mcp.tool()
@require_role("tester", "admin")
async def list_my_issues(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "updated_at_desc",
) -> str:
    """查看我提交的 Issue 列表。默认按更新时间倒序。"""
    tester_name = await _current_sub()
    params = {"created_by": tester_name, "limit": limit, "skip": offset, "sort_by": sort_by}
    if status:
        params["status"] = status
    if priority:
        params["priority"] = priority
    resp = await _api_request("GET", f"{API_BASE}/issues", params=params)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    items = data.get("items", [])
    if not items:
        return "No issues found."
    lines = [f"Total: {data['total']} issues (by {tester_name})"]
    for item in items:
        desc_preview = ""
        if item.get("description"):
            d = item["description"]
            desc_preview = f"\n    描述: {d[:80]}..." if len(d) > 80 else f"\n    描述: {d}"
        assignee_info = f"\n    负责人: {item['assignee']}" if item.get("assignee") else "\n    负责人: 未分配"
        type_info = f" type={item.get('issue_type', '?')}"
        lines.append(f"  #{item['id']} [{item['priority']}] {item['title']} ({item['status']}{type_info}, source={item['source']}){desc_preview}{assignee_info}")
    return "\n".join(lines)


@mcp.tool()
@require_role("tester", "admin")
async def list_all_issues(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    unassigned: bool = False,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "updated_at_desc",
) -> str:
    """查看项目中所有 Issue 列表（只读）。unassigned=True 筛选无负责人 Issue。"""
    params = {"limit": limit, "skip": offset, "sort_by": sort_by}
    if status:
        params["status"] = status
    if priority:
        params["priority"] = priority
    if unassigned:
        params["unassigned"] = "true"
    resp = await _api_request("GET", f"{API_BASE}/issues", params=params)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    items = data.get("items", [])
    if not items:
        return "No issues found."
    lines = [f"Total: {data['total']} issues"]
    for item in items:
        assignee_info = f" → {item['assignee']}" if item.get("assignee") else " (未分配)"
        by_info = f" by {item.get('created_by', '?')}" if item.get("created_by") else ""
        lines.append(f"  #{item['id']} [{item['priority']}] {item['title']} ({item['status']}{assignee_info}{by_info})")
    return "\n".join(lines)


@mcp.tool()
@require_role("tester", "admin")
async def add_comment(
    issue_id: int,
    content: str,
    comment_type: str = "testing",
) -> str:
    """给 Issue 添加测试评论（如复现步骤、测试环境信息）。

    Args:
        issue_id: Issue ID
        content: 评论内容
        comment_type: 评论类型，可选 normal, testing, handover。默认 testing。
    """
    tester_name = await _current_sub()
    resp = await _api_request("POST", f"{API_BASE}/issues/{issue_id}/comments", json={"content": content, "author": tester_name, "comment_type": comment_type})
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    type_info = f" [{comment_type}]" if comment_type != "testing" else ""
    return f"Comment #{data['id']}{type_info} added to Issue #{issue_id} by {tester_name} (testing)"


# ═══════════════════════════════════════════════════════
#  Registrar Only
