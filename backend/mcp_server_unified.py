"""
Project Manager MCP Server - Unified
Combines all roles: agent, mate, tester, registrar

=== Streamable HTTP 模式配置 ===
{
  "mcpServers": {
    "project-manager": {
      "url": "http://localhost:9000/mcp",
      "headers": {
        "X-PM-Password": "your-password"
      }
    }
  }
}

角色通过 AGENT_PASSWORDS 环境变量解析：identity:password,...
identity 包含 mate/tester/registrar 关键词则对应角色，否则为 agent
"""
import functools
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timezone
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

from mcp_common import (
    API_BASE, _api_request, _current_sub, get_headers,
    PasswordMiddleware, AGENT_PASSWORD, _get_password,
    _token_cache, _cache_key,
)

mcp = FastMCP("project-manager")

ROLES = {"agent", "mate", "tester", "registrar", "admin"}


def get_role_by_password(password: str) -> str:
    passwords = os.environ.get("AGENT_PASSWORDS", "")
    for entry in passwords.split(","):
        if ":" not in entry:
            continue
        identity, pwd = entry.strip().split(":", 1)
        if pwd == password:
            identity_lower = identity.lower()
            if "mate" in identity_lower:
                return "mate"
            if "tester" in identity_lower:
                return "tester"
            if "registrar" in identity_lower:
                return "registrar"
            return "agent"
    return "unknown"


async def _current_role() -> str:
    pwd = _get_password()
    return get_role_by_password(pwd)


def require_role(*roles):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            role = await _current_role()
            if role not in roles:
                return f"❌ 权限拒绝：需要角色 {list(roles)}，当前为 '{role}'"
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════
#  共享工具 / 常量
# ═══════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════
#  所有角色可用 (All Roles)
# ═══════════════════════════════════════════════════════

@mcp.tool()
@require_role("agent", "mate", "tester", "registrar", "admin")
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


@mcp.tool()
@require_role("agent", "mate", "tester", "registrar", "admin")
async def get_context(project_id: Optional[int] = None) -> str:
    """【首选入口】获取全局态势感知：一次调用返回项目概览、紧急告警、待审批计划、最近活动、我的状态。建议每次会话开始时首先调用此工具，替代多次 list 调用。"""
    lines = []
    agent_name = await _current_sub()

    params = {}
    if project_id:
        params["project_id"] = project_id
    resp = await _api_request("GET", f"{API_BASE}/dashboard", params=params)
    if resp.status_code >= 400:
        return f"Error fetching dashboard: {resp.status_code} - {resp.text}"
    dash = resp.json()

    issues = dash.get("issues", {})
    plans = dash.get("plans", {})
    servers = dash.get("servers", {})

    lines.append("=== 全局概览 ===")
    lines.append(f"Issues: {issues.get('total',0)} total | P0: {issues.get('p0',0)} | P1: {issues.get('p1',0)} | Open: {issues.get('open',0)} | In Progress: {issues.get('in_progress',0)} | Deferred: {issues.get('deferred',0)} | AI Agent: {issues.get('ai_agent',0)}")
    lines.append(f"Plans: {plans.get('total',0)} total | Pending Approval: {plans.get('pending_approval',0)} | Active: {plans.get('active',0)}")
    lines.append(f"Servers: {servers.get('total',0)} total | Active: {servers.get('active',0)} | Maintenance: {servers.get('maintenance',0)} | Offline: {servers.get('offline',0)}")

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
    else:
        lines.append("")
        lines.append("=== 紧急告警 ===")
        lines.append("无")

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

    recent_issues = dash.get("recent_issues", [])
    if recent_issues:
        lines.append("")
        lines.append("=== 最近 Issue ===")
        for i in recent_issues[:5]:
            lines.append(f"  Issue #{i['id']} [{i['priority']}] {i['title']} ({i['status']}, source={i['source']})")

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
        for i in unassigned_p0[:5]:
            lines.append(f"  Issue #{i['id']} {i['title']} [{i.get('status','?')}]")

    lines.append("")
    lines.append(f"=== 我的状态 ({agent_name}) ===")
    my_issues_resp = await _api_request("GET", f"{API_BASE}/issues", params={"created_by": agent_name, "status": "open", "limit": 5})
    if my_issues_resp.status_code < 400:
        my_data = my_issues_resp.json()
        my_open = my_data.get("total", 0)
        lines.append(f"我创建的 Open Issue: {my_open}")

    my_plans_resp = await _api_request("GET", f"{API_BASE}/plans", params={"status": "pending_approval"})
    if my_plans_resp.status_code < 400:
        my_plans = my_plans_resp.json()
        my_pending = sum(1 for p in my_plans if p.get("proposed_by_name") == agent_name)
        if my_pending > 0:
            lines.append(f"我提交的待审批 Plan: {my_pending}")

    notif_resp = await _api_request("GET", f"{API_BASE}/notifications", params={"unread_only": "true", "limit": 1})
    if notif_resp.status_code < 400:
        notif_data = notif_resp.json()
        lines.append(f"未读通知: {notif_data.get('total', 0)}")

    mem_resp = await _api_request("GET", f"{API_BASE}/agent-memories", params={"limit": 5})
    if mem_resp.status_code < 400:
        mem_data = mem_resp.json()
        if mem_data:
            lines.append(f"记忆条目: {len(mem_data)}")

    return "\n".join(lines)


