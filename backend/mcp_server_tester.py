"""
Project Manager MCP Server - Tester (测试者)
内测客户角色：提交 Bug/需求、验证修复、关闭/退回 Issue

=== Streamable HTTP 模式配置 ===
{
  "mcpServers": {
    "project-manager-tester": {
      "url": "http://localhost:9002/mcp",
      "headers": {
        "X-PM-Password": "CHANGE-ME"
      }
    }
  }
}

测试者角色职责：
  - 提交 Bug / 功能需求（source=human，代表真实用户反馈）
  - 查看自己提交的 Issue 进度
  - 验证修复：将 review 状态的 Issue 关闭（确认已解决）
  - 退回 Issue：验证不通过时退回 in_progress
  - 添加测试评论（comment_type=testing）

测试者不负责：创建 Plan、审批 Plan、分配 Issue、调整优先级（这些是工人/大副的活）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from typing import Optional

from mcp.server.fastmcp import FastMCP

from mcp_common import (
    API_BASE, _api_request, _current_sub, get_headers,
    PasswordMiddleware,
)

mcp = FastMCP("project-manager-tester")


# ── 连接 ────────────────────────────────────────────

@mcp.tool()
async def check_connection() -> str:
    """测试测试者 MCP Server 与后端 API 的连接是否正常"""
    try:
        headers = await get_headers()
    except RuntimeError as e:
        return f"ERROR: {e}"
    from mcp_common import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/auth/me", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return f"Connected OK. Identity: {data.get('sub', '?')} (role={data.get('role', '?')}) [Tester]"
        elif resp.status_code == 401:
            return "ERROR: Token invalid or expired (401). Will re-login on next call."
        else:
            return f"ERROR: API returned {resp.status_code}. Is the backend running?"


# ── 全局概览 ────────────────────────────────────────

@mcp.tool()
async def get_context() -> str:
    """获取测试者视角的项目概览：我的 Issue 统计、待验证 Issue、最近活动。"""
    tester_name = await _current_sub()

    resp = await _api_request("GET", f"{API_BASE}/dashboard")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    dash = resp.json()

    lines = ["=== 测试者概览 ==="]

    issues = dash.get("issues", {})
    plans = dash.get("plans", {})
    lines.append(f"项目 Issues: {issues.get('total',0)} total | P0: {issues.get('p0',0)} | P1: {issues.get('p1',0)} | Open: {issues.get('open',0)} | In Progress: {issues.get('in_progress',0)} | Review: {issues.get('review',0)}")
    lines.append(f"项目 Plans: {plans.get('total',0)} total | Active: {plans.get('active',0)}")

    my_issues_resp = await _api_request("GET", f"{API_BASE}/issues", params={"created_by": tester_name, "limit": 50})
    if my_issues_resp.status_code < 400:
        my_data = my_issues_resp.json()
        my_total = my_data.get("total", 0)
        my_items = my_data.get("items", [])
        my_open = sum(1 for i in my_items if i["status"] in ("open", "in_progress"))
        my_review = sum(1 for i in my_items if i["status"] == "review")
        my_closed = sum(1 for i in my_items if i["status"] == "closed")
        lines.append(f"我提交的: {my_total} total | 待处理: {my_open} | 待验证: {my_review} | 已关闭: {my_closed}")
    else:
        lines.append("我提交的: (无法获取)")

    alerts = []
    unassigned_p0 = dash.get("unassigned_p0_issues", [])
    if unassigned_p0:
        alerts.append(f"🚨 {len(unassigned_p0)} 个 P0 Issue 无负责人")
    if issues.get("p0", 0) > 0:
        alerts.append(f"⚠️ {issues['p0']} 个 P0 紧急 Issue")
    if alerts:
        lines.append("")
        lines.append("=== 告警 ===")
        lines.extend(alerts)

    review_resp = await _api_request("GET", f"{API_BASE}/issues", params={"status": "review", "created_by": tester_name, "limit": 10})
    if review_resp.status_code < 400:
        review_data = review_resp.json()
        review_items = review_data.get("items", [])
        if review_items:
            lines.append("")
            lines.append("=== 待验证 Issue（等待我确认）===")
            for i in review_items:
                lines.append(f"  Issue #{i['id']} [{i['priority']}] {i['title']} (assignee={i.get('assignee') or '未分配'})")

    return "\n".join(lines)


# ── 提交 Bug/需求 ──────────────────────────────────

@mcp.tool()
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


# ── 验证 & 退回 ────────────────────────────────────

@mcp.tool()
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


# ── 查看 Issue ─────────────────────────────────────

@mcp.tool()
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
async def get_issue_detail(issue_id: int) -> str:
    """查看 Issue 完整详情（含评论列表、状态历史）"""
    resp = await _api_request("GET", f"{API_BASE}/issues/{issue_id}")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    d = resp.json()
    lines = [
        f"Issue #{d['id']} [{d['priority']}] [{d['status']}] {d['title']}",
        f"  类型: {d.get('issue_type', '?')} | 来源: {d.get('source', '?')} | 创建者: {d.get('created_by', '?')}",
        f"  负责人: {d.get('assignee') or '未分配'} | 里程碑: #{d.get('milestone_id', '?')}",
    ]
    if d.get('description'):
        lines.append(f"  描述: {d['description'][:300]}")
    if d.get('labels'):
        lines.append(f"  标签: {d['labels']}")
    if d.get('deferred_to_milestone_id'):
        lines.append(f"  推迟到: Milestone #{d['deferred_to_milestone_id']} 原因: {d.get('deferred_reason', '无')}")
    lines.append(f"  创建: {d.get('created_at', '?')} | 更新: {d.get('updated_at', '?')}")
    if d.get('closed_at'):
        lines.append(f"  关闭: {d['closed_at']}")

    comments = d.get("comments", [])
    if comments:
        lines.append(f"  评论 ({len(comments)}):")
        for c in comments[:10]:
            ctype = f" [{c.get('comment_type', 'normal')}]" if c.get('comment_type', 'normal') != 'normal' else ""
            lines.append(f"    {c.get('author', '?')}{ctype}: {c['content'][:100]}")
    return "\n".join(lines)


@mcp.tool()
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


# ── 评论 ────────────────────────────────────────────

@mcp.tool()
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


# ── 通知 ────────────────────────────────────────────

@mcp.tool()
async def check_notifications(unread_only: bool = False, limit: int = 10, since: str = "") -> str:
    """检查通知。since 可选，格式 ISO8601。"""
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


_HANDOVER_TEMPLATES = {
    "dev_complete": """## 交接: Issue 开发完成

