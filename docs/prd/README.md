# Project Manager System — 产品需求文档（PRD）

> 版本：v0.9.0 | 最后更新：2026-05-27
> 作者：项目 Owner | 状态：已发布

---

## 一、产品概述

### 1.1 产品定位

**人机协作项目管理系统** — 专为 **个人开发者 + AI Coding Agent** 协同管理项目而设计。

这不是传统意义上的团队项目管理工具（如 Jira、Linear），而是一个让**一个人 + 多个 AI Agent** 高效协作的"一人项目组操作系统"。

### 1.2 核心差异

| 维度 | 传统 PM 工具 | 本系统 |
|------|-------------|--------|
| 用户 | 团队（多人） | 你 + 多个 AI Agent |
| 身份 | 员工账号 | admin（你）+ 独立 Agent 身份 |
| 交互 | 人→人 | 人→Agent、Agent→人 |
| AI 角色 | 辅助功能 | 一等公民，独立创建/更新/审批 |
| 接入方式 | Web 为主 | **MCP 原生**，Agent 直接操作 |
| 典型场景 | 分配任务给同事 | Agent 自动发现 Bug 并创建 Issue |

### 1.3 目标用户

- **主要用户**：独立开发者 / 技术负责人，同时使用多个 AI Coding Agent（Cline、CodeBuddy、Trae、Hermes 等）
- **核心诉求**：让 AI Agent 和自己在同一个系统里管理任务，而不是 Agent 改了代码你却不知道

---

## 二、核心理念

### 2.1 人机对等协作

- 你和 Agent 都可以录入 Issue、设定 Plan、标记优先级
- 你说"这个先不管"，Agent 会把 Issue 标记为 deferred 并推迟到后期阶段
- Agent 发现问题可以自动创建 Issue 并标记来源为 `ai_agent`
- 你和 Agent 可以对同一个 Issue 添加各自的评论

### 2.2 MCP 原生

系统通过 MCP（Model Context Protocol）暴露所有核心能力，Agent 无需浏览器即可操作：

- 24+ MCP 工具覆盖全部业务操作
- 支持 stdio / SSE / Streamable HTTP 三种传输模式
- 每个 Agent 通过独立密码连接，ActivityLog 精确追踪谁做了什么

### 2.3 审批流控制

Agent 可以提议，但人做决策：

```
Agent 提议 Plan → pending_approval → 你审批通过 → active → Agent 执行
                                    → 你拒绝 → abandoned（可填写原因）
```

---

## 三、功能模块

### 3.1 Issue 管理

#### 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | String(200) | 标题 |
| `description` | Text | 详细描述 |
| `issue_type` | Enum | bug / feature / task / improvement / documentation / idea |
| `status` | Enum | open / in_progress / review / deferred / closed / cancelled |
| `priority` | Enum | P0 / P1 / P2 / P3 |
| `source` | Enum | user / ai_agent / collaborative |
| `milestone_id` | FK | 所属阶段 |
| `deferred_to_milestone_id` | FK | 推迟到哪个阶段 |
| `deferred_reason` | Text | 推迟原因 |

#### 核心功能

- **CRUD**：创建、查看、更新、删除 Issue
- **筛选排序**：按状态/优先级/类型/来源/里程碑筛选，按创建时间/更新时间/优先级排序
- **分页**：`skip`/`limit` 分页，默认 20 条/页，最大 100 条
- **暂缓（Defer）**：将 Issue 推迟到指定里程碑，记录原因
- **评论**：人和 Agent 都可以添加评论，`author` 自动从 JWT 身份获取
- **来源追踪**：`source` 字段区分是人创建还是 Agent 创建

#### API

```
GET    /api/v1/issues                     # 列表（筛选+排序+分页）
POST   /api/v1/issues                     # 创建
GET    /api/v1/issues/{id}                # 详情（含评论）
PUT    /api/v1/issues/{id}                # 更新
DELETE /api/v1/issues/{id}                # 删除
POST   /api/v1/issues/{id}/defer          # 暂缓
POST   /api/v1/issues/{id}/comments       # 添加评论
```