@mcp.tool()
@require_role("agent", "mate", "tester", "registrar", "admin")
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
        owner = f" owner={item['owner']}" if item.get('owner') else ""
        desc = f"\n    描述: {item['description'][:80]}{'...' if len(item.get('description','')) > 80 else ''}" if item.get('description') else ""
        lines.append(f"  #{item['id']} [{status}] {item['name']} (slug={item['slug']}){stats}{owner}{desc}")
    return "\n".join(lines)


@mcp.tool()
@require_role("agent", "mate", "tester", "registrar", "admin")
async def list_issues(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    source: Optional[str] = None,
    assignee: Optional[str] = None,
    unassigned: bool = False,
    created_by: Optional[str] = None,
    milestone_id: Optional[int] = None,
    deferred_only: bool = False,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "created_at_desc",
) -> str:
    """查询 issues 列表（含描述、时间、负责人、里程碑等完整信息）。unassigned=True 筛选无负责人 Issue。sort_by 可选: created_at_desc/created_at_asc/updated_at_desc/updated_at_asc/priority_asc/priority_desc。created_by 按创建者筛选（如 hermes-agent）。offset 分页偏移量，默认 0。"""
    params = {"limit": limit, "skip": offset, "sort_by": sort_by}
    if project_id:
        params["project_id"] = project_id
    if status:
        params["status"] = status
    if priority:
        params["priority"] = priority
    if source:
        params["source"] = source
    if assignee:
        params["assignee"] = assignee
    if unassigned:
        params["unassigned"] = "true"
    if created_by:
        params["created_by"] = created_by
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
        desc_preview = ""
        if item.get("description"):
            d = item["description"]
            desc_preview = f"\n    描述: {d[:80]}..." if len(d) > 80 else f"\n    描述: {d}"
        assignee_info = f"\n    负责人: {item['assignee']}" if item.get("assignee") else ""
        deferred_info = ""
        if item.get("deferred_to_milestone_id"):
            deferred_info = f"\n    推迟到: milestone #{item['deferred_to_milestone_id']}"
            if item.get("deferred_reason"):
                deferred_info += f" ({item['deferred_reason']})"
        time_info = f"\n    创建: {item.get('created_at','?')} | 更新: {item.get('updated_at','?')}"
        by_info = f", by {item['created_by']}" if item.get('created_by') else ""
        lines.append(f"  #{item['id']} [{item['priority']}] {item['title']} ({item['status']}, source={item['source']}{by_info}, type={item.get('issue_type','?')}){desc_preview}{assignee_info}{deferred_info}{time_info}")
    return "\n".join(lines)


@mcp.tool()
@require_role("agent", "mate", "tester", "registrar", "admin")
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
        lines.append(f"  推迟到: milestone #{d['deferred_to_milestone_id']} (原因: {d.get('deferred_reason', '无')})")
    lines.append(f"  创建: {d.get('created_at', '?')} | 更新: {d.get('updated_at', '?')}")
    comments_resp = await _api_request("GET", f"{API_BASE}/issues/{issue_id}/comments", params={"limit": 10})
    if comments_resp.status_code < 400:
        comments = comments_resp.json()
        if comments:
            lines.append(f"  评论 ({len(comments)}):")
            for c in comments[:5]:
                lines.append(f"    #{c['id']} [{c.get('author', '?')}] {c['content'][:100]}{'...' if len(c.get('content', '')) > 100 else ''}")
    return "\n".join(lines)


