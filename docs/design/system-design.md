# Project Manager System — 系统设计文档

> 人机协作项目管理系统：你 + AI Coding Agent 共同管理项目

## 1. 系统定位

这不是一个团队协作工具，而是一个 **人机协作** 的项目管理中枢：

- **你** 通过 Web 前端管理 issues、审批计划、查看状态
- **AI Coding Agent** 通过 MCP 协议录入 issues、提议计划、更新进展
- 两者共享同一份数据，各有各的入口，互相可见

## 2. 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                     用户（你）                            │
│                   React + TypeScript                     │
│                   Web Frontend                           │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP API
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Issues   │ │ Milestones│ │  Plans   │ │ Servers   │  │
│  │ CRUD     │ │ CRUD     │ │ Approval │ │ CRUD      │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐    │
│  │ Comments │ │ Auth    │ │ Status/Activity Log  │    │
│  └──────────┘ └──────────┘ └──────────────────────┘    │
└──────────┬─────────────────────────┬───────────────────┘
           │                         │
           ▼                         ▼
┌─────────────────────┐  ┌─────────────────────────────┐
│   SQLite Database   │  │      MCP Server             │
│  (本地文件存储)      │  │  (AI Agent 原生调用入口)     │
└─────────────────────┘  └─────────────────────────────┘
                                   ▲
                                   │ MCP Protocol
                                   ▼
                         ┌─────────────────────┐
                         │   AI Coding Agent   │
                         │  (CodeBuddy/Cline)  │
                         └─────────────────────┘
```

### 2.1 前端：React + TypeScript

- 基于 Vite 构建
- UI 框架：Ant Design（组件丰富，表单/表格/审批流开箱即用）
- 与 tce_tiku 前端技术栈统一

### 2.2 后端：FastAPI + SQLite

- RESTful API 为核心
- MCP Server 作为独立进程，复用相同的数据模型和业务逻辑
- 简单 Token 认证（单用户 + 密码保护）

### 2.3 AI Agent 接入：MCP Server

MCP（Model Context Protocol）是 AI Coding Agent 的原生工具协议。Agent 可以直接调用 MCP 工具，无需手写 HTTP 请求。

MCP 工具清单：

| 工具名 | 说明 |
|--------|------|
| `create_issue` | 创建 issue（自动标记 source=ai_agent） |
| `list_issues` | 查询 issues |
| `update_issue` | 更新 issue |
| `defer_issue` | 暂缓 issue 到后期阶段 |
| `propose_plan` | 提议计划（状态=pending_approval） |
| `update_plan_progress` | 更新计划执行进展 |
| `add_comment` | 添加评论 |
| `list_servers` | 查看服务器信息 |
| `get_server_credentials` | 获取服务器凭据 |

## 3. 数据模型

### 3.1 Issue（问题/需求/缺陷）

```
Issue
├── id, title, description
├── issue_type: bug | feature | task | improvement | documentation
├── status: open | in_progress | review | deferred | closed | cancelled
├── priority: P0 | P1 | P2 | P3
├── source: user | ai_agent | collaborative
├── milestone_id (所属阶段)
├── deferred_to_milestone_id (推迟到哪个阶段)
├── deferred_reason (推迟原因)
├── parent_id (子任务)
└── comments[], activity_log[]
```

### 3.2 Milestone（阶段/分期）

```
Milestone
├── id, title, description
├── phase: phase-1 | MVP | v2.0 ...（分期标识）
├── status: open | closed
└── due_date
```

### 3.3 Plan（计划）— 含审批流

```
Plan
├── id, title, description
├── status: draft | pending_approval | active | completed | abandoned
├── proposed_by: user | ai_agent          ← 谁提议的
├── approved_by: user | null              ← 谁审批的
├── approved_at: datetime | null          ← 审批时间
├── current_milestone_id (聚焦阶段)
├── plan_items[]                          ← 计划项（checklist）
└── activity_log[]
```

**审批流：**

```
Agent 提议 → pending_approval → 用户审批 → active → 执行中...
                     ↓
                  用户拒绝 → abandoned
```

### 3.4 PlanItem（计划项/Checklist）

```
PlanItem
├── id, plan_id
├── title, description
├── status: pending | in_progress | done | blocked
├── sort_order (排序)
├── completed_by: user | ai_agent | null
└── completed_at: datetime | null
```

### 3.5 Server（服务器/基础设施）

```
Server
├── id, name, description
├── ip_address
├── port
├── username
├── password            ← 明文（仅本地/内网）
├── ssh_key             ← 可选，SSH 私钥
├── server_type: web | db | cache | worker | other
├── status: active | maintenance | offline | decommissioned
├── environment: production | staging | development
├── labels (标签，逗号分隔)
├── last_checked_at     ← 最后检查时间
└── activity_log[]
```

### 3.6 ActivityLog（活动日志）— 通用状态追踪

```
ActivityLog
├── id
├── entity_type: issue | plan | plan_item | server | milestone
├── entity_id
├── action: created | updated | status_changed | approved | rejected | deferred | commented
├── old_value (变更前，JSON)
├── new_value (变更后，JSON)
├── actor: user | ai_agent
└── created_at
```

### 3.7 Auth（简单认证）

```
# 不建表，用环境变量配置
ADMIN_PASSWORD = "xxx"         ← .env 中配置
TOKEN_SECRET = "xxx"           ← JWT 签名密钥

