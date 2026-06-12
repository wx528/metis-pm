# Project Manager System 架构文档

> 人机协作项目管理系统架构设计
> 版本: 1.3.0
> 更新日期: 2026-06-12

---

## 1. 系统概述

Project Manager System 是一个专为 **用户 + 多个 AI Coding Agent** 协同管理项目而设计的系统。它不仅仅是一个项目管理工具，更是一个让不同角色的 AI Agent（开发、审查、测试、登记）能够有序协作、交接工作、互相通知的协作平台。

### 核心设计理念

- **多 Agent 协作**：支持多个编程工具（Cursor、Trae、Cline 等）同时接入，每个分配明确角色
- **角色分工**：agent（开发）、mate（审查）、tester（测试）、registrar（登记）
- **工作流驱动**：Agent 之间通过通知和交接评论完成状态流转；工作流引擎支持条件分支、并行执行、模板
- **内网优先**：基于 Streamable HTTP 的 MCP 传输，适合局域网/Tailscale 部署
- **容错优先**：消息队列 + SQLite 持久化备份，API 不可用时自动降级；工作流超时自动检测

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户层                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Cursor     │  │    Trae      │  │    Cline     │          │
│  │  (agent)     │  │   (agent)    │  │   (mate)     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           │ MCP Streamable HTTP                 │
│                           ▼                                     │
│              ┌────────────────────────┐                        │
│              │     浏览器 (Dashboard)  │                        │
│              └───────────┬────────────┘                        │
└──────────────────────────┼────────────────────────────────────┘
                           │ HTTP API / SSE
