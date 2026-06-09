# 多 Agent 协作工作流实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让多个 AI Coding Agent（IDE/工具）通过 MCP 接入 Project Manager System，实现角色分工与协作，包含通知互通、交接模板、Agent 活动面板。

**Architecture:** 后端扩展 Notification/Comment 模型支持角色级通知和交接评论类型，新增 `notify_role`/`get_handover_template` MCP 工具，新增 Agent 状态聚合 API；前端新增 AgentActivityPanel 组件嵌入 Dashboard，支持交接评论渲染。

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 async, SQLite, React 19, TypeScript, Ant Design 6, MCP

---

## 文件结构

### 新增文件

| 文件 | 职责 |
|------|------|
| `backend/src/routes/agent_status.py` | Agent 状态聚合 API (`GET /api/v1/dashboard/agents`) |
| `frontend/src/api/agentStatus.ts` | 前端 Agent 状态 API 封装 |
| `frontend/src/components/AgentActivityPanel.tsx` | Agent 协作看板组件 |
| `frontend/src/components/HandoverComment.tsx` | 交接评论结构化卡片组件 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `backend/src/models/notification.py` | 新增 `ROLE_NOTIFICATION` 类型 |
| `backend/src/models/comment.py` | 新增 `HANDOVER` 类型 |
| `backend/src/routes/notifications.py` | 扩展 `_recipient_filter` 支持角色名 |
| `backend/src/routes/__init__.py` | 注册 agent_status 路由 |
| `backend/mcp_server.py` | 新增 `notify_role`, `get_handover_template`, `add_issue_comment` 支持 comment_type |
| `backend/mcp_server_mate.py` | 同上（mate 角色也需要） |
| `backend/mcp_server_tester.py` | 同上（tester 角色也需要） |
| `frontend/src/pages/Dashboard.tsx` | 嵌入 AgentActivityPanel |
| `frontend/src/components/ActivityTimeline.tsx` | 支持 handover 类型渲染 |
| `frontend/src/api/index.ts` | 导出 agentStatus API |
| `docs/mcp-config.md` | 扩展为角色配置手册 |

---

## Task 1: 扩展 Notification 模型 — 新增 ROLE_NOTIFICATION 类型

**Files:**
- Modify: `backend/src/models/notification.py:9-16`

- [ ] **Step 1: 修改枚举添加 ROLE_NOTIFICATION**

```python
class NotificationType(str, enum.Enum):
    APPROVAL_NEEDED = "approval_needed"
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    MENTION = "mention"
    WORKFLOW_PAUSED = "workflow_paused"
    ROLE_NOTIFICATION = "role_notification"   # 新增
    INFO = "info"
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/models/notification.py
git commit -m "feat(notification): add ROLE_NOTIFICATION type for inter-agent communication"
```

---

## Task 2: 扩展 Comment 模型 — 新增 HANDOVER 类型

**Files:**
- Modify: `backend/src/models/comment.py:8-11`

- [ ] **Step 1: 修改 CommentType 添加 HANDOVER**

```python
class CommentType:
    NORMAL = "normal"
    MANAGEMENT = "management"
    HANDOVER = "handover"       # 新增：交接评论
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/models/comment.py
git commit -m "feat(comment): add HANDOVER comment type for agent handovers"
```

---

## Task 3: 扩展通知路由 — 支持角色名作为 recipient

**Files:**
- Modify: `backend/src/routes/notifications.py:19-26`

- [ ] **Step 1: 修改 _recipient_filter 支持角色名匹配**

```python
def _recipient_filter(user: dict):
    sub = user.get("sub", "")
    role = user.get("role", "")
    # 直接发给该用户的通知
    personal = Notification.recipient == sub
    # 发给该角色所有成员的通知（agent, mate, tester, registrar 等）
    role_match = Notification.recipient == role
    # 发给 ai_agent 泛角色的通知（所有 agent 角色可见）
    agent_broadcast = Notification.recipient == "ai_agent" if role == "agent" else False

    if role == "agent":
        return or_(personal, role_match, agent_broadcast)
    if role in ("mate", "tester", "registrar"):
        return or_(personal, role_match)
    # admin / user
    return or_(personal, Notification.recipient == "admin")
```