@mcp.tool()
@require_role("agent", "mate", "tester", "registrar", "admin")
async def list_plans(status: Optional[str] = None, project_id: Optional[int] = None) -> str:
    """查询计划列表（含描述、审批信息、拒绝原因、进度统计）"""
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
        desc_preview = ""
        if item.get("description"):
            d = item["description"]
            desc_preview = f"\n    描述: {d[:100]}..." if len(d) > 100 else f"\n    描述: {d}"
        progress = ""
        if item.get("item_count") is not None:
            progress = f"\n    进度: {item.get('item_done_count',0)}/{item['item_count']} items done"
        approval = ""
        if item.get("approved_by"):
            approval = f"\n    审批: by {item['approved_by']} at {item.get('approved_at','?')}"
        reject = ""
        if item.get("reject_reason"):
            reject = f"\n    拒绝原因: {item['reject_reason']}"
        lines.append(f"  #{item['id']} [{item['status']}] {item['title']} (by {item.get('proposed_by_name') or item['proposed_by']}){desc_preview}{progress}{approval}{reject}")
    return "\n".join(lines)


@mcp.tool()
@require_role("agent", "mate", "tester", "registrar", "admin")
async def get_plan_detail(plan_id: int) -> str:
    """查看 Plan 完整详情（含审批信息、拒绝原因、进度项列表）"""
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
                lines.append(f"    {status_icon} #{item['id']} {item.get('content', '?')} ({item.get('status', '?')})")
    return "\n".join(lines)


@mcp.tool()
@require_role("agent", "mate", "tester", "registrar", "admin")
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
@require_role("agent", "mate", "tester", "registrar", "admin")
async def add_issue_comment(
    issue_id: int,
    content: str,
    parent_comment_id: Optional[int] = None,
    comment_type: str = "normal",
) -> str:
    """为 issue 添加评论。parent_comment_id 可选，用于回复特定评论（线程式回复）。

    Args:
        issue_id: Issue ID
        content: 评论内容
        parent_comment_id: 父评论 ID（可选）
        comment_type: 评论类型，可选 normal, management, handover, testing。默认 normal。
    """
    agent_name = await _current_sub()
    payload = {"content": content, "author": agent_name, "comment_type": comment_type}
    if parent_comment_id is not None:
        payload["parent_id"] = parent_comment_id
    resp = await _api_request("POST", f"{API_BASE}/issues/{issue_id}/comments", json=payload)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    reply_info = f" (reply to #{parent_comment_id})" if parent_comment_id else ""
    type_info = f" [{comment_type}]" if comment_type != "normal" else ""
    return f"Comment #{data['id']}{type_info} added to Issue #{issue_id} by {data.get('author', '?')}{reply_info} at {data.get('created_at', '?')}"


@mcp.tool()
@require_role("agent", "mate", "tester", "registrar", "admin")
async def list_comments(issue_id: int, limit: int = 50, offset: int = 0) -> str:
    """获取 Issue 的评论列表。offset 分页偏移量，默认 0。"""
    params = {"limit": limit, "offset": offset}
    resp = await _api_request("GET", f"{API_BASE}/issues/{issue_id}/comments", params=params)
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    items = resp.json()
    if not items:
        return f"No comments on Issue #{issue_id}."
    lines = [f"Total: {len(items)} comments on Issue #{issue_id}"]
    for c in items:
        reply = f" ↩#{c['parent_id']}" if c.get("parent_id") else ""
        ctype = f" [{c.get('comment_type','normal')}]" if c.get('comment_type', 'normal') != 'normal' else ""
        lines.append(f"  #{c['id']} [{c.get('author', '?')}]{ctype}{reply} {c['content'][:200]}{'...' if len(c.get('content', '')) > 200 else ''} ({c.get('created_at', '?')})")
    return "\n".join(lines)


@mcp.tool()
@require_role("agent", "mate", "tester", "registrar", "admin")
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


@mcp.tool()
@require_role("agent", "mate", "tester", "registrar", "admin")
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
@require_role("agent", "mate", "tester", "registrar", "admin")
async def check_notifications(unread_only: bool = False, limit: int = 10, since: str = "") -> str:
    """检查当前 Agent 的通知。since 可选，格式 ISO8601（如 2026-05-25T04:00:00），只返回该时间之后的通知。"""
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
@require_role("agent", "mate", "tester", "registrar", "admin")
async def mark_notification_read(notification_id: int) -> str:
    """标记通知已读"""
    resp = await _api_request("PUT", f"{API_BASE}/notifications/{notification_id}/read")
    if resp.status_code >= 400:
        return f"Error: {resp.status_code} - {resp.text}"
    return f"Notification #{notification_id} marked as read"