# 登录后返回 JWT token
# MCP 连接时通过配置传入 token
```

## 4. 前端页面

| 页面 | 路径 | 功能 |
|------|------|------|
| Dashboard | `/` | 概览：P0/P1 issues、待审批计划、服务器状态 |
| Issues 列表 | `/issues` | 筛选、搜索、新建 issue |
| Issue 详情 | `/issues/:id` | 详情、评论、状态变更、暂缓操作 |
| Milestones | `/milestones` | 阶段管理、issue 统计 |
| Plans | `/plans` | 计划列表、审批操作 |
| Plan 详情 | `/plans/:id` | 计划项 checklist、进度更新 |
| Servers | `/servers` | 服务器信息管理、状态标记 |
| Login | `/login` | 密码登录 |

### 关键交互

1. **审批操作**：Plan 列表中 `pending_approval` 状态的计划高亮提示，点击审批/拒绝
2. **暂缓操作**：Issue 详情中点击"暂缓"，弹出选择推迟到哪个 Milestone
3. **来源标识**：Issue/Plan 卡片上用图标/颜色区分 `user` / `ai_agent` / `collaborative`
4. **活动时间线**：所有实体的详情页底部展示 ActivityLog 时间线

## 5. MCP Server 设计

作为独立进程运行，与 FastAPI 共享同一数据库文件。

```python
# MCP 工具定义示例
@mcp_tool(name="create_issue")
async def create_issue(
    title: str,
    description: str = "",
    priority: str = "P2",        # P0 | P1 | P2 | P3
    issue_type: str = "task",
    milestone_id: int | None = None,
) -> dict:
    """创建 issue，source 自动设为 ai_agent"""
    ...
```

### MCP 配置方式

用户在 CodeBuddy/Cline 的 MCP 配置中添加：

```json
{
  "mcpServers": {
    "project-manager": {
      "command": "python",
      "args": ["path/to/mcp_server.py"],
      "env": {
        "PM_API_URL": "http://localhost:8000",
        "PM_TOKEN": "your-jwt-token"
      }
    }
  }
}
```

## 6. API 设计

### Issues `/api/v1/issues`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 列表（筛选：type/status/priority/source/milestone/deferred_only） |
| POST | `/` | 创建 |
| GET | `/{id}` | 详情（含 comments + activity） |
| PUT | `/{id}` | 更新 |
| DELETE | `/{id}` | 删除 |
| POST | `/{id}/defer` | 暂缓 |
| POST | `/{id}/comments` | 添加评论 |
| GET | `/{id}/activity` | 活动日志 |

### Milestones `/api/v1/milestones`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 列表（筛选：status/phase） |
| POST | `/` | 创建 |
| GET | `/{id}` | 详情（含统计） |
| PUT | `/{id}` | 更新 |
| DELETE | `/{id}` | 删除 |

### Plans `/api/v1/plans`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 列表（筛选：status） |
| POST | `/` | 创建 |
| GET | `/{id}` | 详情（含 plan_items） |
| PUT | `/{id}` | 更新 |
| POST | `/{id}/approve` | 审批通过 |
| POST | `/{id}/reject` | 审批拒绝 |
| DELETE | `/{id}` | 删除 |

### PlanItems `/api/v1/plans/{plan_id}/items`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 计划项列表 |
| POST | `/` | 添加计划项 |
| PUT | `/{item_id}` | 更新计划项（状态等） |
| DELETE | `/{item_id}` | 删除计划项 |

### Servers `/api/v1/servers`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 列表（筛选：status/environment/type） |
| POST | `/` | 创建 |
| GET | `/{id}` | 详情 |
| PUT | `/{id}` | 更新 |
| DELETE | `/{id}` | 删除 |
| POST | `/{id}/check` | 手动触发状态检查 |
| GET | `/{id}/activity` | 活动日志 |

### Auth `/api/v1/auth`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/login` | 登录（返回 JWT） |
| GET | `/me` | 当前用户信息 |

## 7. 安全考量

- 明文存储服务器凭据 → **仅限本地/内网部署，不暴露公网**
- JWT Token 有效期 7 天
- MCP 连接通过环境变量传入 Token
- 后续如需公网部署，可升级为 AES 加密存储