- [ ] **Step 2: 更新 mark_read 权限检查**

修改 `backend/src/routes/notifications.py:82` 的权限检查：

```python
# 原代码:
# if notification.recipient != user["sub"] and notification.recipient != "ai_agent":
# 改为:
allowed = [user["sub"], user.get("role", ""), "ai_agent" if user.get("role") == "agent" else ""]
if notification.recipient not in allowed:
    raise HTTPException(status_code=403, detail="Not your notification")
```

- [ ] **Step 3: Commit**

```bash
git add backend/src/routes/notifications.py
git commit -m "feat(notifications): support role-based recipient filtering for inter-agent communication"
```

---

## Task 4: 新增 notify_role MCP 工具（mcp_server.py）

**Files:**
- Modify: `backend/mcp_server.py`（在现有工具后追加）

- [ ] **Step 1: 在 mcp_server.py 中添加 notify_role 工具**

在 `backend/mcp_server.py` 最后（约第 930 行之后，或任何 `@mcp.tool()` 之后）添加：

```python
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
    from datetime import datetime, timezone

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
```

- [ ] **Step 2: 添加 get_handover_template 工具**

```python
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
```

- [ ] **Step 3: 修改 add_issue_comment 支持 comment_type**

找到 `backend/mcp_server.py:436` 的 `add_issue_comment` 函数，修改签名和 payload：

```python
# 原签名:
# async def add_issue_comment(issue_id: int, content: str, parent_comment_id: Optional[int] = None) -> str:
# 改为:
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
        comment_type: 评论类型，可选 normal, management, handover。默认 normal。
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
```

- [ ] **Step 4: Commit**

```bash
git add backend/mcp_server.py
git commit -m "feat(mcp): add notify_role, get_handover_template tools; support comment_type in add_issue_comment"
```

---

## Task 5: 同步更新 mcp_server_mate.py

**Files:**
- Modify: `backend/mcp_server_mate.py`

- [ ] **Step 1: 在 mcp_server_mate.py 中导入新增工具**

在 `backend/mcp_server_mate.py` 的 import 区域（约前 40 行），确保导入：

```python
from mcp_common import (
    API_BASE, _api_request, _current_sub, get_headers,
    PasswordMiddleware, AGENT_PASSWORD,
)
```

- [ ] **Step 2: 添加 notify_role 工具**

在文件末尾（或其他工具定义区域）添加与 Task 4 Step 1 完全相同的 `notify_role` 函数代码。

- [ ] **Step 3: 添加 get_handover_template 工具**

添加与 Task 4 Step 2 完全相同的 `_HANDOVER_TEMPLATES` 字典和 `get_handover_template` 函数代码。

- [ ] **Step 4: 修改 add_issue_comment 支持 comment_type**

找到 `mcp_server_mate.py` 中的 `add_issue_comment`，按 Task 4 Step 3 修改签名和 payload。

- [ ] **Step 5: Commit**

```bash
git add backend/mcp_server_mate.py
git commit -m "feat(mcp-mate): sync notify_role, get_handover_template, comment_type support"
```

---

## Task 6: 同步更新 mcp_server_tester.py

**Files:**
- Modify: `backend/mcp_server_tester.py`

- [ ] **Step 1-4:** 与 Task 5 完全相同的改动，在 `mcp_server_tester.py` 中添加 `notify_role`、`get_handover_template`，修改 `add_issue_comment`。

- [ ] **Step 5: Commit**

```bash
git add backend/mcp_server_tester.py
git commit -m "feat(mcp-tester): sync notify_role, get_handover_template, comment_type support"
```

---

## Task 7: 创建 Agent 状态聚合 API

**Files:**
- Create: `backend/src/routes/agent_status.py`
- Modify: `backend/src/routes/__init__.py`

- [ ] **Step 1: 创建 agent_status.py**