@mcp.tool()
@require_role("agent", "mate", "tester", "registrar", "admin")
async def list_workflows(project_id: Optional[int] = None) -> str:
    """列出工作流（含步骤概要）"""
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
        steps = item.get('steps', [])
        steps_info = ", ".join(f"{s.get('step_type', '?')}:{s.get('name', '')}" for s in steps) if steps else "none"
        lines.append(f"  #{item['id']} [{status}] {item['name']} (trigger={trigger}, steps=[{steps_info}])")
    return "\n".join(lines)


@mcp.tool()
@require_role("agent", "mate", "tester", "registrar", "admin")
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
        err = f"\n    错误: {item['error_message']}" if item.get('error_message') else ""
        ctx = ""
        if item.get('context'):
            ctx_str = str(item['context'])
            if len(ctx_str) > 100:
                ctx_str = ctx_str[:100] + "..."
            ctx = f"\n    上下文: {ctx_str}"
        lines.append(f"  Run #{item['id']} [{item['status']}] {wf_name} (step {item['current_step_index']}, by {item.get('triggered_by', '?')}){err}{ctx}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
#  Agent Only
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
#  Mate Only
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
        lines.append(f"  Plan #{item['id']} {item['title']} (by {item.get('proposed_by_name') or item.get('proposed_by','?')}){desc_preview}")
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
# ═══════════════════════════════════════════════════════

@mcp.tool()
@require_role("registrar", "admin")
async def register_project(
    name: str,
    path: str,
    description: str = "",
    tech_stack: str = "",
    repo_url: str = "",
    language: str = "",
    framework: str = "",
    notes: str = "",
) -> str:
    """登记一个项目到系统。如果路径已存在则返回错误。

    Args:
        name: 项目名称
        path: 项目本地路径（必须唯一）
        description: 项目描述
        tech_stack: 技术栈，逗号分隔，如 "Python,React,SQLite"
        repo_url: Git 仓库地址
        language: 主要编程语言
        framework: 使用的框架
        notes: 备注

    Returns:
        登记结果摘要
    """
    payload = {
        "name": name,
        "path": path,
    }
    if description:
        payload["description"] = description
    if tech_stack:
        payload["tech_stack"] = tech_stack
    if repo_url:
        payload["repo_url"] = repo_url
    if language:
        payload["language"] = language
    if framework:
        payload["framework"] = framework
    if notes:
        payload["notes"] = notes

    resp = await _api_request("POST", f"{API_BASE}/project-registrations", json=payload)
    if resp.status_code == 409:
        return f"路径已被登记: {path}。请使用 update_registration 更新已有记录。"
    if resp.status_code >= 400:
        return f"登记失败 ({resp.status_code}): {resp.text}"

    data = resp.json()
    return (
        f"已登记项目 #{data['id']}: {data['name']}\n"
        f"  路径: {data['path']}\n"
        f"  语言: {data.get('language') or '-'} | 框架: {data.get('framework') or '-'}\n"
        f"  技术栈: {data.get('tech_stack') or '-'}\n"
        f"  登记人: {data.get('registered_by') or '-'}\n"
        f"  创建时间: {data.get('created_at')}"
    )


@mcp.tool()
@require_role("registrar", "admin")
async def list_registrations(
    status: str = "active",
    language: str = "",
    tech_stack: str = "",
    registered_by: str = "",
    limit: int = 50,
) -> str:
    """查询已登记的项目列表。

    Args:
        status: 状态筛选，active/archived/stale，默认 active
        language: 按语言筛选（模糊匹配）
        tech_stack: 按技术栈筛选（模糊匹配）
        registered_by: 按登记人筛选
        limit: 返回数量，默认 50

    Returns:
        项目列表
    """
    params: dict = {"limit": limit}
    if status:
        params["status"] = status
    if language:
        params["language"] = language
    if tech_stack:
        params["tech_stack"] = tech_stack
    if registered_by:
        params["registered_by"] = registered_by

    resp = await _api_request("GET", f"{API_BASE}/project-registrations", params=params)
    if resp.status_code >= 400:
        return f"查询失败 ({resp.status_code}): {resp.text}"

    data = resp.json()
    items = data.get("items", [])
    total = data.get("total", 0)

    if not items:
        return "没有找到匹配的项目登记。"

    lines = [f"共 {total} 个项目登记（显示 {len(items)} 个）：\n"]
    for item in items:
        lines.append(
            f"  #{item['id']} {item['name']}\n"
            f"    路径: {item['path']}\n"
            f"    语言: {item.get('language') or '-'} | 框架: {item.get('framework') or '-'} | 技术栈: {item.get('tech_stack') or '-'}\n"
            f"    状态: {item['status']} | 登记人: {item.get('registered_by') or '-'}\n"
            f"    更新时间: {item.get('updated_at')}"
        )
    return "\n".join(lines)


@mcp.tool()
@require_role("registrar", "admin")
async def get_registration(reg_id: int) -> str:
    """查看项目登记详情。

    Args:
        reg_id: 项目登记 ID

    Returns:
        项目完整信息
    """
    resp = await _api_request("GET", f"{API_BASE}/project-registrations/{reg_id}")
    if resp.status_code == 404:
        return f"项目登记 #{reg_id} 不存在。"
    if resp.status_code >= 400:
        return f"查询失败 ({resp.status_code}): {resp.text}"

    data = resp.json()
    return (
        f"项目登记 #{data['id']}: {data['name']}\n"
        f"  路径: {data['path']}\n"
        f"  描述: {data.get('description') or '-'}\n"
        f"  语言: {data.get('language') or '-'}\n"
        f"  框架: {data.get('framework') or '-'}\n"
        f"  技术栈: {data.get('tech_stack') or '-'}\n"
        f"  仓库: {data.get('repo_url') or '-'}\n"
        f"  状态: {data['status']}\n"
        f"  备注: {data.get('notes') or '-'}\n"
        f"  登记人: {data.get('registered_by') or '-'}\n"
        f"  最后扫描: {data.get('last_scanned_at') or '-'}\n"
        f"  创建时间: {data.get('created_at')}\n"
        f"  更新时间: {data.get('updated_at')}"
    )


@mcp.tool()
@require_role("registrar", "admin")
async def update_registration(
    reg_id: int,
    name: str = "",
    description: str = "",
    tech_stack: str = "",
    repo_url: str = "",
    language: str = "",
    framework: str = "",
    status: str = "",
    notes: str = "",
) -> str:
    """更新项目登记信息。只传需要修改的字段。

    Args:
        reg_id: 项目登记 ID
        name: 项目名称
        description: 项目描述
        tech_stack: 技术栈
        repo_url: Git 仓库地址
        language: 主要编程语言
        framework: 使用的框架
        status: 状态，active/archived/stale
        notes: 备注

    Returns:
        更新结果
    """
    payload: dict = {}
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    if tech_stack:
        payload["tech_stack"] = tech_stack
    if repo_url:
        payload["repo_url"] = repo_url
    if language:
        payload["language"] = language
    if framework:
        payload["framework"] = framework
    if status:
        payload["status"] = status
    if notes:
        payload["notes"] = notes

    if not payload:
        return "没有提供任何更新字段。"

    resp = await _api_request("PUT", f"{API_BASE}/project-registrations/{reg_id}", json=payload)
    if resp.status_code == 404:
        return f"项目登记 #{reg_id} 不存在。"
    if resp.status_code >= 400:
        return f"更新失败 ({resp.status_code}): {resp.text}"

    data = resp.json()
    return (
        f"已更新项目登记 #{data['id']}: {data['name']}\n"
        f"  更新字段: {', '.join(payload.keys())}\n"
        f"  更新时间: {data.get('updated_at')}"
    )


@mcp.tool()
@require_role("registrar", "admin")
async def mark_scanned(reg_id: int) -> str:
    """标记项目已扫描，更新 last_scanned_at 为当前时间。

    Args:
        reg_id: 项目登记 ID

    Returns:
        标记结果
    """
    now = datetime.now(timezone.utc).isoformat()
    resp = await _api_request(
        "PUT", f"{API_BASE}/project-registrations/{reg_id}",
        json={"last_scanned_at": now},
    )
    if resp.status_code == 404:
        return f"项目登记 #{reg_id} 不存在。"
    if resp.status_code >= 400:
        return f"标记失败 ({resp.status_code}): {resp.text}"

    data = resp.json()
    return f"已标记项目 #{data['id']} ({data['name']}) 为已扫描，时间: {data.get('last_scanned_at')}"


@mcp.tool()
@require_role("registrar", "admin")
async def delete_registration(reg_id: int) -> str:
    """删除项目登记记录。

    Args:
        reg_id: 项目登记 ID

    Returns:
        删除结果
    """
    resp = await _api_request("GET", f"{API_BASE}/project-registrations/{reg_id}")
    if resp.status_code == 404:
        return f"项目登记 #{reg_id} 不存在。"
    name = resp.json().get("name", "?")

    resp = await _api_request("DELETE", f"{API_BASE}/project-registrations/{reg_id}")
    if resp.status_code >= 400:
        return f"删除失败 ({resp.status_code}): {resp.text}"

    return f"已删除项目登记 #{reg_id}: {name}"


# ═══════════════════════════════════════════════════════
#  启动入口
# ═══════════════════════════════════════════════════════

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
