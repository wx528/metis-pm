"""共享工具 - 所有角色可用

所有 Agent 角色（agent, mate, tester, registrar, admin）都可以调用的工具。
这些工具提供基础查询、通知、评论等功能。
"""
from typing import Optional

from mcp_common import API_BASE, _api_request, _current_sub, get_headers


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


def register_tools(mcp, require_role, safe_tool):
    """注册共享工具（所有角色可用）"""

    # ═══════════════════════════════════════════════════════
    #  共享工具 (All Roles)
    # ═══════════════════════════════════════════════════════

    @mcp.tool()
    @require_role("agent", "mate", "tester", "registrar", "admin")
    @safe_tool
    async def check_connection() -> str:
        """测试 MCP Server 与后端 API 的连接是否正常"""
        try:
            headers = await get_headers()
        except RuntimeError as e:
            return f"ERROR: {e}"
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/auth/me", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return f"Connected OK. Identity: {data.get('sub', '?')} (role={data.get('role', '?')})"
            elif resp.status_code == 401:
                from mcp_common import _token_cache, _cache_key, _get_password
                key = _cache_key(_get_password())
                _token_cache.pop(key, None)
                return "ERROR: Token invalid or expired (401). Will re-login on next call."
            else:
                return f"ERROR: API returned {resp.status_code}. Is the backend running?"

    @mcp.tool()
    @require_role("agent", "mate", "tester", "registrar", "admin")
    @safe_tool
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
                lines.append(f"  Plan #{p['id']}: {p['title']}{desc_preview} (by {p.get('proposed_by','?')})")

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

        my_plans_resp = await _api_request("GET", f"{API_BASE}/plans", params={"status": "pending"})
        if my_plans_resp.status_code < 400:
            my_plans = my_plans_resp.json()
            my_pending = sum(1 for p in my_plans if p.get("proposed_by") == agent_name)
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
    @safe_tool
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
    @safe_tool
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
    @safe_tool
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
    @safe_tool
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
            lines.append(f"  #{item['id']} [{item['status']}] {item['title']} (by {item.get('proposed_by')}){desc_preview}{progress}{approval}{reject}")
        return "\n".join(lines)

    @mcp.tool()
    @require_role("agent", "mate", "tester", "registrar", "admin")
    @safe_tool
    async def get_plan_detail(plan_id: int) -> str:
        """查看 Plan 完整详情（含审批信息、拒绝原因、进度项列表）"""
        resp = await _api_request("GET", f"{API_BASE}/plans/{plan_id}")
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        d = resp.json()
        lines = [
            f"Plan #{d['id']} [{d['status']}] {d['title']}",
            f"  提议者: {d.get('proposed_by', '?')} | 项目: #{d.get('project_id', '?')}",
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
    @safe_tool
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
    @safe_tool
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
    @safe_tool
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
    @safe_tool
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
    @safe_tool
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
            # API 调用失败，放入消息队列稍后重试
            from src.core.message_queue import message_queue
            await message_queue.enqueue(payload)
            return f"⚠️ API 暂时不可用，通知已排队稍后发送: {title}"
        data = resp.json()
        return f"通知已发送给角色 '{target_role}': {title} (通知ID: {data.get('id', '?')})"

    @mcp.tool()
    @require_role("agent", "mate", "tester", "registrar", "admin")
    @safe_tool
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
    @safe_tool
    async def mark_notification_read(notification_id: int) -> str:
        """标记通知已读"""
        resp = await _api_request("PUT", f"{API_BASE}/notifications/{notification_id}/read")
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        return f"Notification #{notification_id} marked as read"

    @mcp.tool()
    @require_role("agent", "mate", "tester", "registrar", "admin")
    @safe_tool
    async def mark_handover_read(comment_id: int) -> str:
        """标记一条交接评论为已读。Agent 收到交接后调用此工具确认已读。

        Args:
            comment_id: 交接评论的 ID

        Returns:
            确认结果
        """
        agent_name = await _current_sub()
        resp = await _api_request("PUT", f"{API_BASE}/issue-comments/{comment_id}/read")
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        return f"✅ 已标记交接评论 #{comment_id} 为已读 (by {agent_name})"

    @mcp.tool()
    @require_role("agent", "mate", "tester", "registrar", "admin")
    @safe_tool
    async def check_unread_handovers(limit: int = 20) -> str:
        """检查当前 Agent 的未读交接评论。

        Args:
            limit: 最多返回多少条，默认 20

        Returns:
            未读交接列表
        """
        agent_name = await _current_sub()
        resp = await _api_request(
            "GET",
            f"{API_BASE}/issue-comments",
            params={
                "comment_type": "handover",
                "unread_only": "true",
                "limit": limit,
            },
        )
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        items = resp.json()
        if not items:
            return f"{agent_name}: 没有未读交接 ✅"
        lines = [f"未读交接 ({len(items)}):"]
        for item in items:
            lines.append(f"  #{item['id']} Issue #{item['issue_id']} by {item['author']} at {item['created_at']}")
            lines.append(f"    {item['content'][:200]}...")
        return "\n".join(lines)

    @mcp.tool()
    @require_role("agent", "mate", "tester", "registrar", "admin")
    @safe_tool
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
    @safe_tool
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

    @mcp.tool()
    @require_role("agent", "mate", "tester", "registrar", "admin")
    @safe_tool
    async def get_workflow_run_detail(run_id: int) -> str:
        """查看工作流执行详情（含每步执行状态）

        Args:
            run_id: WorkflowRun ID
        """
        resp = await _api_request("GET", f"{API_BASE}/workflows/runs/{run_id}")
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        data = resp.json()

        lines = [
            f"Run #{data['id']} [{data['status']}]",
            f"  工作流: {data.get('workflow_name', '?')} (ID: {data['workflow_id']})",
            f"  触发者: {data.get('triggered_by', '?')}",
            f"  当前步骤索引: {data['current_step_index']}",
            f"  开始时间: {data.get('started_at', '?')}",
            f"  完成时间: {data.get('completed_at', '-')}",
        ]
        if data.get('error_message'):
            lines.append(f"  错误: {data['error_message']}")

        step_runs = data.get('step_runs', [])
        if step_runs:
            lines.append(f"\n  步骤执行记录 ({len(step_runs)} 步):")
            for sr in step_runs:
                status_icon = {
                    "pending": "⏳", "running": "▶️", "completed": "✅",
                    "failed": "❌", "skipped": "⏭️",
                }.get(sr['status'], "?")
                line = f"    {status_icon} Step #{sr['step_id']} [{sr['status']}]"
                if sr.get('retry_count', 0) > 0:
                    line += f" (重试 {sr['retry_count']} 次)"
                if sr.get('error'):
                    err_short = sr['error'][:80] + "..." if len(sr['error']) > 80 else sr['error']
                    line += f"\n      错误: {err_short}"
                if sr.get('result'):
                    res_str = str(sr['result'])
                    if len(res_str) > 80:
                        res_str = res_str[:80] + "..."
                    line += f"\n      结果: {res_str}"
                lines.append(line)
        else:
            lines.append("\n  无步骤执行记录")

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════
    #  意见箱 (Feedback)
    # ═══════════════════════════════════════════════════════

    @mcp.tool()
    @require_role("agent", "mate", "tester", "registrar", "admin")
    @safe_tool
    async def submit_feedback(
        title: str,
        content: str,
        category: str = "other",
        priority: str = "P2",
        project_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
    ) -> str:
        """提交意见/反馈到意见箱。Agent 在使用过程中遇到问题或有改进建议时随时提交。

        Args:
            title: 反馈标题，简短概括
            content: 反馈详细内容，描述遇到的问题或改进建议
            category: 分类，可选值: bug（遇到Bug）, feature_request（希望新增功能）, improvement（改进建议）, ux（使用体验）, workflow（工作流相关）, other（其他）。默认 other
            priority: 优先级，可选 P0/P1/P2/P3，默认 P2
            project_id: 关联项目 ID（可选）
            entity_type: 关联实体类型，如 issue, plan, workflow（可选）
            entity_id: 关联实体 ID（可选）

        Returns:
            提交结果摘要
        """
        payload = {
            "title": title,
            "content": content,
            "category": category,
            "priority": priority,
        }
        if project_id is not None:
            payload["project_id"] = project_id
        if entity_type is not None:
            payload["entity_type"] = entity_type
        if entity_id is not None:
            payload["entity_id"] = entity_id

        resp = await _api_request("POST", f"{API_BASE}/feedbacks", json=payload)
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        data = resp.json()
        return f"✅ 意见已提交: #{data['id']} [{category}] {title} (by {data.get('submitted_by', '?')})"

    @mcp.tool()
    @require_role("agent", "mate", "tester", "registrar", "admin")
    @safe_tool
    async def list_feedbacks(
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """查看意见箱反馈列表。Agent 只能看自己提交的，admin 可看全部。

        Args:
            category: 按分类筛选，可选: bug, feature_request, improvement, ux, workflow, other
            status: 按状态筛选，可选: open, acknowledged, in_progress, resolved, wont_fix
            limit: 返回数量，默认 20

        Returns:
            反馈列表
        """
        params = {"limit": limit}
        if category:
            params["category"] = category
        if status:
            params["status"] = status

        resp = await _api_request("GET", f"{API_BASE}/feedbacks", params=params)
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        data = resp.json()
        items = data.get("items", [])
        if not items:
            return "意见箱暂无反馈。"
        lines = [f"共 {data['total']} 条反馈"]
        for item in items:
            reply_mark = "💬" if item.get("admin_reply") else ""
            lines.append(
                f"  #{item['id']} [{item['category']}] [{item['status']}] {item['title']} "
                f"(by {item.get('submitted_by', '?')}, {item.get('priority', 'P2')}) {reply_mark}"
            )
            if item.get("admin_reply"):
                reply_preview = item["admin_reply"][:80]
                lines.append(f"    💬 管理员回复: {reply_preview}{'...' if len(item['admin_reply']) > 80 else ''}")
        return "\n".join(lines)

    @mcp.tool()
    @require_role("agent", "mate", "tester", "registrar", "admin")
    @safe_tool
    async def get_feedback_detail(feedback_id: int) -> str:
        """查看反馈详情（含管理员回复）

        Args:
            feedback_id: 反馈 ID

        Returns:
            反馈详情
        """
        resp = await _api_request("GET", f"{API_BASE}/feedbacks/{feedback_id}")
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        d = resp.json()
        lines = [
            f"反馈 #{d['id']} [{d['category']}] [{d['status']}] {d['title']}",
            f"  提交者: {d.get('submitted_by', '?')} (角色: {d.get('submitted_by_role', '?')})",
            f"  优先级: {d.get('priority', 'P2')}",
            f"  内容: {d['content']}",
        ]
        if d.get("project_id"):
            lines.append(f"  关联项目: #{d['project_id']}")
        if d.get("entity_type"):
            lines.append(f"  关联实体: {d['entity_type']} #{d.get('entity_id', '?')}")
        if d.get("admin_reply"):
            lines.append(f"  💬 管理员回复 (by {d.get('replied_by', '?')} at {d.get('replied_at', '?')}):")
            lines.append(f"    {d['admin_reply']}")
        else:
            lines.append("  管理员暂未回复")
        lines.append(f"  创建: {d.get('created_at', '?')} | 更新: {d.get('updated_at', '?')}")
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════
    #  审计日志 (Audit)
    # ═══════════════════════════════════════════════════════

    @mcp.tool()
    @require_role("admin")
    @safe_tool
    async def list_audit_logs(
        entity_type: Optional[str] = None,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 50,
    ) -> str:
        """查看审计日志（仅 admin）。可查看 MCP 工具调用记录、操作历史等。

        Args:
            entity_type: 按实体类型筛选，如 mcp_tool, issue, plan 等
            actor: 按操作者筛选（如 agent 名称）
            action: 按动作筛选（如 MCP 工具名：create_issue, list_issues 等）
            limit: 返回数量，默认 50

        Returns:
            审计日志列表
        """
        params = {"limit": limit}
        if entity_type:
            params["entity_type"] = entity_type
        if actor:
            params["actor"] = actor
        if action:
            params["action"] = action

        resp = await _api_request("GET", f"{API_BASE}/activity-logs", params=params)
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        items = resp.json()
        if not items:
            return "暂无审计日志。"
        lines = [f"共 {len(items)} 条审计日志"]
        for item in items[:30]:
            new_val = item.get("new_value") or {}
            if item["entity_type"] == "mcp_tool":
                # MCP 工具调用审计
                tool = new_val.get("tool", "?")
                duration = new_val.get("duration_ms", "?")
                success = "✅" if new_val.get("success") else "❌"
                client_ip = new_val.get("client_ip", "")
                ip_info = f" from {client_ip}" if client_ip else ""
                lines.append(
                    f"  #{item['id']} [{item['created_at'][:19]}] {success} {item['actor']} → {tool} "
                    f"({duration}ms){ip_info}"
                )
            else:
                lines.append(
                    f"  #{item['id']} [{item['created_at'][:19]}] {item['actor']} → "
                    f"{item['action']} on {item['entity_type']}#{item['entity_id']}"
                )
        return "\n".join(lines)