┌──────────────────────────┼────────────────────────────────────┐
│                          ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                   FastAPI 后端                           │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │  │
│  │  │ Issues  │  │  Plans  │  │Milestones│  │ Servers │   │  │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘   │  │
│  │       └─────────────┴─────────────┴─────────────┘        │  │
│  │                         │                                │  │
│  │  ┌──────────────────────┤                                │  │
│  │  │  核心基础设施         │                                │  │
│  │  │  • WorkflowEngine    │                                │  │
│  │  │  • MessageQueue      │                                │  │
│  │  │  • WorkflowTimeout   │                                │  │
│  │  │  • Notification+SSE  │                                │  │
│  │  │  • ActivityLog       │                                │  │
│  │  │  • Prometheus Metrics│                                │  │
│  │  └──────────────────────┤                                │  │
│  │                         │                                │  │
│  │              ┌──────────┴──────────┐                    │  │
│  │              │    SQLAlchemy ORM   │                    │  │
│  │              └──────────┬──────────┘                    │  │
│  │                         ▼                                │  │
│  │                   ┌──────────┐                          │  │
│  │                   │  SQLite  │                          │  │
│  │                   │ (WAL模式) │                          │  │
│  │                   └──────────┘                          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                           │                                    │
│                           ▼                                    │
│                   ┌──────────────┐                            │
│                   │  mcp:9000    │                            │
│                   │ 统一 Server  │                            │
│  ┌────────────────┤ (模块化)     ├────────────────┐          │
│  │ shared (16)    │              │ agent (19)     │          │
│  │ mate (7)       │              │ tester (7)     │          │
│  │ registrar (6)  │              │                │          │
│  └────────────────┴──────────────┴────────────────┘          │
└──────────────────────────────────────────────────────────────┘
```

### 服务矩阵

| 服务 | 容器名 | 端口 | 说明 |
|------|--------|------|------|
| backend | pm-backend | 8000 | FastAPI REST API + Prometheus /metrics |
| frontend | pm-frontend | 8080 | React SPA (Nginx) |
| mcp | pm-mcp | 9000 | 统一 MCP Server（4 角色共用，模块化工具） |

---

## 3. 后端架构

### 3.1 技术栈

- **框架**: FastAPI 0.115 (Python 3.11)
- **ORM**: SQLAlchemy 2.0 (async)
- **数据库**: SQLite + aiosqlite (WAL 模式)
- **认证**: JWT (PyJWT) + bcrypt 密码哈希
- **加密**: Fernet (cryptography) — 服务器凭据加密
- **监控**: Prometheus (prometheus-fastapi-instrumentator)
- **测试**: pytest + pytest-asyncio

### 3.2 项目结构

```
backend/
├── main.py                  # FastAPI 入口 + 数据库迁移 + 后台任务
├── mcp_server_unified.py    # 统一 MCP Server 入口（123 行）
├── mcp_common.py            # MCP 共享模块（认证、API 请求、中间件）
├── mcp_tools/               # MCP 工具包（按角色拆分）
│   ├── __init__.py          # register_all_tools() 统一注册
│   ├── shared.py            # 16 个共享工具（所有角色可用）
│   ├── agent.py             # 19 个 Agent 专属工具
│   ├── mate.py              # 7 个 First Mate 专属工具
│   ├── tester.py            # 7 个 Tester 专属工具
│   └── registrar.py         # 6 个 Registrar 专属工具
├── src/
│   ├── settings.py          # 全局配置（bcrypt 哈希密码、Pydantic BaseSettings）
│   ├── core/
│   │   ├── database.py      # SQLAlchemy 异步引擎 + WAL 模式 PRAGMA
│   │   ├── dependencies.py  # 依赖注入（get_db, get_current_user）
│   │   ├── crypto.py        # Fernet 加密工具
│   │   ├── activity.py      # 活动日志
│   │   ├── notification.py  # 通知 + SSE 推送
│   │   ├── message_queue.py # 内存消息队列 + SQLite 持久化备份
│   │   ├── workflow_engine.py # 工作流引擎（条件分支/并行/模板）
│   │   ├── workflow_timeout.py # 工作流超时检测（5 分钟无进展自动 failed）
│   │   └── metrics.py       # Prometheus 业务指标
│   ├── models/              # SQLAlchemy ORM（14 个实体）
│   ├── schemas/             # Pydantic 请求/响应模型
│   └── routes/              # FastAPI 路由（16 个模块）
└── tests/                   # 集成测试
```

### 3.3 三层分离

```
┌─────────────┐
│   routes/   │  ← API 层：组合 models + schemas，业务逻辑
├─────────────┤
│  schemas/   │  ← 验证/序列化层：Pydantic，不做数据库操作
├─────────────┤
│  models/    │  ← 数据层：ORM 定义，不包含业务逻辑
└─────────────┘
```

### 3.4 核心实体

| 实体 | 说明 | 关键字段 |
|------|------|----------|
| Project | 项目 | slug, status, owner |
| Issue | 问题/需求/缺陷 | status, priority, source, milestone_id, created_by |
| Plan | 计划（含审批流） | status, proposed_by, approved_by, reject_reason |
| PlanItem | 计划项/Checklist | status, completed_by |
| Milestone | 阶段/分期 | phase, status, due_date |
| Comment | 评论（含交接类型） | comment_type (normal/management/handover), read_by, read_at |
| Notification | 通知 | recipient, type, read |
| ActivityLog | 活动日志 | actor, action, entity_type |
| Server | 服务器/基础设施 | ip_address, credentials (Fernet 加密) |
| Workflow | 工作流 | trigger, trigger_config, status |
| WorkflowStep | 工作流步骤 | step_type, condition, next_step_id, parallel_group |
| WorkflowRun | 工作流执行实例 | status, context, error_message |
| AgentMemory | Agent 记忆 | agent_id, key, value |
| ProjectRegistration | 项目登记 | path, tech_stack, repo_url, language, framework |

### 3.5 核心基础设施

#### 工作流引擎 (WorkflowEngine)

支持 5 种步骤类型、4 种触发方式，以及条件分支和并行执行：

```
┌─────────────────────────────────────────────────────────────┐
│  WorkflowEngine 特性                                         │
│  • 步骤类型: create_issue, update_issue, notify,            │
│    wait_approval, propose_plan                              │
│  • 触发方式: on_issue_created, on_plan_approved,            │
│    on_schedule, manual                                      │
│  • 条件分支: condition 表达式 → next_step_id / else_step_id │
│  • 并行执行: parallel_group 标识 → asyncio.gather           │
│  • 失败策略: skip / retry (指数退避) / abort / notify_human │
│  • 模板: GET /workflows/templates, POST /workflows/         │
│    from-template/{id}                                       │
│  • 超时检测: 5 分钟无进展 → 自动 failed + 通知 admin         │
└─────────────────────────────────────────────────────────────┘
```

#### 消息队列 (MessageQueue)

```
┌─────────────────────────────────────────────────────────────┐
│  MessageQueue 特性                                           │
│  • 内存缓冲: asyncio.Queue (maxsize=1000)                   │
│  • 持久化备份: 内存满时写入 SQLite message_queue_backup 表   │
│  • 自动消费: 后台消费者持续处理，API 恢复后自动重试          │
│  • 降级策略: 通知发送失败 → 入队 → 恢复后重试               │
└─────────────────────────────────────────────────────────────┘
```

#### 安全设计

| 措施 | 说明 |
|------|------|
| bcrypt 密码哈希 | ADMIN_PASSWORD_HASH + AGENT_PASSWORDS_JSON (bcrypt hash) |
| JWT 认证 | 所有 API 端点需携带 Bearer Token |
| Fernet 凭据加密 | 服务器密码/SSH Key 加密存储，列表接口不返回敏感信息 |
| CORS 限制 | 通过 `CORS_ORIGINS` 环境变量配置允许的来源 |
| LIKE 转义 | 搜索接口转义 `%`、`_`、`\` 防止通配符注入 |
| MCP Token 缓存 | 按密码缓存 JWT，401 自动清缓存重登录 |
| MCP 指数退避重试 | 连接/超时错误自动重试 3 次（1s → 2s → 4s） |
| RBAC 隔离 | MCP 工具按角色隔离，require_role 装饰器 |

---

## 4. 前端架构

### 4.1 技术栈

- **框架**: React 19 + TypeScript
- **UI 组件**: Ant Design 6
- **构建工具**: Vite 8
- **路由**: React Router 7
- **HTTP 客户端**: axios
- **状态管理**: React Context (useProject, useAuth, useNotifications) + React Query
- **拖拽**: @dnd-kit/core + @dnd-kit/sortable

### 4.2 项目结构

```
frontend/src/
├── main.tsx                    # 入口
├── App.tsx                     # 路由定义（含项目 slug 路由）
├── api/                        # API 调用层
│   ├── client.ts              # axios 实例 + 拦截器（401 自动跳转登录）
│   ├── agentStatus.ts         # Agent 状态 API
│   ├── issues.ts, plans.ts, milestones.ts, ...
│   └── index.ts               # 统一导出
├── components/                 # 可复用组件
│   ├── AgentActivityPanel.tsx # Agent 协作看板
│   ├── ActivityTimeline.tsx   # 活动时间线
│   ├── BoardColumn.tsx        # 看板列组件（@dnd-kit droppable）
│   ├── IssueCard.tsx          # 看板卡片组件（@dnd-kit sortable）
│   ├── Layout.tsx             # 全局布局（侧栏+导航+通知+资源管理）
│   └── ui/                    # 通用 UI 组件
│       ├── LoadingState.tsx
│       └── ErrorState.tsx
├── hooks/                      # 自定义 Hooks
│   ├── useAuth.tsx            # 认证状态（localStorage 持久化）
│   ├── useProject.tsx         # 项目切换（Context + localStorage）
│   ├── useNotifications.tsx   # 通知（轮询 30s + SSE 实时推送）
│   ├── useDashboard.ts        # Dashboard 数据（React Query）
│   ├── useIssues.ts           # Issues 数据（React Query）
│   ├── usePlans.ts            # Plans 数据（React Query）
│   └── useWorkflows.ts        # Workflows 数据（React Query）
├── pages/                      # 页面组件
│   ├── Dashboard.tsx          # 仪表盘（Agent 看板 + 统计 + 产出对比）
│   ├── Board.tsx              # 看板视图（5 列拖拽，里程碑筛选）
│   ├── Issues.tsx             # Issue 列表（筛选+排序+分页）
│   ├── IssueDetail.tsx        # Issue 详情（评论、暂缓）
│   ├── Plans.tsx              # 计划列表（审批操作、进度条）
│   ├── PlanDetail.tsx         # 计划详情（Checklist）
│   ├── Milestones.tsx         # 里程碑卡片
│   ├── Servers.tsx            # 服务器管理
│   ├── Workflows.tsx          # 工作流管理
│   ├── Projects.tsx           # 项目管理
│   ├── ProjectRegistrations.tsx # 项目登记
│   └── Login.tsx              # 登录页
├── queries/                    # React Query 配置
│   ├── queryClient.ts         # QueryClient 实例（30s staleTime）
│   ├── dashboardQueries.ts    # Dashboard query keys
│   ├── issueQueries.ts        # Issue query keys
│   ├── planQueries.ts         # Plan query keys
│   └── workflowQueries.ts     # Workflow query keys
└── index.css                   # 全局样式
```

### 4.3 页面与功能

| 页面 | 功能 |
|------|------|
| Dashboard | P0/P1 issues、待审批计划、服务器状态、Agent 协作看板、Agent 产出对比、Plan 完成率 |
| Board | 5 列看板（Open/In Progress/Review/Deferred/Closed）、拖拽改状态、里程碑筛选 |
| Issues | 列表（筛选+排序+分页）、新建、详情（含评论/线程回复）、暂缓 |
| Plans | 计划列表（含进度条）、审批操作、详情 checklist |
| Milestones | 阶段卡片、issue 统计 |
| Servers | 服务器列表、添加、查看凭据 |
| Workflows | 工作流列表、创建、触发、模板 |
| Projects | 项目管理（跨项目） |
| ProjectRegistrations | 项目登记（散落项目收集） |

### 4.4 状态管理架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端状态管理                           │
│                                                         │
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │ React Context    │  │ React Query                  │ │
│  │ (全局 UI 状态)    │  │ (服务端数据缓存)              │ │
│  │                  │  │                              │ │
│  │ • useAuth        │  │ • useDashboard               │ │
│  │   token/sub/role │  │ • useIssues                  │ │
│  │ • useProject     │  │ • usePlans                   │ │
│  │   currentProject │  │ • useWorkflows               │ │
│  │ • useNotifications│  │ staleTime: 30s              │ │
│  │   SSE + 轮询     │  │ refetchOnWindowFocus: true   │ │
│  └──────────────────┘  └──────────────────────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ localStorage 持久化                               │   │
│  │ token / sub / role / currentProject /             │   │
│  │ currentProjectSlug / pm_global_resources          │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 5. MCP 架构

### 5.1 设计原则

- **统一传输**: 全部使用 Streamable HTTP，适合内网部署
- **统一入口**: 所有角色通过同一个端口 9000 接入，密码区分身份
- **模块化工具**: 按角色拆分为独立模块（shared/agent/mate/tester/registrar）
- **容错机制**: safe_tool 装饰器捕获异常防止 MCP Server 崩溃
- **内网优先**: IDE 无需安装本地脚本，直接通过 HTTP 连接

### 5.2 角色与工具

| 角色 | 职责 | 工具数 | 模块文件 |
|------|------|--------|----------|
| **agent** | 日常开发、创建 issue、完成 plan | 19 | mcp_tools/agent.py |
| **mate** | 架构审查、批准 plan、协调冲突 | 7 | mcp_tools/mate.py |
| **tester** | 测试验证、提交 bug、验证修复 | 7 | mcp_tools/tester.py |
| **registrar** | 项目登记、初始化项目、创建里程碑 | 6 | mcp_tools/registrar.py |
| **shared** | 通用查询、通知、评论、交接 | 16 | mcp_tools/shared.py |

### 5.3 MCP 连接方式

```json
{
  "mcpServers": {
    "pm-agent": {
      "url": "http://192.168.1.100:9000/mcp",
      "headers": { "X-PM-Password": "CHANGE-ME" }
    },
    "pm-mate": {
      "url": "http://192.168.1.100:9000/mcp",
      "headers": { "X-PM-Password": "mate-2026" }
    }
  }
}
```

> **优势**：所有角色使用**同一个 URL**，只需修改密码即可切换角色权限。部署从 4 个容器缩减为 1 个，大幅降低运维复杂度。

### 5.4 MCP 认证流程

```
┌──────────┐   X-PM-Password    ┌──────────────────┐
│ IDE/Agent │ ─────────────────► │ PasswordMiddleware│
└──────────┘                    └────────┬─────────┘
                                         │ _request_password.set()
                                         ▼
                                ┌──────────────────┐
                                │ _ensure_token()  │
                                │ POST /auth/login │
                                └────────┬─────────┘
                                         │ JWT Token
                                         ▼
                                ┌──────────────────┐
                                │ _api_request()   │
                                │ Bearer Token     │
                                │ + 指数退避重试    │
                                └──────────────────┘
