# Project Manager System — v2 设计文档

> 从"人机协作工具"进化为"一人项目组操作系统"
>
> 前置文档：[system-design-01.md](system-design-01.md)（v0.1 ~ v0.3 已实现）

## 1. 设计目标

v1 解决了"人和 AI 怎么共用一个项目管理工具"的问题。v2 要解决的是：

> **一个人 + 多个 AI Agent，如何像一个完整项目组一样运作？**

核心差距：

| 维度 | v1 现状 | v2 目标 |
|------|---------|---------|
| 项目范围 | 单项目 | 多项目并行 |
| 工作方式 | 人手动创建 Issue → Agent 执行 | Agent 自动发现 → 自动创建 → 自动执行 → 通知人类审批 |
| 可视化 | 列表 + 详情 | 看板 + 甘特 + 数据看板 |
| 通知 | 无 | Agent 完成任务通知人类，人类拒绝后 Agent 自动调整 |
| Agent 协作 | 各自独立 | Agent 间可分配任务、传递上下文 |

## 2. 功能规划

### 2.1 多项目支持

当前所有数据混在一起，无法区分不同产品/仓库。新增 `Project` 模型作为顶层组织单元。

```
Project
├── id, name, slug
├── description
├── repo_url (代码仓库地址)
├── status: active | archived
├── owner (创建者身份)
├── default_milestone_id (当前聚焦阶段)
└── created_at, updated_at
```

**数据隔离策略：**

所有现有模型增加 `project_id` 外键：

```
Issue.project_id    →  所属项目
Plan.project_id     →  所属项目
Milestone.project_id → 所属项目
Server.project_id   →  所属项目
```

**API 变更：**

```
/api/v1/projects/                        → 项目 CRUD
/api/v1/projects/{slug}/issues           → 项目下 Issue
/api/v1/projects/{slug}/plans            → 项目下 Plan
/api/v1/projects/{slug}/milestones       → 项目下 Milestone
/api/v1/projects/{slug}/servers          → 项目下 Server
/api/v1/projects/{slug}/dashboard        → 项目 Dashboard
```

**MCP 工具变更：**

| 工具 | 变更 |
|------|------|
| `create_issue` | 新增 `project_slug` 参数 |
| `list_issues` | 新增 `project_slug` 筛选 |
| `propose_plan` | 新增 `project_slug` 参数 |
| `list_projects` | 新增：列出可访问的项目 |

**前端变更：**

- 侧边栏顶部增加项目切换器（Dropdown）
- 新增项目设置页
- URL 结构：`/projects/{slug}/issues`、`/projects/{slug}/plans` 等

**数据库迁移：**

```python
# 迁移策略
# 1. 创建 projects 表
# 2. 插入默认项目 "default"
# 3. 所有现有数据 project_id 设为默认项目 ID
# 4. 添加外键约束
```

---

### 2.2 Agent 工作流编排

v1 中 Agent 只能被动响应人类指令。v2 让 Agent 能主动发现工作、自动执行、只在关键节点请求人类确认。

#### 2.2.1 Workflow 模型

```
Workflow
├── id, name, description
├── project_id
├── trigger: on_issue_created | on_plan_approved | on_schedule | manual
├── trigger_config (JSON, 触发条件配置)
├── status: active | paused | archived
├── created_by (身份)
└── steps[]

WorkflowStep
├── id, workflow_id
├── step_type: create_issue | update_issue | propose_plan | notify | wait_approval | run_mcp_tool
├── config (JSON, 步骤配置)
├── sort_order
├── timeout_seconds (超时自动跳过/失败)
└── on_failure: skip | retry | abort | notify_human

WorkflowRun
├── id, workflow_id
├── triggered_by (身份 + 触发原因)
├── status: running | completed | failed | waiting_approval
├── current_step_index
├── context (JSON, 步骤间传递的上下文)
└── started_at, completed_at
```

#### 2.2.2 内置工作流模板