```python
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from src.core.dependencies import get_db
from src.routes.auth import get_current_user
from src.models.activity_log import ActivityLog
from src.models.issue import Issue, IssueStatus
from src.models.comment import Comment

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/agents")
async def get_agent_status(
    project_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取各 Agent 角色的实时状态和待交接任务"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. 获取所有 activity_log 中的 identity（actor）列表
    actors_query = select(ActivityLog.actor).distinct()
    if project_id:
        actors_query = actors_query.where(ActivityLog.project_id == project_id)
    actors_result = await db.execute(actors_query)
    actors = [row[0] for row in actors_result.all() if row[0] and row[0] != "user"]

    # 2. 为每个 actor 计算状态
    agents = []
    for actor in actors:
        # 最近活动时间
        last_query = select(ActivityLog.created_at).where(ActivityLog.actor == actor)
        if project_id:
            last_query = last_query.where(ActivityLog.project_id == project_id)
        last_query = last_query.order_by(desc(ActivityLog.created_at)).limit(1)
        last_result = await db.execute(last_query)
        last_active = last_result.scalar()

        # 状态判断
        if last_active:
            delta = now - last_active
            if delta < timedelta(hours=1):
                status = "online"
            elif delta < timedelta(hours=4):
                status = "idle"
            else:
                status = "offline"
        else:
            status = "offline"
            last_active = None

        # 今日统计
        today_created = 0
        today_completed = 0
        today_reviewed = 0
        if last_active:
            stats_query = select(
                ActivityLog.action,
                func.count(ActivityLog.id),
            ).where(
                ActivityLog.actor == actor,
                ActivityLog.created_at >= today_start,
            )
            if project_id:
                stats_query = stats_query.where(ActivityLog.project_id == project_id)
            stats_query = stats_query.group_by(ActivityLog.action)
            stats_result = await db.execute(stats_query)
            stats_map = {row.action: row[1] for row in stats_result.all()}
            today_created = stats_map.get("created", 0)
            today_completed = stats_map.get("completed", 0)
            # reviewed 统计：mate 角色的 approved/rejected 动作
            today_reviewed = stats_map.get("approved", 0) + stats_map.get("rejected", 0)

        # 待办任务数
        pending_tasks = 0
        if actor.startswith(("trae", "cursor", "agent")):  # 简化：agent 角色
            pending_query = select(func.count(Issue.id)).where(
                Issue.status.in_([IssueStatus.OPEN, IssueStatus.IN_PROGRESS]),
            )
            if project_id:
                pending_query = pending_query.where(Issue.project_id == project_id)
            pending_result = await db.execute(pending_query)
            pending_tasks = pending_result.scalar() or 0

        # 推断角色（从 identity 前缀或 actor 名称）
        role = "agent"
        if "mate" in actor.lower():
            role = "mate"
        elif "tester" in actor.lower():
            role = "tester"
        elif "registrar" in actor.lower():
            role = "registrar"

        agents.append({
            "role": role,
            "identity": actor,
            "last_active": last_active.isoformat() if last_active else None,
            "status": status,
            "today_created": today_created,
            "today_completed": today_completed,
            "today_reviewed": today_reviewed,
            "pending_tasks": pending_tasks,
        })

    # 3. 获取待交接任务（最近 24h 的 handover 评论）
    day_ago = now - timedelta(hours=24)
    handover_query = select(Comment).where(
        Comment.comment_type == "handover",
        Comment.created_at >= day_ago,
    ).order_by(desc(Comment.created_at)).limit(20)
    handover_result = await db.execute(handover_query)
    handover_comments = handover_result.scalars().all()

    pending_handovers = []
    for c in handover_comments:
        # 尝试从评论内容解析标题和 @目标角色
        content = c.content or ""
        title_line = content.split("\n")[0] if content else ""
        # 简单提取 #数字 作为 issue_id
        import re
        issue_match = re.search(r'#(\d+)', title_line)
        issue_id = int(issue_match.group(1)) if issue_match else c.issue_id

        # 尝试找 @角色
        at_match = re.search(r'@(\w+)', content)
        to_role = at_match.group(1) if at_match else "unknown"

        pending_handovers.append({
            "issue_id": issue_id,
            "from_role": c.author or "unknown",
            "to_role": to_role,
            "title": title_line.replace("## ", "").strip(),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return {
        "agents": agents,
        "pending_handovers": pending_handovers,
    }
```

- [ ] **Step 2: 注册路由**

修改 `backend/src/routes/__init__.py`：