#### MCP 工具

| 工具 | 说明 |
|------|------|
| `create_issue` | 创建 Issue，自动标记 source |
| `list_issues` | 查询 Issues，支持筛选 |
| `update_issue_status` | 更新状态 |
| `update_issue_priority` | 更新优先级 |
| `defer_issue` | 暂缓到指定里程碑 |
| `add_issue_comment` | 添加评论 |

---

### 3.2 Milestone（阶段/分期）

#### 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | String | 阶段名称 |
| `phase` | String | 分期标识，如 `phase-1`、`MVP` |
| `status` | Enum | open / closed |
| `project_id` | FK | 所属项目 |

#### 核心功能

- **CRUD**：创建、查看、更新、删除里程碑
- **统计**：列表和详情返回 issue_count（按状态分组）
- **Issue 归属**：Issue 通过 `milestone_id` 关联到里程碑

#### API

```
GET    /api/v1/milestones                # 列表（含统计）
POST   /api/v1/milestones                # 创建
GET    /api/v1/milestones/{id}           # 详情（含统计）
PUT    /api/v1/milestones/{id}           # 更新
DELETE /api/v1/milestones/{id}           # 删除
```

---

### 3.3 Plan（计划）— 含审批流

#### 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | String | 计划名称 |
| `description` | Text | 计划描述 |
| `status` | Enum | draft / pending_approval / active / completed / abandoned |
| `proposed_by` | String | 谁提议的：user / ai_agent / 具体 Agent 名 |
| `approved_by` | String | 谁审批的 |
| `reject_reason` | Text | 拒绝原因 |

#### 审批流

```
Agent 提议 → pending_approval → 你审批通过 → active → Agent 更新进展
                     ↓
              你拒绝 → abandoned（可填写拒绝原因）
```

- Agent 提议 Plan 时，`status` 设为 `pending_approval`
- 审批通过：`status → active`，记录 `approved_by`
- 拒绝：`status → abandoned`，记录 `reject_reason`
- 通知：待审批时通知 admin，审批结果通知提议者

#### PlanItem（计划项/Checklist）

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | String | 项标题 |
| `status` | Enum | pending / in_progress / done / blocked |
| `completed_by` | String | user / ai_agent / 具体 Agent 名 |

#### API

```
GET    /api/v1/plans                     # 列表（含进度统计）
POST   /api/v1/plans                     # 创建
GET    /api/v1/plans/{id}                # 详情（含 plan_items）
PUT    /api/v1/plans/{id}                # 更新
POST   /api/v1/plans/{id}/approve        # 审批通过
POST   /api/v1/plans/{id}/reject         # 拒绝
DELETE /api/v1/plans/{id}                # 删除
GET    /api/v1/plans/{id}/items          # 计划项列表
POST   /api/v1/plans/{id}/items          # 添加计划项
PUT    /api/v1/plans/{id}/items/{item_id} # 更新计划项
DELETE /api/v1/plans/{id}/items/{item_id} # 删除计划项
```

#### MCP 工具

| 工具 | 说明 |
|------|------|
| `propose_plan` | 提议计划（pending_approval） |
| `list_plans` | 查询计划 |
| `update_plan_progress` | 更新/创建 PlanItem |

---

### 3.4 Project（项目）

#### 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | String | 项目名称 |
| `slug` | String | URL 标识 |
| `description` | Text | 项目描述 |
| `repo_url` | String | 仓库地址 |
| `status` | Enum | active / archived |
| `owner` | String | 项目负责人 |

#### 核心功能

- **多项目支持**：系统可管理多个项目，Issue/Plan/Milestone/Server 均归属项目
- **项目切换器**：前端侧边栏顶部 Dropdown 切换项目
- **统计**：列表和详情返回 issue_count、plan_count、milestone_count、server_count
- **URL 结构**：`/projects/{slug}/issues` 等
- **旧路由兼容**：`/issues` 自动重定向到 default 项目

#### API