| 模板 | 触发 | 步骤 |
|------|------|------|
| Bug 自动处理 | `on_issue_created` (type=bug) | 创建 Issue → 设为 in_progress → 通知人类 → 等待确认 |
| 功能开发流 | `on_plan_approved` | 创建子 Issue → 标记 in_progress → 完成后更新 PlanItem |
| 定期巡检 | `on_schedule` (cron) | 检查服务器状态 → 异常则创建 Issue → 通知人类 |
| 代码审查流 | `manual` | 创建 Review Issue → 等待人类审批 → 通过则关闭，拒绝则创建修复 Issue |

#### 2.2.3 MCP 新增工具

| 工具 | 说明 |
|------|------|
| `create_workflow` | 创建工作流 |
| `list_workflows` | 列出工作流 |
| `trigger_workflow` | 手动触发工作流 |
| `list_workflow_runs` | 查看工作流执行记录 |

---

### 2.3 通知系统

Agent 完成任务后主动通知人类，人类无需频繁刷新页面。

#### 2.3.1 Notification 模型

```
Notification
├── id
├── recipient (目标身份，如 "admin")
├── type: approval_needed | task_completed | task_failed | mention | workflow_paused
├── title
├── body
├── entity_type (关联实体类型)
├── entity_id (关联实体 ID)
├── read: bool
├── created_by (触发者身份)
└── created_at
```

#### 2.3.2 通知触发场景

| 场景 | 通知对象 | 通知类型 |
|------|----------|----------|
| Plan 等待审批 | admin | `approval_needed` |
| Agent 完成 Issue | admin | `task_completed` |
| Agent 执行失败 | admin | `task_failed` |
| 工作流暂停等待 | admin | `workflow_paused` |
| 评论中 @某人 | 被提及者 | `mention` |

#### 2.3.3 通知渠道

| 渠道 | 优先级 | 说明 |
|------|--------|------|
| Web 前端 | P0 | Header 铃铛图标 + 未读数 Badge + 通知列表页 |
| MCP 轮询 | P0 | Agent 通过 `check_notifications` 工具获取 |
| 浏览器推送 | P1 | Web Push API，浏览器最小化时推送 |
| Webhook | P2 | 支持飞书/钉钉/企业微信/Telegram 等 |
| 邮件 | P3 | SMTP 发送，低优先级 |

#### 2.3.4 API 设计

```
GET  /api/v1/notifications           → 通知列表（分页、未读筛选）
PUT  /api/v1/notifications/{id}/read → 标记已读
PUT  /api/v1/notifications/read-all  → 全部已读
GET  /api/v1/notifications/unread-count → 未读数
```

#### 2.3.5 MCP 新增工具

| 工具 | 说明 |
|------|------|
| `check_notifications` | Agent 检查自己的通知 |
| `mark_notification_read` | 标记通知已读 |

---

### 2.4 看板视图

列表视图适合浏览，看板视图适合拖拽管理状态。

#### 2.4.1 设计方案

基于 Ant Design 的 `DNDKit` 或自研拖拽组件：

```
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│   Open   │In Progress│  Review  │ Deferred │  Closed  │
├──────────┼──────────┼──────────┼──────────┼──────────┤
│ ┌──────┐ │ ┌──────┐ │ ┌──────┐ │          │ ┌──────┐ │
│ │ISS-8 │ │ │ISS-5 │ │ │ISS-3 │ │          │ │ISS-1 │ │
│ │ P1 🤖│ │ │ P2 👤│ │ │ P0 🤖│ │          │ │ P2 👤│ │
│ └──────┘ │ └──────┘ │ └──────┘ │          │ └──────┘ │
│ ┌──────┐ │          │          │          │ ┌──────┐ │
│ │ISS-9 │ │          │          │          │ │ISS-2 │ │
│ │ P3 👤│ │          │          │          │ │ P1 🤖│ │
│ └──────┘ │          │          │          │ └──────┘ │
└──────────┴──────────┴──────────┴──────────┴──────────┘
```

**卡片信息：**

- Issue 标题（截断）
- 优先级标签（P0 红色 / P1 橙色 / P2 蓝色 / P3 灰色）
- 来源图标（🤖 AI / 👤 人类）
- 负责人（如已分配）

**交互：**

