# Metis PM v2.0 — 精简重构设计

> 状态：待审核 | 日期：2026-06-17 | 版本：v2.0

---

## 一、背景与目标

### 问题

当前 v1.4.0 系统存在过度设计：

- **15 个模型 / 20 个 ORM 类**，大量实体从未使用
- **62 个 MCP 工具**，对个人 AI Agent 协作场景过于庞大
- **3 层 AI 集成**（Copilot 内嵌 + MCP Server + A2A），功能重叠
- **13 个基础设施组件**，对 SQLite 单用户系统过重
- **20 个前端页面**，认知过载

### 目标

将系统从"大而全的 PM 工具"精简为"**AI Agent 协作中枢**"：

- 核心场景：多个 AI Coding Agent 通过各自的角色容器协作管理项目
- Web UI 仅用于人工查看和手动操作
- 用多个 pm-copilot-engine 容器替代 MCP Server + Copilot 内嵌 + A2A

---

## 二、架构概览

```
docker-compose (6 containers)

  agent:9001    mate:9002    tester:9003    registrar:9004
  copilot-eng   copilot-eng  copilot-eng    copilot-eng
  + agent tools + mate tools + tester tools + registrar tools
  + MCP proto   + MCP proto  + MCP proto    + MCP proto
       |              |            |               |
       +--------------+-----+------+---------------+
                             | REST API (httpx)
                       backend:8000
                       纯 CRUD + SQLite
                             |
                       frontend:8080
                       Nginx + React SPA
```

**核心变化：**

| 维度 | v1.4.0 | v2.0 |
|------|--------|------|
| Agent 入口 | MCP Server（httpx 调 REST） | 4 个 pm-copilot-engine 容器，自带 MCP |
| AI 内部能力 | Copilot 内嵌 + A2A + TriggerHub | 无（Agent 容器已覆盖） |
| Backend 角色 | 业务逻辑 + AI 调度 | 纯 CRUD 数据层 |
| 容器数 | 3 | 6 |

---

## 三、数据模型（15 文件 → 6 模型）

```
Project --< Issue --< Comment
  |
  +--< Plan --< PlanItem
  |
  +--< Notification
```

### Project（精简字段）

id, name, slug, description, status(active/archived), created_at, updated_at
砍掉：server_id, git_repo, git_branch, default_assignee

### Issue（精简字段）

id, project_id, title, description, status(open/in_progress/resolved/closed),
priority(P0-P3), issue_type(bug/feature/task), assignee_role, source,
created_at, updated_at
砍掉：milestone_id, server_id, parent_issue_id, due_date

### Comment

id, issue_id, content, author_role, created_at（不变）

### Plan（精简字段）

id, project_id, title, description, status(pending/approved/rejected/in_progress/done),
proposed_by, created_at, updated_at
砍掉：milestone_id, due_date, priority

### PlanItem

id, plan_id, issue_id?, title, status(todo/in_progress/done), sort_order（不变）

### Notification（极简版）

id, target_role, message, is_read, created_at

### 认证简化

JWT 登录 → 共享 API Key：Agent 容器和前端通过 `X-API-Key` header 认证，无需登录页面和 token 刷新逻辑。

Milestone, Workflow(4类), Server, AgentMemory, ProjectRegistration,
Feedback, GitIntegration(3类), RiskAlert, ActivityLog

---

## 四、Agent 容器设计

### 目录结构

```
agents/
  Dockerfile              # 共享
  agent/main.py, tools.py, system_prompt.md
  mate/main.py, tools.py, system_prompt.md
  tester/main.py, tools.py, system_prompt.md
  registrar/main.py, tools.py, system_prompt.md
```

### 共享 Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install pm-copilot-engine httpx
COPY main.py tools.py system_prompt.md ./
CMD ["python", "main.py"]
```

### 各角色工具（总计 ~20，从 62 减少 68%）

**Agent（开发者）~8 工具：**
list_my_issues, get_issue, update_issue_status, add_comment,
propose_plan, update_plan_progress, list_plans, notify_role

**Mate（审查者）~5 工具：**
list_pending_plans, approve_plan, reject_plan, assign_issue, get_project_overview

**Tester（测试者）~4 工具：**
report_bug, request_feature, verify_issue, list_my_issues

**Registrar（登记员）~3 工具：**
create_project, initialize_issues, get_project_context

### 环境变量

BACKEND_URL, PM_MODEL, PM_API_BASE_URL, PM_API_KEY, ROLE, MCP_PORT

---

## 五、Backend 精简

### 路由（22 → 6）

auth(简化为 API Key), projects, issues, plans, comments, notifications

### 基础设施（13 → 3）

database.py, dependencies.py, notification.py(极简，纯 REST CRUD，无 SSE)

### 砍掉

copilot/, a2a/, mcp_server*.py, mcp_tools/, mcp_common.py,
crypto.py, message_queue.py, workflow_engine.py, workflow_timeout.py,
trigger_hub.py, metrics.py, rate_limit.py, debounce.py, webhook_handler.py,
activity.py

---

## 六、前端精简

### 页面（20 → 5）

Dashboard(极简), Issues(列表+看板), IssueDetail, Plans, PlanDetail

### 组件（保留 5）

Layout, IssueCard, PlanItem, LoadingState, ErrorState

---

## 七、docker-compose

6 个服务：backend, frontend, agent, mate, tester, registrar
一个 `docker compose up -d` 全部启动

---

## 八、文件变更清单

### 新增
agents/Dockerfile, agents/{agent,mate,tester,registrar}/{main.py,tools.py,system_prompt.md}

### 删除
backend/copilot/, backend/src/a2a/, backend/mcp_server*.py, backend/mcp_tools/,
backend/mcp_common.py, 10 个 models 文件, 10 个 schemas 文件, 16 个 routes 文件,
7 个 core 文件, 15 个前端页面, 10 个前端组件

### 修改
backend/main.py, backend/pyproject.toml, backend/src/models/__init__.py,
backend/src/schemas/__init__.py, backend/src/routes/__init__.py,
backend/src/models/{project,issue,comment,plan,plan_item}.py（精简字段）,
backend/src/schemas/{project,issue,comment,plan,plan_item}.py（精简字段）,
frontend/src/App.tsx, frontend/src/types/index.ts, frontend/src/services/api.ts,
docker-compose.yml, .env.example, Makefile, CHANGELOG.md, README.md