```python
from src.routes import issues, milestones, plans, servers, activity_logs, auth, dashboard, projects, notifications, stats, workflows, agent_memory, project_registrations, agent_status

# ... 在 api_router.include_router 区域添加:
api_router.include_router(agent_status.router, prefix="/dashboard", tags=["Agent状态"])
```

注意：agent_status 的 prefix 也是 `/dashboard`，这样它的完整路径是 `/api/v1/dashboard/agents`，与 dashboard 路由并列。

- [ ] **Step 3: Commit**

```bash
git add backend/src/routes/agent_status.py backend/src/routes/__init__.py
git commit -m "feat(api): add /dashboard/agents endpoint for agent status aggregation"
```

---

## Task 8: 前端 API 层 — agentStatus.ts

**Files:**
- Create: `frontend/src/api/agentStatus.ts`
- Modify: `frontend/src/api/index.ts`

- [ ] **Step 1: 创建 agentStatus.ts**

```typescript
import { api } from "./client";

export interface AgentStatus {
  role: string;
  identity: string;
  last_active: string | null;
  status: "online" | "idle" | "offline";
  today_created: number;
  today_completed: number;
  today_reviewed: number;
  pending_tasks: number;
}

export interface PendingHandover {
  issue_id: number;
  from_role: string;
  to_role: string;
  title: string;
  created_at: string;
}

export interface AgentStatusResponse {
  agents: AgentStatus[];
  pending_handovers: PendingHandover[];
}

export const agentStatusApi = {
  get: (project_id?: number) =>
    api.get<AgentStatusResponse>("/dashboard/agents", {
      params: project_id ? { project_id } : undefined,
    }),
};
```

- [ ] **Step 2: 在 index.ts 中导出**

修改 `frontend/src/api/index.ts`，在最后一行添加：

```typescript
export * from "./agentStatus";
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/agentStatus.ts frontend/src/api/index.ts
git commit -m "feat(frontend): add agentStatus API layer"
```

---

## Task 9: 前端 AgentActivityPanel 组件

**Files:**
- Create: `frontend/src/components/AgentActivityPanel.tsx`

- [ ] **Step 1: 创建组件**