```
GET    /api/v1/projects                  # 列表（含统计）
POST   /api/v1/projects                  # 创建
GET    /api/v1/projects/{id}             # 详情
PUT    /api/v1/projects/{id}             # 更新
DELETE /api/v1/projects/{id}             # 删除（有关联数据时返回 409）
```

---

### 3.5 Server（服务器/基础设施）

#### 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | String | 服务器名称 |
| `ip_address` | String | IP 地址 |
| `username` | String | 用户名 |
| `password` | String | 密码（Fernet 加密存储） |
| `ssh_key` | Text | SSH Key（Fernet 加密存储） |
| `status` | Enum | active / maintenance / offline / decommissioned |
| `environment` | Enum | production / staging / development |

#### 核心功能

- **凭据加密**：密码和 SSH Key 使用 Fernet 对称加密存储
- **凭据隔离**：列表和详情接口不返回敏感信息，仅显示 `has_password`/`has_ssh_key` 标志
- **凭据获取**：`GET /servers/{id}/credentials` 单独接口，仅 admin 角色可访问
- **连通性检查**：`POST /servers/{id}/check` 执行 TCP 连通性测试

#### API

```
GET    /api/v1/servers                   # 列表（不含凭据）
POST   /api/v1/servers                   # 创建
GET    /api/v1/servers/{id}              # 详情（不含凭据）
PUT    /api/v1/servers/{id}              # 更新
DELETE /api/v1/servers/{id}              # 删除
GET    /api/v1/servers/{id}/credentials  # 获取凭据（admin only）
POST   /api/v1/servers/{id}/check        # 连通性检查
```

---

### 3.6 工作流引擎

#### 数据模型

| 模型 | 说明 |
|------|------|
| `Workflow` | 工作流定义：name, trigger, trigger_config, status |
| `WorkflowStep` | 步骤定义：step_type, config, sort_order, timeout_seconds, on_failure |
| `WorkflowRun` | 执行记录：workflow_id, triggered_by, status, current_step_index, context |

#### 步骤类型

| step_type | 说明 |
|-----------|------|
| `create_issue` | 自动创建 Issue |
| `update_issue` | 更新 Issue 状态/优先级 |
| `notify` | 发送通知 |
| `wait_approval` | 暂停等待人类审批 |
| `propose_plan` | 提议 Plan |

#### 触发机制

| trigger | 说明 | 状态 |
|---------|------|------|
| `on_issue_created` | Issue 创建时自动触发 | ✅ 已接入 |
| `on_plan_approved` | Plan 审批后自动触发 | ✅ 已接入 |
| `manual` | 手动触发 | ✅ |
| `on_schedule` | 定时触发 | ⬜ 需 APScheduler |

#### 失败策略

| on_failure | 说明 |
|------------|------|
| `skip` | 跳过当前步骤，继续执行 |
| `abort` | 终止工作流 |
| `retry` | 指数退避重试（2/4/8 秒，最多 3 次） |
| `notify_human` | 通知人类处理 |

#### API

```
GET    /api/v1/workflows                 # 列表
POST   /api/v1/workflows                 # 创建（含步骤）
GET    /api/v1/workflows/{id}            # 详情（含步骤）
PUT    /api/v1/workflows/{id}            # 更新
DELETE /api/v1/workflows/{id}            # 删除
POST   /api/v1/workflows/{id}/steps      # 添加步骤
DELETE /api/v1/workflows/{id}/steps/{id} # 删除步骤
POST   /api/v1/workflows/{id}/trigger    # 手动触发
GET    /api/v1/workflows/runs            # 执行记录列表
GET    /api/v1/workflows/runs/{id}       # 执行记录详情
POST   /api/v1/workflows/runs/{id}/resume # 审批后恢复
```

---

### 3.7 通知系统 + SSE

#### 通知类型

| type | 说明 |
|------|------|
| `approval_needed` | Plan 待审批 |
| `task_created` | 新任务创建 |
| `task_completed` | 任务完成 |
| `task_failed` | 任务失败 |
| `mention` | @提及 |
| `workflow_paused` | 工作流暂停等待审批 |
| `info` | 一般信息 |