```

### 5.5 核心 MCP 工具

| 工具 | 角色 | 说明 |
|------|------|------|
| `get_context` | all | 全局态势感知（首选入口） |
| `check_connection` | all | 测试 MCP Server 与后端 API 连接 |
| `create_issue` | agent | 创建 Issue |
| `update_issue_status` | agent | 更新 Issue 状态 |
| `notify_role` | all | 给指定角色发送通知 |
| `get_handover_template` | all | 获取交接评论模板 |
| `add_issue_comment` | all | 添加评论（支持 handover 类型、线程回复） |
| `mark_handover_read` | all | 标记交接消息已读 |
| `check_unread_handovers` | all | 检查未读交接消息 |
| `propose_plan` | agent | 提议 Plan |
| `approve_plan` | mate | 批准 Plan |
| `reject_plan` | mate | 拒绝 Plan |
| `report_bug` | tester | 提交 Bug 报告 |
| `verify_fix` | tester | 验证修复 |
| `register_project` | registrar | 登记项目 |
| `save_memory` / `recall_memory` | all | Agent 记忆存取 |

---

## 6. 多 Agent 协作工作流

### 6.1 通信机制

```
┌──────────┐   notify_role    ┌──────────────┐
│ Agent A  │ ───────────────► │ Notification │
│ (agent)  │                  │   数据库      │
└──────────┘                  └──────┬───────┘
     │                               │ SSE 推送 / 轮询
     │ add_comment(type=handover)    │
     ▼                               ▼