```tsx
import { useEffect, useState } from "react";
import { Card, Row, Col, Tag, Spin, Empty, Badge, Tooltip } from "antd";
import {
  RobotOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  MessageOutlined,
  ArrowRightOutlined,
} from "@ant-design/icons";
import { agentStatusApi } from "../api/agentStatus";
import type { AgentStatus, PendingHandover } from "../api/agentStatus";
import { useProject } from "../hooks/useProject";

const statusConfig: Record<string, { color: string; text: string }> = {
  online: { color: "#52c41a", text: "在线" },
  idle: { color: "#faad14", text: "空闲" },
  offline: { color: "#d9d9d9", text: "离线" },
};

const roleLabels: Record<string, string> = {
  agent: "开发",
  mate: "审查",
  tester: "测试",
  registrar: "登记",
};

const roleColors: Record<string, string> = {
  agent: "blue",
  mate: "purple",
  tester: "orange",
  registrar: "cyan",
};

interface Props {
  onHandoverClick?: (issueId: number) => void;
}

export default function AgentActivityPanel({ onHandoverClick }: Props) {
  const [loading, setLoading] = useState(true);
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [handovers, setHandovers] = useState<PendingHandover[]>([]);
  const { currentProject } = useProject();

  const load = async () => {
    if (!currentProject) return;
    setLoading(true);
    try {
      const res = await agentStatusApi.get(currentProject.id);
      setAgents(res.data.agents);
      setHandovers(res.data.pending_handovers);
    } catch (err) {
      console.error("Failed to load agent status:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const timer = setInterval(load, 60000); // 每60秒刷新
    return () => clearInterval(timer);
  }, [currentProject]);

  if (loading) return <Spin size="small" />;

  return (
    <Card
      title={
        <span>
          <RobotOutlined /> Agent 协作看板
        </span>
      }
      style={{ marginBottom: 24 }}
    >
      {/* Agent 卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {agents.map((agent) => {
          const cfg = statusConfig[agent.status] || statusConfig.offline;
          return (
            <Col span={8} key={agent.identity}>
              <Card
                size="small"
                style={{ borderLeft: `4px solid ${cfg.color}` }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <Badge color={cfg.color} />
                  <strong>{agent.identity}</strong>
                  <Tag color={roleColors[agent.role] || "default"} size="small">
                    {roleLabels[agent.role] || agent.role}
                  </Tag>
                </div>
                <div style={{ fontSize: 12, color: "#666" }}>
                  <div>
                    <CheckCircleOutlined /> 今日创建: {agent.today_created}
                  </div>
                  <div>
                    <ClockCircleOutlined /> 今日完成: {agent.today_completed}
                  </div>
                  {agent.today_reviewed > 0 && (
                    <div>
                      <MessageOutlined /> 今日审查: {agent.today_reviewed}
                    </div>
                  )}
                  <div style={{ marginTop: 4, color: agent.pending_tasks > 0 ? "#cf1322" : "#666" }}>
                    待办: {agent.pending_tasks}
                  </div>
                </div>
              </Card>
            </Col>
          );
        })}
        {agents.length === 0 && (
          <Col span={24}>
            <Empty description="暂无 Agent 活动数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          </Col>
        )}
      </Row>

      {/* 待交接任务 */}
      {handovers.length > 0 && (
        <div>
          <div style={{ fontWeight: "bold", marginBottom: 8 }}>
            <MessageOutlined /> 待交接任务
          </div>
          <div style={{ maxHeight: 200, overflowY: "auto" }}>
            {handovers.map((h) => (
              <div
                key={`${h.issue_id}-${h.created_at}`}
                style={{
                  padding: "8px 12px",
                  borderBottom: "1px solid #f0f0f0",
                  cursor: onHandoverClick ? "pointer" : "default",
                }}
                onClick={() => onHandoverClick?.(h.issue_id)}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Tag size="small">Issue #{h.issue_id}</Tag>
                  <span style={{ flex: 1 }}>{h.title}</span>
                  <Tag color="default" size="small">
                    {h.from_role}
                  </Tag>
                  <ArrowRightOutlined style={{ color: "#999" }} />
                  <Tag color="processing" size="small">
                    @{h.to_role}
                  </Tag>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/AgentActivityPanel.tsx
git commit -m "feat(frontend): add AgentActivityPanel component"
```

---

## Task 10: Dashboard 嵌入 AgentActivityPanel

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: 导入组件并嵌入**

在 `frontend/src/pages/Dashboard.tsx` 顶部 import 区域添加：

```typescript
import AgentActivityPanel from "../components/AgentActivityPanel";
```

在 return 的 JSX 中，在第一行 `<Row gutter={16} style={{ marginBottom: 24 }}>` **之前**插入：

```tsx
<AgentActivityPanel
  onHandoverClick={(issueId) => {
    window.location.href = `/issues/${issueId}`;
  }}
/>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat(dashboard): embed AgentActivityPanel"
```

---

## Task 11: ActivityTimeline 支持 handover 类型

**Files:**
- Modify: `frontend/src/components/ActivityTimeline.tsx`

- [ ] **Step 1: 扩展 actionIcons 和 actionLabels**

```typescript
// 在现有常量后添加
const typeIcons: Record<string, React.ReactNode> = {
  handover: <MessageOutlined style={{ color: "#faad14" }} />,
};

const typeLabels: Record<string, string> = {
  handover: "交接",
};
```

- [ ] **Step 2: 修改 Timeline items 渲染逻辑**

在 `items` 的 `children` 渲染中，在现有的 Tag 之后添加 handover 标识：

```tsx
children: (
  <div>
    <Tag color={log.actor === "ai_agent" ? "purple" : "blue"}>
      {log.actor === "ai_agent" ? <RobotOutlined /> : <UserOutlined />}
      {log.actor === "ai_agent" ? " AI Agent" : " 用户"}
    </Tag>
    <Tag>{actionLabels[log.action] || log.action}</Tag>
    {/* 新增：如果是 handover 类型活动，额外标识 */}
    {log.new_value?.comment_type === "handover" && (
      <Tag color="orange">🔄 交接</Tag>
    )}
    {log.new_value && log.action === "status_changed" && (
      <span style={{ color: "#666", marginLeft: 8 }}>
        {log.new_value?.status} → {log.new_value.status}
      </span>
    )}
    {/* ... 其余保持原样 ... */}
  </div>
),
```

