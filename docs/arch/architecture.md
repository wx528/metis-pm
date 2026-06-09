# Project Manager System 架构文档

> 人机协作项目管理系统架构设计
> 版本: 1.1.0
> 更新日期: 2026-06-10

---

## 1. 系统概述

Project Manager System 是一个专为 **用户 + 多个 AI Coding Agent** 协同管理项目而设计的系统。它不仅仅是一个项目管理工具，更是一个让不同角色的 AI Agent（开发、审查、测试）能够有序协作、交接工作、互相通知的协作平台。

### 核心设计理念

- **多 Agent 协作**：支持多个编程工具（Cursor、Trae、Cline 等）同时接入，每个分配明确角色
- **角色分工**：agent（开发）、mate（审查）、tester（测试）、registrar（登记）
- **工作流驱动**：Agent 之间通过通知和交接评论完成状态流转
- **内网优先**：基于 Streamable HTTP 的 MCP 传输，适合局域网/Tailscale 部署

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
                           │ HTTP API
┌──────────────────────────┼────────────────────────────────────┐
│                          ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                   FastAPI 后端                           │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │  │
│  │  │ Issues  │  │  Plans  │  │Milestones│  │ Servers │   │  │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘   │  │
│  │       └─────────────┴─────────────┴─────────────┘        │  │
│  │                         │                                │  │
│  │              ┌──────────┴──────────┐                    │  │
│  │              │    SQLAlchemy ORM   │                    │  │
│  │              └──────────┬──────────┘                    │  │
│  │                         ▼                                │  │
│  │                   ┌──────────┐                          │  │
│  │                   │  SQLite  │                          │  │
│  │                   │ (aiosqlite)│                         │  │
│  │                   └──────────┘                          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                           │                                    │
│                           ▼                                    │
│                   ┌──────────────┐                            │
│                   │  mcp:9000    │                            │
│                   │ 统一 Server  │                            │
│                   │ (agent/mate/ │                            │
│                   │ tester/reg)  │                            │
│                   └──────────────┘                            │
└──────────────────────────────────────────────────────────────┘
```

### 服务矩阵

| 服务 | 容器名 | 端口 | 说明 |
|------|--------|------|------|
| backend | pm-backend | 8000 | FastAPI REST API |
| frontend | pm-frontend | 8080 | React SPA (Nginx) |
| mcp | pm-mcp | 9000 | 统一 MCP Server（4 角色共用） |

---

## 3. 后端架构

### 3.1 技术栈

- **框架**: FastAPI 0.115 (Python 3.11)
- **ORM**: SQLAlchemy 2.0 (async)
- **数据库**: SQLite + aiosqlite
- **认证**: JWT (PyJWT) + 密码认证
- **加密**: Fernet (cryptography)
- **测试**: pytest + pytest-asyncio

### 3.2 项目结构

```
backend/
├── main.py                  # FastAPI 入口 + 数据库迁移
├── mcp_server.py            # Agent MCP Server (端口 9000)
├── mcp_server_mate.py       # Mate MCP Server (端口 9001)
├── mcp_server_tester.py     # Tester MCP Server (端口 9002)
├── mcp_server_registrar.py  # Registrar MCP Server (端口 9003)
├── mcp_common.py            # MCP 共享工具与基类
├── src/
│   ├── settings.py          # 全局配置（Pydantic BaseSettings）
│   ├── core/
│   │   ├── database.py      # SQLAlchemy 异步引擎 + Base
│   │   ├── dependencies.py  # 依赖注入（get_db, get_current_user）
│   │   ├── crypto.py        # 加密工具
│   │   ├── activity.py      # 活动日志
│   │   ├── notification.py  # 通知 + SSE
│   │   └── workflow_engine.py
│   ├── models/              # SQLAlchemy ORM（14 个实体）
│   ├── schemas/             # Pydantic 请求/响应模型
│   └── routes/              # FastAPI 路由（17 个模块）
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
| Issue | 问题/需求/缺陷 | status, priority, source, milestone_id |
| Plan | 计划（含审批流） | status, proposed_by, approved_by |
| PlanItem | 计划项/Checklist | status, completed_by |
| Milestone | 阶段/分期 | phase, status |
| Comment | 评论（含交接类型） | comment_type (normal/management/handover) |
| Notification | 通知 | recipient, type, read |
| ActivityLog | 活动日志 | actor, action, entity_type |
| Server | 服务器/基础设施 | ip_address, credentials (encrypted) |
| Workflow | 工作流 | trigger, steps |
| Project | 项目 | slug, description |

---

## 4. 前端架构

### 4.1 技术栈

- **框架**: React 19 + TypeScript
- **UI 组件**: Ant Design 6
- **构建工具**: Vite
- **路由**: React Router 7
- **HTTP 客户端**: axios
- **状态管理**: React Context (useProject, useAuth)

### 4.2 项目结构

```
frontend/src/
├── main.tsx                    # 入口
├── App.tsx                     # 路由定义
├── api/                        # API 调用层
│   ├── client.ts              # axios 实例
│   ├── agentStatus.ts         # Agent 状态 API
│   ├── issues.ts, plans.ts, ...
│   └── index.ts               # 统一导出
├── components/                 # 可复用组件
│   ├── AgentActivityPanel.tsx # Agent 协作看板
│   ├── ActivityTimeline.tsx   # 活动时间线
│   ├── IssueCard.tsx
│   └── Layout.tsx
├── hooks/                      # 自定义 Hooks
│   ├── useAuth.tsx
│   ├── useProject.tsx
│   └── useNotifications.tsx
├── pages/                      # 页面组件
│   ├── Dashboard.tsx          # 仪表盘（含 Agent 看板）
│   ├── Issues.tsx
│   ├── Plans.tsx
│   ├── Milestones.tsx
│   ├── Servers.tsx
│   └── Workflows.tsx
└── styles/
    └── index.css
```