┌──────────┐                  ┌──────────┐
│ Comment  │                  │ Agent B  │
│  数据库   │                  │ (mate)   │
└──────────┘                  └──────────┘
```

### 6.2 典型工作流

**开发 → 审查 → 测试 → 完成**

1. **Agent (Cursor)** 编码完成，调用 `get_handover_template("dev_complete")`
2. 填写后通过 `add_issue_comment(comment_type="handover")` 发送到 Issue #5
3. 调用 `notify_role(target_role="mate", title="Issue #5 待审查")`
4. **Mate (Cline)** 收到通知，查看 handover 评论，审查代码
5. 审查通过，添加 handover 评论，调用 `notify_role(target_role="tester", ...)`
6. **Tester** 收到通知，执行测试，添加测试报告
7. 测试通过，更新 Issue 状态为 closed

### 6.3 Agent 状态面板

Dashboard 页面嵌入 `AgentActivityPanel`，实时显示：
- 各 Agent 在线状态（online/idle/offline）
- 今日统计（创建/完成/审查数）
- 待办任务数
- 待交接任务列表（含已读/未读状态）

数据来自 `GET /api/v1/dashboard/agents` API。

---

## 7. 部署架构

### 7.1 Docker Compose（推荐）

```
┌─────────────────────────────────────────┐
│           Docker Host (家服)             │
│                                         │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ │
│  │backend  │ │frontend │ │mcp:9000  │ │
│  │:8000    │ │:8080    │ │(unified) │ │
│  │+/metrics│ │(nginx)  │ │          │ │
│  └─────────┘ └─────────┘ └──────────┘ │
│  ┌─────────────────────────┐           │
│  │    sqlite_data (卷)     │           │
│  └─────────────────────────┘           │
└─────────────────────────────────────────┘
              │
              │ Tailscale / 内网
              ▼
    ┌─────────────────────┐
    │   Cursor / Trae     │
    │   (工作本机)         │
    └─────────────────────┘
