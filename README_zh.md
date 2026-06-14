# Metis PM

> [English](README.md)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?style=flat&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=flat" alt="License"></a>
  <a href="https://github.com/wx528/metis-pm/actions/workflows/test.yml"><img src="https://github.com/wx528/metis-pm/actions/workflows/test.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/wx528/metis-pm/actions/workflows/build.yml"><img src="https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker&logoColor=white" alt="Docker"></a>
  <br>
  <img src="https://img.shields.io/badge/AI-pm--copilot--engine-722ED1?style=flat&logo=openai&logoColor=white" alt="AI Engine">
  <img src="https://img.shields.io/badge/MCP-Streamable%20HTTP-0078D4?style=flat" alt="MCP">
</p>

人机协作项目管理系统 — 专为 **用户 + AI Coding Agent** 协同管理项目而设计。

## 核心理念

这个系统不是给团队用的，而是给 **你和一个 AI Coding Agent** 一起用的：
- 你和 Agent 都可以录入 issues、设定 plan、标记优先级
- 你说"这个先不管"，Agent 会把 issue 标记为 deferred 并推迟到后期阶段
- Agent 发现问题可以自动创建 issue 并标记来源为 `ai_agent`
- 你和 Agent 可以对同一个 issue 添加各自的评论

## 快速启动

### 环境要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip
- Node.js 20+

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` — 以下三项**必填**：

```env
# 1. JWT 签名密钥（随机 32+ 字符）
SECRET_KEY=your-random-secret-key-here-min-32-chars

# 2. 管理员密码哈希
#    生成: python -c "import bcrypt; print(bcrypt.hashpw(b'your-password'.encode(), bcrypt.gensalt()).decode())"
ADMIN_PASSWORD_HASH=$2b$12$...

# 3. Fernet 加密密钥（加密服务器凭据）
#    生成: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=...
```

### 2. 启动后端

```bash
cd backend
uv sync                    # 安装依赖
uv run python main.py      # 启动服务
# API: http://localhost:8000
# Swagger 文档: http://localhost:8000/docs
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
# 前端: http://localhost:5173
# API 请求自动代理到 localhost:8000
```

### Docker 一键启动

```bash
docker compose up -d
# 前端: http://localhost:8080
# API:  http://localhost:8000
```

## 系统架构

```
┌─────────────┐     HTTP API      ┌─────────────┐     SQLite
│  React 前端  │ ◄──────────────► │ FastAPI 后端 │ ◄────────►
│  (你用的)    │                   │             │  metis_pm.db
└─────────────┘                   └──────┬──────┘
                                        │
                                  ┌─────┴──────┐
                                  │ TriggerHub  │ ← 系统事件
                                  │  Copilot    │ ← pm-copilot-engine（可选）
                                  │  A2A Client │ ← 外部 Agent（可选）
                                  └─────┬──────┘
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

| 模式 | 端点 | 说明 |
|------|------|------|
| **Streamable HTTP** | `http://host:9000/mcp` | **推荐**，内网 Agent 直连，配置简单 |
| SSE | `http://host:9000/sse` | 旧版客户端兼容 |

IDE MCP 配置示例：

```json
{
  "mcpServers": {
    "pm-agent": {
      "url": "http://192.168.1.100:9000/mcp",
      "headers": { "X-PM-Password": "CHANGE-ME" }
    },
    "pm-mate": {
      "url": "http://192.168.1.100:9001/mcp",
      "headers": { "X-PM-Password": "CHANGE-ME" }
    }
  }
}
```

### 多身份认证

每个 Agent 通过独立密码识别身份，ActivityLog 精确追踪谁做了什么：

```env
AGENT_PASSWORDS=agent-a:CHANGE-ME:agent,mate:CHANGE-ME:mate
```

### AI Copilot（可选）