- 拖拽卡片到另一列 → 自动更新 Issue 状态
- 拖到 Deferred 列 → 弹出选择暂缓到哪个 Milestone
- 点击卡片 → 右侧抽屉显示详情
- 支持按 Project / Milestone / Agent 筛选

#### 2.4.2 前端路由

```
/projects/{slug}/board    → 看板视图
/projects/{slug}/issues   → 列表视图（现有）
```

---

### 2.5 数据看板

量化 Agent 效率，用数据驱动"一人项目组"的运营决策。

#### 2.5.1 核心指标

| 指标 | 计算方式 | 用途 |
|------|----------|------|
| Issue 解决时长 | `closed_at - created_at` 平均值 | 评估响应效率 |
| Agent 产出量 | 按 `actor` 统计创建/完成的 Issue 数 | 评估 Agent 贡献 |
| 人类审批耗时 | `approved_at - proposed_at` | 评估人类决策效率 |
| Plan 完成率 | `done_items / total_items` | 评估计划执行进度 |
| Bug 存活时间 | Bug 类型 Issue 的平均解决时长 | 评估质量 |
| Agent 活跃度 | 每日操作次数（ActivityLog） | 评估 Agent 利用率 |

#### 2.5.2 Dashboard 增强

```
┌─────────────────────────────────────────────────────────┐
│  Project: tce_tiku    [切换项目 ▼]                       │
├────────────┬────────────┬────────────┬──────────────────┤
│ Open: 12   │ In Prog: 3 │ Review: 2  │ Deferred: 5      │
├────────────┴────────────┴────────────┴──────────────────┤
│                                                         │
│  📊 Agent 产出对比（本周）                                │
│  ┌─────────────────────────────────────────────┐        │
│  │ cline      ████████████  8 issues            │        │
│  │ codebuddy  ██████████████  11 issues         │        │
│  │ trae       ████████  6 issues                │        │
│  │ admin      ████  3 issues                    │        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
│  ⏱ Issue 解决时长趋势                                    │
│  ┌─────────────────────────────────────────────┐        │
│  │  ▁▂▃▅▇█▇▅▃▂▁  (近 30 天)                     │        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
│  🔔 待处理通知                                           │
│  • Plan #3 等待审批 (codebuddy 提议)                     │
│  • Issue #8 执行失败 (cline)                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 2.5.3 API 设计

```
GET /api/v1/projects/{slug}/stats/agent-productivity  → Agent 产出统计
GET /api/v1/projects/{slug}/stats/issue-resolution    → Issue 解决时长
GET /api/v1/projects/{slug}/stats/plan-completion     → Plan 完成率
GET /api/v1/projects/{slug}/stats/agent-activity      → Agent 活跃度
GET /api/v1/projects/{slug}/dashboard                 → 增强：包含统计摘要
```

---

## 3. 技术方案

### 3.1 架构演进

```
┌─────────────────────────────────────────────────────────────┐
│                        用户（你）                             │
│              React + TypeScript + DNDKit                     │
│         Web Frontend (看板 / 列表 / 看板 / 通知)              │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP API + SSE (通知推送)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐      │
│  │ Projects │ │ Workflows│ │Notificat.│ │  Stats    │      │
│  │ CRUD     │ │ Engine   │ │ Service  │ │ Aggregation│     │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐      │
│  │ Issues   │ │ Milestones│ │  Plans   │ │ Servers   │      │
│  │ CRUD     │ │ CRUD     │ │ Approval │ │ CRUD      │      │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘      │
└──────────┬─────────────────────────┬────────────────────────┘
           │                         │
           ▼                         ▼
┌─────────────────────┐  ┌─────────────────────────────────┐
│   SQLite Database   │  │        MCP Server               │
│  (多项目数据隔离)     │  │  (Agent 工作流 + 通知轮询)       │
└─────────────────────┘  └─────────────────────────────────┘
                                   ▲
                    ┌──────────────┼──────────────┐
                    │              │              │
              ┌─────┴─────┐ ┌─────┴─────┐ ┌─────┴─────┐
              │   trae    │ │ codebuddy │ │   cline   │
              │  (Trae)   │ │(CodeBuddy)│ │  (Cline)  │
              └───────────┘ └───────────┘ └───────────┘