```

### 7.2 环境变量

```env
# 必须设置
SECRET_KEY=your-random-secret-key-here-min-32-chars
ADMIN_PASSWORD_HASH=$2b$12$...  # bcrypt 哈希

# Agent 密码（JSON 格式，bcrypt 哈希）
AGENT_PASSWORDS_JSON={"trae":{"password_hash":"$2b$12$...","role":"agent"},"mate":{"password_hash":"$2b$12$...","role":"mate"}}

# 加密密钥（服务器凭据加密，可选但推荐）
ENCRYPTION_KEY=...

# 网络配置（Tailscale 场景）
HOST_IP=100.x.x.x  # 家服 Tailscale IP
CORS_ORIGINS=http://localhost:8080,http://100.x.x.x:8080

# 端口（可选，默认如下）
BACKEND_PORT=8000
FRONTEND_PORT=8080
MCP_PORT=9000
```

### 7.3 启动方式

```bash
# Docker 一键启动（推荐）
docker compose up -d

# 本地开发
cd backend && python main.py
cd frontend && npm run dev
```

---

## 8. 数据流

### 8.1 Issue 生命周期

```
用户/Agent 创建
    │
    ▼
┌─────────┐    ┌──────────┐    ┌─────────┐
│  open   │───►│in_progress│───►│ review  │
└─────────┘    └──────────┘    └────┬────┘
     ▲                              │
     │         ┌──────────┐         │
     └─────────│ deferred │◄────────┘
               └──────────┘
                    │
                    ▼
               ┌─────────┐
               │  closed │
               └─────────┘
