# Metis PM

人机协作项目管理系统 — 专为 **用户 + AI Coding Agent** 协同管理项目而设计。

## 快速启动

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，**必须设置**以下变量：

```env
SECRET_KEY=your-random-secret-key-here-min-32-chars
ADMIN_PASSWORD=your-secure-password
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
# API: http://localhost:8000
# Swagger 文档: http://localhost:8000/docs
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
# 前端: http://localhost:5173
# 自动代理 API 请求到 localhost:8000
```

### Docker 一键启动

```bash
docker compose up -d
# 前端: http://localhost:8080
# API:  http://localhost:8000
```

## 核心理念

这个系统不是给团队用的，而是给 **你和一个 AI Coding Agent** 一起用的：
- 你和 Agent 都可以录入 issues、设定 plan、标记优先级
- 你说"这个先不管"，Agent 会把 issue 标记为 deferred 并推迟到后期阶段
- Agent 发现问题可以自动创建 issue 并标记来源为 `ai_agent`
- 你和 Agent 可以对同一个 issue 添加各自的评论

## 系统架构

```
┌─────────────┐     HTTP API      ┌─────────────┐     SQLite
│  React 前端  │ ◄──────────────► │ FastAPI 后端 │ ◄────────►
│  (你用的)    │                   │             │  metis_pm.db
└─────────────┘                   └──────┬──────┘
                                         │
                                    MCP Server (Streamable HTTP)
                                    ┌─────┴──────┐
                                    │  统一入口   │ :9000
                                    │ 角色自动识别 │ ← X-PM-Password
                                    └─────┬──────┘
                                 ┌────────┼────────┐
                                 │        │        │
                            ┌────┴──┐ ┌──┴───┐ ┌──┴────┐
                            │ Agent │ │ Mate │ │Tester │
                            │  trae │ │ cline│ │ (qa)  │
                            └───────┘ └──────┘ └───────┘
```

### MCP 传输模式（推荐 Streamable HTTP）

本项目**默认且推荐**使用 **Streamable HTTP** 模式，适合内网/远程部署，各 IDE 无需安装本地脚本：

| 模式 | 端点 | 说明 |
|------|------|------|
| **Streamable HTTP** | `http://host:9000/mcp` | **推荐**，内网 Agent 直连，配置简单 |
| SSE | `http://host:9000/sse` | 旧版客户端兼容 |

所有角色的 MCP Server 均通过 HTTP 暴露，IDE 只需填写 URL 和密码即可连接：

```json
{
  "mcpServers": {
    "pm-agent": {
      "url": "http://192.168.1.100:9000/mcp",
      "headers": { "X-PM-Password": "CHANGE-ME" }
    },
    "pm-mate": {
      "url": "http://192.168.1.100:9001/mcp",
      "headers": { "X-PM-Password": "mate-2026" }
    }
  }
}
```

### 多身份认证

每个 Agent 通过独立密码识别身份，ActivityLog 精确追踪谁做了什么：

```env
# .env
AGENT_PASSWORDS=trae:CHANGE-ME,mate:mate-2026,tester:tester-2026
```

HTTP 模式通过 `X-PM-Password` 请求头传递密码。

## MCP 工具

Agent 通过 MCP 协议与系统交互，以下是核心工具：

| 工具 | 说明 |
|------|------|
| `get_context` | 【首选入口】全局态势感知：一次调用返回项目概览、紧急告警、待审批计划、最近活动、我的状态 |
| `create_issue` | 创建 Issue（返回完整对象含描述、时间等） |
| `list_issues` | 查询 Issue 列表（含描述、时间、负责人、推迟信息） |
| `update_issue_status` | 更新 Issue 状态 |
| `update_issue_priority` | 更新 Issue 优先级 |
| `defer_issue` | 暂缓 Issue 到后期阶段 |
| `undefer_issue` | 取消暂缓，恢复 deferred Issue 为 open |
| `add_issue_comment` | 添加评论（返回评论 ID、作者、时间） |
| `list_comments` | 查看 Issue 评论列表（回溯讨论历史） |
| `propose_plan` | 提议 Plan（返回完整对象含描述、时间） |
| `list_plans` | 查询 Plan 列表（含描述、拒绝原因、审批信息、进度统计） |
| `update_plan_progress` | 更新 Plan 进度（仅 active/completed 状态可操作） |
| `check_notifications` | 检查通知 |
| `mark_notification_read` | 标记通知已读 |
| `list_milestones` | 查询里程碑列表 |
| `create_milestone` | 创建里程碑 |
| `list_servers` | 查询服务器列表 |
| `get_server_credentials` | 获取服务器凭据（仅 admin） |
| `list_workflows` | 查询工作流列表（含步骤概要） |
| `create_workflow` | 创建工作流 |
| `trigger_workflow` | 手动触发工作流 |
| `list_workflow_runs` | 查询工作流执行记录 |