注意：这里假设 activity_log 的 `new_value` 中包含 `comment_type` 字段。如果后端 activity_log 记录评论创建时不记录 comment_type，则需要在后端 routes/issues.py 的创建评论接口中确保 activity_log 写入时包含此字段。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ActivityTimeline.tsx
git commit -m "feat(activity): highlight handover comments in ActivityTimeline"
```

---

## Task 12: 更新 mcp-config.md 文档

**Files:**
- Modify: `docs/mcp-config.md`

- [ ] **Step 1: 在文档开头添加角色配置说明**

在 `docs/mcp-config.md` 的 "## 一、快速开始" 之前插入新章节：

```markdown
## 零、角色与分工

Project Manager System 支持多角色 Agent 协作：

| 角色 | 职责 | 推荐 IDE | MCP Server |
|------|------|---------|-----------|
| **agent** | 日常开发：编码、创建 issue、完成 plan | Cursor / Trae | `mcp_server.py` |
| **mate** | 架构审查：审查代码、批准 plan | Cline / Windsurf | `mcp_server_mate.py` |
| **tester** | 测试验证：提交 bug、验证修复 | 独立终端 | `mcp_server_tester.py` |
| **registrar** | 项目登记：初始化项目、创建里程碑 | CLI 脚本 | `mcp_server_registrar.py` |

每个角色使用独立的密码，在 `.env` 中配置：

```env
AGENT_PASSWORDS=trae:CHANGE-ME,cursor:cursor-2026,mate:mate-2026,tester:tester-2026,registrar:CHANGE-ME
```
```

- [ ] **Step 2: 添加各角色配置实例**

在 "## 二、内网部署配置" 之后插入新章节：

```markdown
## 三、角色配置实例

### Agent 角色（Cursor）

```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "python",
      "args": ["D:/project-manager-system/backend/mcp_server.py"],
      "env": {
        "PM_API_URL": "http://localhost:8000/api/v1",
        "PM_AGENT_PASSWORD": "cursor-2026"
      }
    }
  }
}
```

### Mate 角色（Cline）

```json
{
  "mcpServers": {
    "pm-mate": {
      "command": "python",
      "args": ["D:/project-manager-system/backend/mcp_server_mate.py"],
      "env": {
        "PM_API_URL": "http://localhost:8000/api/v1",
        "PM_AGENT_PASSWORD": "mate-2026"
      }
    }
  }
}
```

### Tester 角色（HTTP 模式）

```json
{
  "mcpServers": {
    "CHANGE-MEer": {
      "url": "http://localhost:9002/mcp",
      "headers": {
        "X-PM-Password": "tester-2026"
      }
    }
  }
}
```
```

- [ ] **Step 3: 添加协作工具说明**

在 "## 三、可用工具一览" 或原有工具列表后面添加：

```markdown
### 协作工具（新增）

| 工具 | 功能 |
|------|------|
| `notify_role` | 给指定角色发送通知（如通知 mate 审查） |
| `get_handover_template` | 获取交接评论模板（dev_complete / review_feedback / test_report） |

#### notify_role 示例

```
Agent 完成开发后调用：
notify_role(target_role="mate", title="Issue #5 开发完成待审查", entity_type="issue", entity_id=5)
→ Mate 的 check_notifications 会收到此通知
```

#### get_handover_template 示例

```
get_handover_template(template_name="dev_complete")
→ 返回 Markdown 格式的开发完成交接模板
Agent 填写后通过 add_issue_comment(comment_type="handover") 发送
```
```

- [ ] **Step 4: Commit**

```bash
git add docs/mcp-config.md
git commit -m "docs(mcp): add role-based configuration guide and collaboration tools"
```

---

## Task 13: 后端测试

**Files:**
- Create: `backend/tests/test_agent_collaboration.py`

- [ ] **Step 1: 创建测试文件**

```python
import pytest
from httpx import AsyncClient
from asgi_lifespan import LifespanManager

from main import app


@pytest.fixture
async def client():
    async with LifespanManager(app):
        async with AsyncClient(app=app, base_url="http://test") as c:
            yield c