Metis PM 可通过 [pm-copilot-engine](https://pypi.org/project/pm-copilot-engine/) 增强 AI 能力：

```env
PM_COPILOT_ENABLED=true
PM_API_BASE_URL=https://api.openai.com/v1
PM_API_KEY=sk-...
PM_MODEL=gpt-4o
```

启用后 Copilot 可以：
- 自主执行项目健康巡检
- 回答项目相关问题
- 自动创建风险告警
- 生成日报/周报

关闭时（`PM_COPILOT_ENABLED=false`），系统作为完整独立的 PM 工具运行 — 零 AI 依赖。

**故障隔离**：Copilot 方法（`scan`、`ask`）均包裹 try/except — AI 引擎崩溃不影响 PM 系统 API 正常服务。

### A2A 协议（可选）

Metis PM 支持 [A2A（Agent-to-Agent）协议](https://github.com/google/A2A)，可向外部 AI Agent 委派任务：

```env
A2A_ENABLED=true
A2A_AGENTS=code-reviewer:http://localhost:3100,risk-analyzer:http://remote-server:3100
```

启用后，高优先级事件（P0 Issue、风险告警、超期里程碑）会自动通过 A2A 委派给匹配的外部 Agent。PM 系统仅作为 A2A Client，无需开放入站端口。

| A2A 端点 | 说明 |
|----------|------|
| `GET /api/v1/a2a/agent-card` | PM 系统的 Agent Card |
| `GET /api/v1/a2a/agents` | 列出已注册 Agent |
| `POST /api/v1/a2a/agents` | 注册 Agent（需 admin） |
| `POST /api/v1/a2a/discover` | 自动发现 Agent |
| `POST /api/v1/a2a/delegate` | 委派任务 |

### TriggerHub

TriggerHub 是事件调度中心，将系统事件连接到 Copilot 和 A2A Agent：

```
系统事件（P0 Issue / 风险 / 超期）
  → TriggerHub.fire_event()
    → _dispatch_to_copilot()   → Copilot 内部处理
    → _dispatch_to_a2a()       → 查找匹配的外部 Agent → 委派任务
```

## MCP 工具

Agent 通过 MCP 协议与系统交互，以下是核心工具：

| 工具 | 说明 |
|------|------|
| `get_context` | 【首选入口】全局态势感知：一次调用返回项目概览、紧急告警、待审批计划、最近活动 |
| `create_issue` | 创建 Issue |
| `list_issues` | 查询 Issue 列表 |
| `update_issue_status` | 更新 Issue 状态 |
| `update_issue_priority` | 更新 Issue 优先级 |
| `defer_issue` | 暂缓 Issue 到后期阶段 |
| `undefer_issue` | 取消暂缓，恢复为 open |
| `add_issue_comment` | 添加评论 |
| `list_comments` | 查看评论列表 |
| `propose_plan` | 提议 Plan |
| `list_plans` | 查询 Plan 列表 |
| `update_plan_progress` | 更新 Plan 进度 |
| `check_notifications` | 检查通知 |
| `mark_notification_read` | 标记通知已读 |
| `list_milestones` | 查询里程碑列表 |
| `create_milestone` | 创建里程碑 |
| `list_servers` | 查询服务器列表 |
| `get_server_credentials` | 获取服务器凭据（仅 admin） |
| `list_workflows` | 查询工作流列表 |
| `create_workflow` | 创建工作流 |
| `trigger_workflow` | 手动触发工作流 |
| `list_workflow_runs` | 查询工作流执行记录 |

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

### Risk Alert（风险告警）

| 字段 | 说明 |
|------|------|
| `title` | 告警标题 |
| `level` | critical / high / medium / low |
| `source` | manual / copilot / system |
| `status` | open / acknowledged / resolved / dismissed |
| `suggested_action` | 建议措施 |

## 前端页面

| 页面 | 功能 |
|------|------|
| Dashboard | P0/P1 issues、待审批计划、服务器状态概览、最近活动时间线 |
| Issues | 列表（筛选+排序+分页）、新建、详情（含评论）、暂缓 |
| Graph View | 力导向图展示项目功能结构（类似 Obsidian） |
| Milestones | 阶段卡片、issue 统计 |
| Plans | 计划列表（含进度条）、审批操作、详情 checklist |
| Servers | 服务器列表、添加、查看凭据 |
| Risk Alerts | 告警列表、创建、解决、按级别/状态筛选 |

## API 接口

> 所有接口均需 JWT 认证（`Authorization: Bearer <token>`）

### Auth
```
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

### Issues
```
GET    /api/v1/issues
POST   /api/v1/issues
GET    /api/v1/issues/{id}
PUT    /api/v1/issues/{id}
DELETE /api/v1/issues/{id}
POST   /api/v1/issues/{id}/defer
POST   /api/v1/issues/{id}/comments
```

### Milestones
```
GET    /api/v1/milestones
POST   /api/v1/milestones
GET    /api/v1/milestones/{id}
PUT    /api/v1/milestones/{id}
DELETE /api/v1/milestones/{id}
```

### Plans
```
GET    /api/v1/plans
POST   /api/v1/plans
GET    /api/v1/plans/{id}
PUT    /api/v1/plans/{id}
POST   /api/v1/plans/{id}/approve
POST   /api/v1/plans/{id}/reject
DELETE /api/v1/plans/{id}
GET    /api/v1/plans/{id}/items
POST   /api/v1/plans/{id}/items
PUT    /api/v1/plans/{id}/items/{item_id}
DELETE /api/v1/plans/{id}/items/{item_id}
```

### Risk Alerts
```
GET    /api/v1/risk-alerts
POST   /api/v1/risk-alerts
GET    /api/v1/risk-alerts/{id}
PUT    /api/v1/risk-alerts/{id}
POST   /api/v1/risk-alerts/{id}/resolve
DELETE /api/v1/risk-alerts/{id}
```

### Copilot
```
POST   /api/v1/copilot/chat
POST   /api/v1/copilot/scan
GET    /api/v1/copilot/status
```

### A2A（Agent-to-Agent）
```
GET    /api/v1/a2a/agent-card
GET    /api/v1/a2a/agents
POST   /api/v1/a2a/agents
POST   /api/v1/a2a/discover
POST   /api/v1/a2a/delegate
POST   /api/v1/a2a/tasks
```

## 安全说明

| 措施 | 说明 |
|------|------|
| JWT 认证 | 所有 API 端点需携带 Bearer Token |
| 凭据隔离 | 服务器密码/SSH Key 不在列表/详情接口返回，通过独立接口获取 |
| CORS 限制 | 通过 `CORS_ORIGINS` 环境变量配置允许的来源 |
| 密钥强制 | `SECRET_KEY` 和 `ADMIN_PASSWORD` 必须在 `.env` 中设置，无默认值 |
| MCP 多身份 | 每个 Agent 通过独立密码连接 MCP Server |
| MCP Token 缓存 | 按密码缓存 JWT，401 自动清缓存重登录 |
| LIKE 转义 | 搜索接口转义 `%`、`_`、`\` 防止通配符注入 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), SQLite, JWT |
| 前端 | React 19, TypeScript, Ant Design 6, Vite, React Router 7 |
| MCP | FastMCP, httpx |
| AI 引擎 | pm-copilot-engine（可选） |
| 部署 | Docker, Docker Compose, Nginx, Helm |

## 许可证

MIT