> `get_context` 是 Agent 入口首选工具，替代多次 `list_issues` + `list_plans` + `check_notifications` 调用。

## 数据模型

### Issue（问题/需求/缺陷）

| 字段 | 说明 |
|------|------|
| `title` | 标题 |
| `description` | 详细描述 |
| `issue_type` | bug / feature / task / improvement / documentation |
| `status` | open / in_progress / review / **deferred** / closed / cancelled |
| `priority` | **P0** / **P1** / **P2** / **P3** |
| `source` | **user** / **ai_agent** / **collaborative** |
| `milestone_id` | 所属阶段 |
| `deferred_to_milestone_id` | 推迟到哪个阶段 |
| `deferred_reason` | 推迟原因 |

### Milestone（阶段/分期）

| 字段 | 说明 |
|------|------|
| `title` | 阶段名称 |
| `phase` | 分期标识，如 `phase-1`、`MVP` |
| `status` | open / closed |

### Plan（计划）— 含审批流

| 字段 | 说明 |
|------|------|
| `title` | 计划名称 |
| `status` | draft / **pending_approval** / active / completed / abandoned |
| `proposed_by` | 谁提议的：user / ai_agent |
| `approved_by` | 谁审批的 |
| `reject_reason` | 拒绝原因 |

**审批流：**
```
Agent 提议 → pending_approval → 你点击"审批通过" → active → Agent 更新进展
                     ↓
              你点击"拒绝" → abandoned（可填写拒绝原因）
```

### PlanItem（计划项/Checklist）

| 字段 | 说明 |
|------|------|
| `title` | 项标题 |
| `status` | pending / in_progress / **done** / blocked |
| `completed_by` | user / ai_agent |

### Server（服务器/基础设施）

| 字段 | 说明 |
|------|------|
| `name` | 服务器名称 |
| `ip_address` | IP |
| `username` | 用户名 |
| `has_password` / `has_ssh_key` | 凭据标志（不暴露实际值） |
| `status` | active / maintenance / offline / decommissioned |
| `environment` | production / staging / development |

> 凭据通过 `GET /api/v1/servers/{id}/credentials` 单独接口获取，列表和详情接口不返回敏感信息。

## 前端页面

| 页面 | 功能 |
|------|------|
| Dashboard | P0/P1 issues、待审批计划、服务器状态概览、最近活动时间线 |
| Issues | 列表（筛选+排序+分页）、新建、详情（含评论）、暂缓 |
| Milestones | 阶段卡片、issue 统计 |
| Plans | 计划列表（含进度条）、审批操作、详情 checklist |
| Servers | 服务器列表、添加、查看凭据 |

## API 接口

> 所有接口均需 JWT 认证（`Authorization: Bearer <token>`）

### Auth
```
POST /api/v1/auth/login          # 登录
GET  /api/v1/auth/me             # 当前用户
```

### Issues
```
GET    /api/v1/issues                    # 列表（支持筛选、排序、分页）
POST   /api/v1/issues                    # 创建
GET    /api/v1/issues/{id}               # 详情（含评论）
PUT    /api/v1/issues/{id}               # 更新
DELETE /api/v1/issues/{id}               # 删除
POST   /api/v1/issues/{id}/defer         # 暂缓
POST   /api/v1/issues/{id}/comments      # 添加评论
```