#### 核心功能

- **SSE 实时推送**：`GET /api/v1/notifications/stream`，新通知即时推送
- **未读计数**：`GET /api/v1/notifications/unread-count`
- **标记已读**：单条/全部标记已读
- **前端铃铛**：Header 显示未读数 Badge + 通知抽屉

#### API

```
GET    /api/v1/notifications              # 通知列表
GET    /api/v1/notifications/unread-count # 未读计数
GET    /api/v1/notifications/stream        # SSE 实时推送
PUT    /api/v1/notifications/{id}/read    # 标记已读
PUT    /api/v1/notifications/read-all      # 全部标记已读
```

---

### 3.8 Dashboard（数据看板）

#### 核心数据

| 数据 | 说明 |
|------|------|
| P0/P1 Issues | 紧急问题列表 |
| 待审批 Plan | 等待你决策 |
| 服务器状态 | 在线/离线/维护 |
| Activity 时间线 | 最近操作记录 |

#### Stats API（统计端点）

| 端点 | 说明 |
|------|------|
| `/stats/agent-productivity` | Agent 产出统计：创建/完成的 Issue 数 |
| `/stats/issue-resolution` | Issue 解决时长：平均值/中位数/P90 |
| `/stats/plan-completion` | Plan 完成率：环形进度 + 分项统计 |
| `/stats/agent-activity` | Agent 活跃度：每日操作时序图 |

---

### 3.9 看板视图

- **5 列看板**：Open / In Progress / Review / Deferred / Closed
- **拖拽改状态**：拖到另一列自动调用 API 更新
- **Issue 卡片**：ID + 标题 + 优先级 + 类型 + 来源图标
- **里程碑筛选**：看板顶部按里程碑筛选
- **乐观更新**：拖拽后先更新 UI，API 失败时回滚

---

### 3.10 多身份认证系统

#### 身份体系

| 角色 | 说明 | 登录方式 |
|------|------|---------|
| admin | 人类用户，最高权限 | 密码登录 |
| agent | AI Agent，操作受控 | 密码登录（MCP 自动） |

#### MCP 多身份

```env
# .env 配置
AGENT_PASSWORDS=trae:CHANGE-ME,cline:CHANGE-ME,buddy:buddy-2026
```

- **stdio 模式**：Agent 通过 `PM_AGENT_PASSWORD` 环境变量传密码
- **HTTP 模式**：Agent 通过 `X-PM-Password` 请求头传密码
- **身份隔离**：每个 Agent 独立 JWT 缓存，ActivityLog 精确记录 actor

#### MCP 传输模式

| 模式 | 端点 | 适用场景 |
|------|------|---------|
| Streamable HTTP | `http://host:9000/mcp` | 远程 Agent（Hermes 等） |
| SSE | `http://host:9000/sse` | 旧版客户端兼容 |
| stdio | 本地进程 | 本地 Agent（Cline/CodeBuddy 等） |

---

## 四、非功能需求

### 4.1 安全