### 4.3 页面与功能

| 页面 | 功能 |
|------|------|
| Dashboard | P0/P1 issues、待审批计划、服务器状态、Agent 协作看板 |
| Issues | 列表（筛选+排序+分页）、新建、详情（含评论）、暂缓 |
| Plans | 计划列表（含进度条）、审批操作、详情 checklist |
| Milestones | 阶段卡片、issue 统计 |
| Servers | 服务器列表、添加、查看凭据 |
| Workflows | 工作流列表、创建、触发 |

---

## 5. MCP 架构

### 5.1 设计原则

- **统一传输**: 全部使用 Streamable HTTP，适合内网部署
- **多角色**: 每个角色独立进程 + 独立端口，通过密码区分身份
- **角色隔离**: 不同角色的 MCP 工具集不同，权限不同
- **内网优先**: IDE 无需安装本地脚本，直接通过 HTTP 连接

### 5.2 角色与端口

| 角色 | 职责 | 端口 | 说明 |
|------|------|------|------|
| **agent** | 日常开发、创建 issue、完成 plan | 9000 | 共用统一 Server |
| **mate** | 架构审查、批准 plan、协调冲突 | 9000 | 共用统一 Server |
| **tester** | 测试验证、提交 bug、验证修复 | 9000 | 共用统一 Server |
| **registrar** | 项目登记、初始化项目、创建里程碑 | 9000 | 共用统一 Server |

**统一设计**：所有角色通过**同一个端口 9000**接入，由 `X-PM-Password` 请求头自动识别角色并分配对应工具权限。

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

### 5.4 核心 MCP 工具

| 工具 | 角色 | 说明 |
|------|------|------|
| `get_context` | all | 全局态势感知（首选入口） |
| `create_issue` | agent | 创建 Issue |
| `update_issue_status` | agent | 更新 Issue 状态 |
| `notify_role` | all | 给指定角色发送通知 |
| `get_handover_template` | all | 获取交接评论模板 |
| `add_issue_comment` | all | 添加评论（支持 handover 类型） |
| `propose_plan` | agent | 提议 Plan |
| `list_plans` | all | 查询 Plan 列表 |
| `check_notifications` | all | 检查通知 |
| `list_milestones` | all | 查询里程碑 |

---

## 6. 多 Agent 协作工作流

### 6.1 通信机制

```
┌──────────┐   notify_role    ┌──────────────┐
│ Agent A  │ ───────────────► │ Notification │
│ (agent)  │                  │   数据库      │
└──────────┘                  └──────┬───────┘
     │                               │
     │ add_comment(type=handover)    │ Agent B 轮询
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
- 待交接任务列表

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
│  │:8000    │ │:8080    │ │(agent)   │ │
│  └─────────┘ └─────────┘ └──────────┘ │
│                              ┌────────┐│
│                              │mcp:9001││
│                              │(mate)  ││
│                              └────────┘│
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
ADMIN_PASSWORD=your-secure-password

# Agent 密码
AGENT_PASSWORDS=trae:CHANGE-ME,mate:mate-2026,tester:tester-2026

# 网络配置（Tailscale 场景）
HOST_IP=100.x.x.x  # 家服 Tailscale IP
CORS_ORIGINS=http://localhost:8080,http://100.x.x.x:8080

# 端口（可选，默认如下）
BACKEND_PORT=8000
FRONTEND_PORT=8080
MCP_PORT=9000
MCP_MATE_PORT=9001
MCP_TESTER_PORT=9002
MCP_REGISTRAR_PORT=9003
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

## 8. 安全设计

| 措施 | 说明 |
|------|------|
| JWT 认证 | 所有 API 端点需携带 Bearer Token |
| 多身份认证 | 每个 Agent 通过独立密码连接 MCP Server |
| 凭据隔离 | 服务器密码/SSH Key 加密存储，列表接口不返回敏感信息 |
| CORS 限制 | 通过 `CORS_ORIGINS` 环境变量配置允许的来源 |
| 密钥强制 | `SECRET_KEY` 和 `ADMIN_PASSWORD` 必须在 `.env` 中设置 |
| MCP Token 缓存 | 按密码缓存 JWT，401 自动清缓存重登录 |
| LIKE 转义 | 搜索接口转义 `%`、`_`、`\` 防止通配符注入 |
| RBAC 隔离 | 后端 auth 层区分 agent/mate/tester 角色，API 路由层做权限校验 |

---

## 9. 数据流

### 9.1 Issue 生命周期

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

### 9.2 Plan 审批流

```
Agent 提议 → pending_approval → 用户审批通过 → active → Agent 更新进展
                      │
               用户拒绝 → abandoned（可填写拒绝原因）
```

---

## 10. 技术栈总结

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), SQLite, JWT |
| 前端 | React 19, TypeScript, Ant Design 6, Vite, React Router 7 |
| MCP | FastMCP, Streamable HTTP, httpx |
| 部署 | Docker, Docker Compose, Nginx |
| 网络 | Tailscale (可选，用于跨设备内网访问) |

---

## 11. 变更历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-05-28 | 初始稳定版，Docker 部署，Tailscale 适配 |
| 1.1.0 | 2026-06-10 | 多 Agent 协作：notify_role、handover 评论、Agent 状态面板、MCP 全面切换 HTTP 模式 |