@pytest.mark.asyncio
async def test_notify_role_creates_notification(client: AsyncClient):
    """测试 notify_role 工具通过 API 创建角色通知"""
    # 1. 登录获取 token（使用 admin 密码）
    login_resp = await client.post("/api/v1/auth/login", json={"password": "admin"})
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 创建通知（模拟 notify_role 的行为）
    resp = await client.post("/api/v1/notifications", json={
        "recipient": "mate",
        "type": "role_notification",
        "title": "Test notification for mate",
        "body": "Please review issue #1",
        "entity_type": "issue",
        "entity_id": 1,
    }, headers=headers)
    assert resp.status_code == 201 or resp.status_code == 200
    data = resp.json()
    assert data["recipient"] == "mate"
    assert data["type"] == "role_notification"


@pytest.mark.asyncio
async def test_comment_handover_type(client: AsyncClient):
    """测试 comment_type=handover 的评论创建"""
    login_resp = await client.post("/api/v1/auth/login", json={"password": "admin"})
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 先创建一个 issue
    issue_resp = await client.post("/api/v1/issues", json={
        "title": "Test handover comment",
        "issue_type": "task",
        "priority": "P2",
    }, headers=headers)
    issue_id = issue_resp.json()["id"]

    # 创建 handover 评论
    comment_resp = await client.post(f"/api/v1/issues/{issue_id}/comments", json={
        "content": "## 交接: Issue 开发完成\n\n### 改动范围\n- 文件: test.py",
        "author": "cursor",
        "comment_type": "handover",
    }, headers=headers)
    assert comment_resp.status_code == 201 or comment_resp.status_code == 200
    data = comment_resp.json()
    assert data["comment_type"] == "handover"


@pytest.mark.asyncio
async def test_dashboard_agents_endpoint(client: AsyncClient):
    """测试 Agent 状态聚合 API"""
    login_resp = await client.post("/api/v1/auth/login", json={"password": "admin"})
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/dashboard/agents", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data
    assert "pending_handovers" in data
```

- [ ] **Step 2: 运行测试**

```bash
cd backend
pytest tests/test_agent_collaboration.py -v
```

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_agent_collaboration.py
git commit -m "test: add agent collaboration integration tests"
```

---

## Task 14: 运行完整测试套件

- [ ] **Step 1: 运行后端全部测试**

```bash
cd backend
pytest -v
```

- [ ] **Step 2: 运行前端 lint**

```bash
cd frontend
npm run lint
```

- [ ] **Step 3: 如有失败则修复**

根据测试输出修复问题，然后重复 Step 1-2 直到全部通过。

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: all tests passing for multi-agent collaboration"
```

---

## 自审检查

**1. Spec 覆盖检查：**

| Spec 要求 | 对应 Task |
|-----------|----------|
| 配置层：各 IDE 角色配置手册 | Task 12 |
| 通信机制：notify_role 工具 | Task 4, 5, 6 |
| 通信机制：HANDOVER 评论类型 | Task 2, 4, 5, 6, 11 |
| 交接模板：dev_complete | Task 4, 5, 6 |
| 交接模板：review_feedback | Task 4, 5, 6 |
| 交接模板：test_report | Task 4, 5, 6 |
| 前端：Agent 活动面板 | Task 7, 8, 9, 10 |
| 前端：handover 渲染 | Task 11 |
| 通知路由：角色名过滤 | Task 3 |

✅ 全部覆盖，无遗漏。

**2. Placeholder 扫描：**
- 无 "TBD", "TODO", "implement later"
- 所有代码块包含完整实现
- 所有测试包含具体断言
- 所有文件路径精确

✅ 无占位符。

**3. 类型一致性：**
- `comment_type` 在后端模型、MCP 工具、前端 API 中统一为 `"handover"`
- `NotificationType.ROLE_NOTIFICATION` 在模型、MCP 工具、测试中一致
- AgentStatus 接口字段与后端 API 返回字段匹配

✅ 类型一致。

---

## 执行交接

**Plan complete and saved to `docs/superpowers/plans/2026-06-09-multi-agent-collaboration-plan.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints for review

**Which approach?**