```

### 8.2 SQLite 并发优化

系统使用 SQLite + aiosqlite 作为数据库，已启用 **WAL 模式**（Write-Ahead Logging）：

```
┌─────────────────────────────────────────────────────────────┐
│  WAL 模式特性                                               │
│  • 读不阻塞写，写不阻塞读                                     │
│  • 支持多读 + 一写并发                                        │
│  • 写入速度提升（追加日志而非重写文件）                         │
│  • 自动 checkpoint，无需手动干预                              │
└─────────────────────────────────────────────────────────────┘
```

**配置**：`src/core/database.py` 中通过 PRAGMA 自动启用
- `journal_mode=WAL`
- `synchronous=NORMAL`（平衡性能与可靠性）
- `temp_store=MEMORY`（减少磁盘 I/O）

**连接池**：
- `pool_size=5`（保持的连接数）
- `max_overflow=10`（突发并发额外连接）
- `pool_timeout=30`（等待可用连接超时）
- `pool_recycle=3600`（连接回收时间）

### 8.3 Plan 审批流

```
Agent 提议 → pending_approval → 用户审批通过 → active → Agent 更新进展
                      │
               用户拒绝 → abandoned（可填写拒绝原因）
```

### 8.4 通知推送流

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ create_      │────►│ Notification │────►│ SSE 推送     │
│ notification │     │ 数据库写入    │     │ (内存队列)   │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                     推送失败 │
                            ▼
                     ┌──────────────┐     ┌──────────────┐
                     │ MessageQueue │────►│ SQLite 备份  │
                     │ (内存缓冲)    │     │ (持久化)     │
                     └──────────────┘     └──────────────┘
                            │
                     API 恢复 │
                            ▼
                     自动消费重试
```

---

## 9. 监控

### 9.1 Prometheus 指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `pm_agent_operations_total` | Counter | Agent 操作计数（按 role/operation/entity_type） |
| `pm_issue_transitions_total` | Counter | Issue 状态流转计数 |
| `pm_plan_approvals_total` | Counter | Plan 审批计数 |
| `pm_api_request_duration_seconds` | Histogram | API 响应时间 |
| `pm_current_issues` | Gauge | 当前 Issue 数量（按 status/priority） |
| `pm_agents_online` | Gauge | Agent 在线数量 |
| `pm_handovers_total` | Counter | 交接评论计数 |
| `pm_notifications_sent_total` | Counter | 通知发送计数 |

### 9.2 健康检查

| 端点 | 认证 | 说明 |
|------|------|------|
| `GET /health` | 否 | 后端健康检查 |
| `GET /api/v1/monitoring/health` | 否 | 数据库状态检查 |
| `GET /api/v1/monitoring/system` | 是 | 系统指标 |
| `GET /api/v1/monitoring/stuck-workflows` | 是 | 卡住的工作流检测 |

---

## 10. 技术栈总结

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), SQLite (WAL), JWT, bcrypt, Fernet |
| 前端 | React 19, TypeScript, Ant Design 6, Vite 8, React Router 7, React Query, @dnd-kit |
| MCP | FastMCP, Streamable HTTP, httpx (指数退避重试) |
| 监控 | Prometheus, prometheus-fastapi-instrumentator |
| 部署 | Docker, Docker Compose, Nginx |
| 网络 | Tailscale (可选，用于跨设备内网访问) |

---

## 11. 变更历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-05-28 | 初始稳定版，Docker 部署，Tailscale 适配 |
| 1.1.0 | 2026-06-10 | 多 Agent 协作：notify_role、handover 评论、Agent 状态面板、MCP HTTP 模式、容错机制、监控 API |
| 1.2.0 | 2026-06-10 | MCP Server 模块化拆分：1746 行单文件 → 6 个模块（shared/agent/mate/tester/registrar） |
| 1.3.0 | 2026-06-10 | SSE 通知 + Handover 已读回执、消息队列 + SQLite 持久化、bcrypt 密码哈希、工作流条件分支/并行/模板 |