```

### 3.2 通知推送方案

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|------|
| SSE (Server-Sent Events) | 原生 HTTP、自动重连、简单 | 单向推送 | ✅ v2 首选 |
| WebSocket | 双向通信 | 复杂、需额外库 | v3 考虑 |
| 短轮询 | 最简单 | 浪费资源 | 仅 MCP 降级方案 |

SSE 端点：

```
GET /api/v1/notifications/stream?token=xxx
→ 返回 text/event-stream
→ 有新通知时推送 event: notification, data: {...}
```

### 3.3 工作流引擎方案

轻量级自研，不引入 Prefect/Celery 等重型框架：

```python
class WorkflowEngine:
    async def trigger(self, workflow_id, context):
        workflow = await self.get_workflow(workflow_id)
        run = await self.create_run(workflow, context)
        for step in workflow.steps:
            result = await self.execute_step(step, run.context)
            if step.step_type == "wait_approval":
                run.status = "waiting_approval"
                await self.notify_human(run)
                return
            run.context.update(result)
        run.status = "completed"

    async def resume(self, run_id, approval_result):
        run = await self.get_run(run_id)
        # 从暂停的步骤继续执行
        ...
```

**触发机制：**

- `on_issue_created`：FastAPI 路由中 Issue 创建后触发
- `on_plan_approved`：Plan 审批后触发
- `on_schedule`：APScheduler 定时任务（轻量依赖）
- `manual`：MCP 工具或前端按钮触发

### 3.4 数据库迁移策略

v2 涉及大量 schema 变更，迁移策略：

```python
# 迁移顺序
# 1. 创建 projects 表
# 2. 所有现有表添加 project_id 列（nullable）
# 3. 创建默认项目，回填 project_id
# 4. project_id 改为 NOT NULL + 外键
# 5. 创建 notifications 表
# 6. 创建 workflows / workflow_steps / workflow_runs 表
# 7. API 路由从 /api/v1/issues → /api/v1/projects/{slug}/issues
#    保留旧路由兼容（重定向到 default 项目）
```

---

## 4. 实施路线

### Phase 4：多项目 + 通知（v0.4.0）

| 任务 | 说明 |
|------|------|
| Project 模型 + CRUD | 新增项目增删改查 |
| 数据迁移 | 现有数据归入默认项目 |
| API 路由重构 | `/projects/{slug}/...` |
| Notification 模型 | 通知存储 |
| SSE 推送 | 前端实时接收通知 |
| 前端项目切换器 | 侧边栏项目 Dropdown |
| 前端通知铃铛 | Header 未读数 + 通知列表 |
| MCP 通知工具 | `check_notifications` |

### Phase 5：看板 + 数据看板（v0.5.0）

| 任务 | 说明 |
|------|------|
| 看板视图 | 拖拽式 Issue 状态管理 |
| Dashboard 增强 | Agent 产出对比、Issue 趋势图 |
| Stats API | 聚合统计接口 |
| 前端图表 | ECharts 或 Ant Design Charts |

### Phase 6：工作流引擎（v0.6.0）

| 任务 | 说明 |
|------|------|
| Workflow 模型 | 工作流定义 + 步骤 |
| WorkflowEngine | 执行引擎 |
| 内置模板 | Bug 处理流、功能开发流 |
| APScheduler | 定时触发 |
| MCP 工作流工具 | `create_workflow` / `trigger_workflow` |
| 前端工作流管理 | 工作流列表 + 执行记录 |

---

## 5. 风险与取舍

| 风险 | 应对 |
|------|------|
| 多项目数据隔离增加查询复杂度 | 所有查询强制带 `project_id` 条件；考虑后续升级 PostgreSQL |
| 工作流引擎可能过度设计 | 先做 3 个内置模板，验证价值后再开放自定义 |
| SSE 在 Docker/Nginx 下可能断连 | Nginx 配置 `proxy_buffering off`；前端自动重连 |
| 拖拽看板性能 | 虚拟滚动 + 限制单列卡片数（默认 50） |
| SQLite 并发写入瓶颈 | 工作流引擎使用队列缓冲写入；后续可切换 WAL 模式 |