### 改动范围
- 文件:
- 涉及接口:

### 测试情况
- [ ] 单元测试通过
- [ ] 集成测试通过

### 已知问题/注意点
-

### 下一步
- 请 @mate 审查代码
- 或请 @tester 执行集成测试
""",
    "review_feedback": """## 审查反馈: Issue

### 通过项
-

### 待修复
- [ ]

### 优先级
- 建议修复后合并，不阻塞
- 或 必须修复，阻塞发布
""",
    "test_report": """## 测试报告: Issue

### 测试环境
- 分支:
- 数据库:

### 结果
- [ ] 功能正常
- [ ] 发现 Bug（见下方）

### Bug 详情
- 步骤:
- 预期:
- 实际:
- 建议: 修复后重新 @tester 验证
""",
}


@mcp.tool()
async def notify_role(
    target_role: str,
    title: str,
    body: str = "",
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
) -> str:
    """给指定角色发送通知。

    Args:
        target_role: 目标角色，可选值: agent, mate, tester, registrar, admin
        title: 通知标题
        body: 通知正文
        entity_type: 关联实体类型，如 issue, plan
        entity_id: 关联实体 ID

    Returns:
        发送结果摘要
    """
    payload = {
        "recipient": target_role,
        "type": "role_notification",
        "title": title,
        "body": body,
    }
    if entity_type is not None:
        payload["entity_type"] = entity_type
    if entity_id is not None:
        payload["entity_id"] = entity_id

    resp = await _api_request("POST", f"{API_BASE}/notifications", json=payload)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    return f"通知已发送给角色 '{target_role}': {title} (通知ID: {data.get('id', '?')})"


@mcp.tool()
async def get_handover_template(template_name: str) -> str:
    """获取交接评论模板。

    Args:
        template_name: 模板名称，可选值: dev_complete（开发完成）, review_feedback（审查反馈）, test_report（测试报告）

    Returns:
        Markdown 格式的模板内容
    """
    tmpl = _HANDOVER_TEMPLATES.get(template_name)
    if not tmpl:
        available = ", ".join(_HANDOVER_TEMPLATES.keys())
        return f"错误: 未知模板 '{template_name}'。可用模板: {available}"
    return tmpl


# ── 项目 & 里程碑 ──────────────────────────────────

@mcp.tool()
async def list_projects() -> str:
    """列出所有项目（只读）"""
    resp = await _api_request("GET", f"{API_BASE}/projects")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    items = resp.json()
    if not items:
        return "No projects found."
    lines = [f"Total: {len(items)} projects"]
    for item in items:
        status = item.get("status", "?")
        stats = f" ({item.get('issue_count',0)} issues, {item.get('plan_count',0)} plans)"
        lines.append(f"  #{item['id']} [{status}] {item['name']}{stats}")
    return "\n".join(lines)


@mcp.tool()
async def list_milestones(project_id: Optional[int] = None) -> str:
    """查看里程碑列表（只读）"""
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
        stats = f" (total: {item.get('total_issues',0)}, open: {item.get('open_issues',0)}, closed: {item.get('closed_issues',0)})"
        phase = f" [{item['phase']}]" if item.get('phase') else ""
        lines.append(f"  #{item['id']} {item['title']}{phase} — {item.get('status','?')}{stats}")
    return "\n".join(lines)


# ── 启动 ────────────────────────────────────────────

MCP_PORT = int(os.environ.get("MCP_PORT", "9002"))
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