| 措施 | 说明 |
|------|------|
| JWT 认证 | 所有 API 端点需 Bearer Token |
| 凭据加密 | 服务器密码/SSH Key 使用 Fernet 加密存储 |
| 凭据隔离 | 列表/详情不返回敏感信息，独立接口 + admin 限制 |
| CORS 限制 | `CORS_ORIGINS` 环境变量配置，不开放 `*` |
| 密钥强制 | `SECRET_KEY`/`ADMIN_PASSWORD` 必须配置，无默认值 |
| LIKE 转义 | 搜索转义 `%`/`_`/`\`，防通配符注入 |
| 审计日志 | 凭据访问记录审计日志 |

### 4.2 部署

| 要求 | 说明 |
|------|------|
| Docker 化 | Docker Compose 一键启动 |
| 内网就绪 | 端口可配（`.env`），CORS 支持 IP 访问 |
| SQLite | 零依赖数据库，named volume 持久化 |
| 备份 | `backup.sh` 一致性备份 + gzip + 自动清理 |
| 日志 | json-file 驱动，大小和数量限制 |
| 重启策略 | 生产 `on-failure`，开发 `unless-stopped` |

### 4.3 性能

| 指标 | 目标 |
|------|------|
| API 响应 | < 200ms（非聚合查询） |
| 分页 | 默认 20 条/页，最大 100 条 |
| SSE | 实时推送 + 30s 心跳 |
| N+1 查询 | 已优化，条件聚合 |

### 4.4 可观测性

| 手段 | 说明 |
|------|------|
| ActivityLog | 所有操作自动记录（谁、何时、做了什么） |
| 通知系统 | 关键事件实时推送 |
| Dashboard | 聚合统计 + Agent 产出对比 |
| 健康检查 | `/health` 端点，Docker healthcheck |

---

## 五、前端页面

| 页面 | 路由 | 功能 |
|------|------|------|
| 登录 | `/login` | 密码登录，显示当前身份 |
| Dashboard | `/projects/{slug}/dashboard` | P0/P1 Issues、待审批 Plan、Agent 统计、Activity 时间线 |
| Issues | `/projects/{slug}/issues` | 列表（筛选+排序+分页）、新建、详情（含评论）、暂缓 |
| 看板 | `/projects/{slug}/board` | 5 列拖拽看板 |
| Milestones | `/projects/{slug}/milestones` | 阶段卡片、Issue 统计 |
| Plans | `/projects/{slug}/plans` | 计划列表（含进度条）、审批操作、详情 checklist |
| Workflows | `/projects/{slug}/workflows` | 工作流列表、详情、执行记录、审批 |
| Servers | `/projects/{slug}/servers` | 服务器列表、添加、查看凭据 |

---

## 六、技术架构

```
┌─────────────┐     HTTP API      ┌─────────────┐     SQLite
│  React 前端  │ ◄──────────────► │ FastAPI 后端 │ ◄────────►
│  (你用的)    │                   │             │  project_manager.db
└─────────────┘                   └──────┬──────┘
                                         │
                                    MCP Server (Streamable HTTP / SSE / stdio)
                                    ┌─────┴──────┐
                                    │  多身份认证  │ ← X-PM-Password 请求头
                                    └─────┬──────┘
                                 ┌────────┼────────┐
                                 │        │        │
                            ┌────┴──┐ ┌──┴───┐ ┌──┴────┐
                            │ Agent │ │Agent │ │ Agent │
                            │  trae │ │cline │ │  ...  │
                            └───────┘ └──────┘ └───────┘
```

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), SQLite, JWT |
| 前端 | React 19, TypeScript, Ant Design 6, Vite, React Router 7 |
| MCP | FastMCP, httpx |
| 部署 | Docker, Docker Compose, Nginx |

---

## 七、路线图

### 已完成（v0.1.0 — v0.9.0）

| 版本 | Phase | 核心 |
|------|-------|------|
| v0.1.0 | Phase 1-3 | 基础 CRUD + MCP + Dashboard + Docker |
| v0.3.0 | — | 多 Agent 身份认证 |
| v0.4.0 | Phase 4 | 多项目 + 通知 + SSE |
| v0.5.0 | Phase 5 | 看板 + 数据看板 |
| v0.6.0 | Phase 6 | 工作流引擎 |
| v0.7.0 | Phase 7 | 安全治理 |
| v0.8.0 | Phase 8 | 内网部署就绪 |
| v0.9.0 | — | MCP 多身份 + Streamable HTTP |

### 计划中

| 优先级 | 功能 | 工期 | 价值 |
|--------|------|------|------|
| 🔴 高 | Git Webhook 自动关联 | 1-2 周 | 解决代码提交和项目管理割裂 |
| 🟡 中 | Prompt-to-Structure | 3-5 天 | 一句话生成完整项目结构 |
| 🟢 长期 | MCP 生态位强化 | 持续 | 成为 MCP-native PM 先行者 |

详见 [Idea Inbox 索引](../ideas/inbox/_index.md)。