### Milestones
```
GET    /api/v1/milestones                # 列表（含统计）
POST   /api/v1/milestones                # 创建
GET    /api/v1/milestones/{id}           # 详情（含统计）
PUT    /api/v1/milestones/{id}           # 更新
DELETE /api/v1/milestones/{id}           # 删除
```

### Plans
```
GET    /api/v1/plans                     # 列表（含进度统计）
POST   /api/v1/plans                     # 创建
GET    /api/v1/plans/{id}                # 详情（含 plan_items）
PUT    /api/v1/plans/{id}                # 更新
POST   /api/v1/plans/{id}/approve        # 审批通过
POST   /api/v1/plans/{id}/reject         # 拒绝（可选 reason 参数）
DELETE /api/v1/plans/{id}                # 删除
GET    /api/v1/plans/{id}/items          # 计划项列表
POST   /api/v1/plans/{id}/items          # 添加计划项
PUT    /api/v1/plans/{id}/items/{item_id} # 更新计划项
DELETE /api/v1/plans/{id}/items/{item_id} # 删除计划项
```

### Servers
```
GET    /api/v1/servers                   # 列表（不含凭据）
POST   /api/v1/servers                   # 创建
GET    /api/v1/servers/{id}              # 详情（不含凭据）
PUT    /api/v1/servers/{id}              # 更新
DELETE /api/v1/servers/{id}              # 删除
GET    /api/v1/servers/{id}/credentials  # 获取凭据
POST   /api/v1/servers/{id}/check        # 手动检查
```

### Dashboard
```
GET    /api/v1/dashboard                 # 聚合统计数据
```

## 安全说明

| 措施 | 说明 |
|------|------|
| JWT 认证 | 所有 API 端点需携带 Bearer Token |
| 凭据隔离 | 服务器密码/SSH Key 不在列表/详情接口返回，通过独立接口获取 |
| CORS 限制 | 通过 `CORS_ORIGINS` 环境变量配置允许的来源 |
| 密钥强制 | `SECRET_KEY` 和 `ADMIN_PASSWORD` 必须在 `.env` 中设置，无默认值 |
| MCP 多身份 | 每个 Agent 通过独立密码连接 MCP Server，HTTP 模式使用 `X-PM-Password` 请求头 |
| MCP Token 缓存 | 按密码缓存 JWT，401 自动清缓存重登录 |
| LIKE 转义 | 搜索接口转义 `%`、`_`、`\` 防止通配符注入 |

## 典型工作流

### 1. 创建项目分期
```bash
curl -X POST http://localhost:8000/api/v1/milestones \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"title": "Phase 1 - 基础功能", "phase": "phase-1"}'
```

### 2. 录入 Issue（人/Agent 各自标记来源）
```bash
# 你创建一个 P1 issue
curl -X POST http://localhost:8000/api/v1/issues \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"title": "登录页面无法跳转", "issue_type": "bug", "priority": "P1", "source": "user"}'

# AI Agent 发现一个优化点
curl -X POST http://localhost:8000/api/v1/issues \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"title": "搜索接口可加缓存", "issue_type": "improvement", "priority": "P3", "source": "ai_agent"}'
```

### 3. 暂缓不需要现在处理的 Issue
```bash
curl -X POST "http://localhost:8000/api/v1/issues/2/defer?deferred_to_milestone_id=2&deferred_reason=当前阶段聚焦核心功能" \
  -H "Authorization: Bearer <token>"
```

### 4. Agent 提议计划，你审批
```bash
# Agent 提议
curl -X POST http://localhost:8000/api/v1/plans \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"title": "重构认证模块", "proposed_by": "ai_agent", "status": "pending_approval"}'

# 你审批通过
curl -X POST http://localhost:8000/api/v1/plans/1/approve \
  -H "Authorization: Bearer <token>"

# 或拒绝并说明原因
curl -X POST "http://localhost:8000/api/v1/plans/1/reject" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"reason": "优先级不足"}'
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), SQLite, JWT |
| 前端 | React 19, TypeScript, Ant Design 6, Vite, React Router 7 |
| MCP | FastMCP, httpx |
| 部署 | Docker, Docker Compose, Nginx |
