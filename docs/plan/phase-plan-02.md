# Project Manager System — v2 分期实施计划

> 对应设计文档：[system-design-02.md](../design/system-design-02.md)

## 总览

| 阶段 | 名称 | 核心目标 | 版本 | 状态 |
|------|------|----------|------|------|
| Phase 1 | 基础 CRUD + 前端骨架 | Issues/Milestones/Plans 增删改查 | v0.1.0 | **已完成** |
| Phase 2 | 人机协作 + MCP | MCP Server、ActivityLog | v0.2.0 | **已完成** |
| Phase 3 | 仪表盘 + 部署 | Dashboard、Docker 化 | v0.3.0 | **已完成** |
| Phase 4 | 多项目 + 通知 | Project 模型、Notification、SSE 推送 | v0.4.0 | **已完成** |
| Phase 5 | 看板 + 数据看板 | 拖拽看板、Agent 统计、趋势图 | v0.5.0 | 待开始 |
| Phase 6 | 工作流引擎 | Workflow 模型、执行引擎、内置模板 | v0.6.0 | 待开始 |

---

## Phase 4：多项目 + 通知（v0.4.0）

> 目标：支持多项目并行管理，Agent 完成任务后主动通知人类

### 4.1 后端 — Project 模型

- [ ] **P0** 创建 `Project` 模型（name, slug, description, repo_url, status, owner）
- [ ] **P0** Alembic 迁移：创建 `projects` 表
- [ ] **P0** 所有现有模型添加 `project_id` 列（nullable 先行）
- [ ] **P0** 迁移脚本：插入默认项目 "default"，回填所有现有数据的 `project_id`
- [ ] **P0** `project_id` 改为 NOT NULL + 外键约束
- [ ] **P1** Project CRUD 路由：`/api/v1/projects/`
- [ ] **P1** Project Schema（ProjectCreate / ProjectRead / ProjectUpdate）

### 4.2 后端 — API 路由重构

- [ ] **P0** 新路由结构：`/api/v1/projects/{slug}/issues`、`/plans`、`/milestones`、`/servers`
- [ ] **P0** 旧路由兼容：`/api/v1/issues` 重定向到 default 项目的查询
- [ ] **P1** 所有查询强制带 `project_id` 条件（数据隔离）
- [ ] **P1** Dashboard 路由：`/api/v1/projects/{slug}/dashboard`

### 4.3 后端 — Notification 模型

- [ ] **P0** 创建 `Notification` 模型（recipient, type, title, body, entity_type, entity_id, read, created_by）
- [ ] **P0** Alembic 迁移：创建 `notifications` 表
- [ ] **P0** Notification CRUD 路由
  - [ ] `GET /api/v1/notifications` — 列表（分页、未读筛选）
  - [ ] `PUT /api/v1/notifications/{id}/read` — 标记已读
  - [ ] `PUT /api/v1/notifications/read-all` — 全部已读
  - [ ] `GET /api/v1/notifications/unread-count` — 未读数
- [ ] **P1** 通知触发逻辑
  - [ ] Plan 等待审批 → 通知 admin（`approval_needed`）
  - [ ] Agent 完成 Issue → 通知 admin（`task_completed`）
  - [ ] Agent 执行失败 → 通知 admin（`task_failed`）
- [ ] **P2** 通知服务封装：`NotificationService.create(...)` 统一入口

### 4.4 后端 — SSE 推送

- [ ] **P1** SSE 端点：`GET /api/v1/notifications/stream?token=xxx`
- [ ] **P1** 通知创建时向 SSE 连接推送事件
- [ ] **P2** Nginx 配置：`proxy_buffering off` + `X-Accel-Buffering: no`
- [ ] **P2** 前端 SSE 断线自动重连（指数退避）

### 4.5 MCP — 新增工具

- [ ] **P0** `list_projects` — 列出可访问项目
- [ ] **P0** `create_issue` 增加 `project_slug` 参数
- [ ] **P0** `list_issues` 增加 `project_slug` 筛选
- [ ] **P1** `propose_plan` 增加 `project_slug` 参数
- [ ] **P1** `check_notifications` — Agent 检查自己的通知
- [ ] **P2** `mark_notification_read` — 标记通知已读

### 4.6 前端 — 项目切换

- [ ] **P0** 侧边栏顶部项目切换器（Dropdown，列出所有 active 项目）
- [ ] **P0** URL 结构变更：`/projects/{slug}/issues`、`/projects/{slug}/plans` 等
- [ ] **P1** 项目设置页（编辑名称、描述、仓库地址）
- [ ] **P1** 新建项目弹窗（name 自动生成 slug）
- [ ] **P2** 项目归档功能（status: archived）

### 4.7 前端 — 通知

- [ ] **P0** Header 铃铛图标 + 未读数 Badge
- [ ] **P0** 通知列表页（分页、已读/未读筛选、点击跳转关联实体）
- [ ] **P1** SSE 实时推送（新通知自动出现，无需刷新）
- [ ] **P2** 浏览器推送（Web Push API，最小化时通知）
- [ ] **P2** 通知全部已读按钮

### Phase 4 Checklist

```
[ ] 创建 Project 模型 + 迁移，现有数据归入 default 项目
[ ] API 路由重构为 /projects/{slug}/...，旧路由兼容
[ ] 所有查询强制 project_id 隔离
[ ] Notification 模型 + CRUD + 触发逻辑
[ ] SSE 推送端点 + 前端实时接收
[ ] 前端项目切换器 + URL 结构变更
[ ] 前端通知铃铛 + 通知列表
[ ] MCP 新增 list_projects / check_notifications
[ ] Docker + Nginx 配置更新（SSE 支持）
[ ] 旧路由兼容测试：现有 MCP 配置不中断
```

---

## Phase 5：看板 + 数据看板（v0.5.0）

> 目标：拖拽看板管理 Issue 状态，数据看板量化 Agent 效率

### 5.1 后端 — Stats API

- [ ] **P0** Agent 产出统计：`GET /api/v1/projects/{slug}/stats/agent-productivity`
  - 按 `actor` 统计创建/完成的 Issue 数
  - 按时间段筛选（本周/本月/全部）
- [ ] **P0** Issue 解决时长：`GET /api/v1/projects/{slug}/stats/issue-resolution`
  - 平均解决时长、中位数、P90
  - 按类型（bug/feature/task）分组
- [ ] **P1** Plan 完成率：`GET /api/v1/projects/{slug}/stats/plan-completion`
  - `done_items / total_items` 百分比
  - 按状态分组统计
- [ ] **P1** Agent 活跃度：`GET /api/v1/projects/{slug}/stats/agent-activity`
  - 每日操作次数（ActivityLog 聚合）
  - 操作类型分布
- [ ] **P2** Dashboard API 增强：`/projects/{slug}/dashboard` 返回统计摘要

### 5.2 前端 — 看板视图

- [ ] **P0** 安装 `@dnd-kit/core` + `@dnd-kit/sortable`
- [ ] **P0** 看板页面骨架：5 列（Open / In Progress / Review / Deferred / Closed）
- [ ] **P0** Issue 卡片组件（标题 + 优先级标签 + 来源图标）
- [ ] **P0** 拖拽功能：拖到另一列 → 调用 `update_issue_status` API
- [ ] **P1** 拖到 Deferred 列 → 弹窗选择暂缓 Milestone
- [ ] **P1** 点击卡片 → 右侧 Drawer 显示详情
- [ ] **P1** 筛选栏：按 Project / Milestone / Agent / Priority 筛选
- [ ] **P2** 虚拟滚动（单列卡片 > 50 时启用）
- [ ] **P2** 拖拽动画 + 占位符

### 5.3 前端 — 数据看板

- [ ] **P0** 安装图表库（`@ant-design/charts` 或 `echarts`）
- [ ] **P0** Dashboard 增强：Agent 产出对比柱状图
- [ ] **P0** Dashboard 增强：Issue 解决时长趋势折线图
- [ ] **P1** Dashboard 增强：Plan 完成率环形图
- [ ] **P1** Dashboard 增强：Agent 活跃度热力图/日历图
- [ ] **P2** Dashboard 增强：待处理通知摘要卡片
- [ ] **P2** 统计页面（独立路由，更详细的图表和筛选）

### 5.4 前端路由

- [ ] **P0** `/projects/{slug}/board` — 看板视图
- [ ] **P0** `/projects/{slug}/issues` — 列表视图（现有）
- [ ] **P1** `/projects/{slug}/stats` — 统计页面
- [ ] **P1** 侧边栏增加"看板"和"统计"菜单项

### Phase 5 Checklist

```
[ ] Stats API 4 个端点全部可用
[ ] 看板视图拖拽改状态正常工作
[ ] Deferred 拖拽弹窗选择 Milestone
[ ] 卡片点击 Drawer 详情
[ ] Agent 产出对比柱状图
[ ] Issue 解决时长趋势图
[ ] Dashboard 包含统计摘要
[ ] 看板和统计路由在侧边栏可见
```

---

## Phase 6：工作流引擎（v0.6.0）

> 目标：Agent 能自动发现工作、执行、只在关键节点请求人类确认

### 6.1 后端 — Workflow 模型

- [ ] **P0** 创建 `Workflow` 模型（name, description, project_id, trigger, trigger_config, status, created_by）
- [ ] **P0** 创建 `WorkflowStep` 模型（workflow_id, step_type, config, sort_order, timeout_seconds, on_failure）
- [ ] **P0** 创建 `WorkflowRun` 模型（workflow_id, triggered_by, status, current_step_index, context）
- [ ] **P0** Alembic 迁移：创建 3 张表
- [ ] **P1** Workflow CRUD 路由
  - [ ] `GET /api/v1/projects/{slug}/workflows` — 列表
  - [ ] `POST /api/v1/projects/{slug}/workflows` — 创建
  - [ ] `GET /api/v1/projects/{slug}/workflows/{id}` — 详情（含 steps）
  - [ ] `PUT /api/v1/projects/{slug}/workflows/{id}` — 更新
  - [ ] `DELETE /api/v1/projects/{slug}/workflows/{id}` — 删除
- [ ] **P1** WorkflowRun 路由
  - [ ] `GET /api/v1/workflows/runs` — 执行记录列表
  - [ ] `GET /api/v1/workflows/runs/{id}` — 执行详情
  - [ ] `POST /api/v1/workflows/{id}/trigger` — 手动触发
  - [ ] `POST /api/v1/workflows/runs/{id}/resume` — 恢复暂停的执行

### 6.2 后端 — WorkflowEngine

- [ ] **P0** `WorkflowEngine` 类：`trigger()` / `execute_step()` / `resume()`
- [ ] **P0** Step 执行器
  - [ ] `create_issue` — 创建 Issue
  - [ ] `update_issue` — 更新 Issue 状态/优先级
  - [ ] `notify` — 创建通知
  - [ ] `wait_approval` — 暂停执行，通知人类
- [ ] **P1** Step 执行器
  - [ ] `propose_plan` — 提议计划
  - [ ] `run_mcp_tool` — 调用任意 MCP 工具（扩展点）
- [ ] **P1** 步骤间上下文传递：前一步输出作为后一步输入
- [ ] **P2** 超时处理：`timeout_seconds` 到期后按 `on_failure` 策略处理
- [ ] **P2** 重试机制：`on_failure=retry` 时自动重试（最多 3 次）

### 6.3 后端 — 触发机制

- [ ] **P0** `on_issue_created` 触发：Issue 创建后检查匹配的 Workflow
- [ ] **P1** `on_plan_approved` 触发：Plan 审批后检查匹配的 Workflow
- [ ] **P2** `on_schedule` 触发：安装 APScheduler，支持 cron 表达式
- [ ] **P2** `manual` 触发：前端按钮 / MCP 工具触发

### 6.4 内置工作流模板

- [ ] **P0** Bug 自动处理流：`on_issue_created(type=bug)` → 设 in_progress → 通知人类
- [ ] **P1** 功能开发流：`on_plan_approved` → 创建子 Issue → 更新 PlanItem
- [ ] **P2** 定期巡检流：`on_schedule` → 检查服务器 → 异常创建 Issue
- [ ] **P2** 代码审查流：`manual` → 创建 Review Issue → 等待审批

### 6.5 MCP — 新增工具

- [ ] **P0** `create_workflow` — 创建工作流（含步骤定义）
- [ ] **P0** `list_workflows` — 列出工作流
- [ ] **P1** `trigger_workflow` — 手动触发工作流
- [ ] **P1** `list_workflow_runs` — 查看执行记录

### 6.6 前端 — 工作流管理

- [ ] **P0** 工作流列表页（名称、触发类型、状态、操作）
- [ ] **P0** 工作流详情页（步骤列表 + 执行记录）
- [ ] **P1** 工作流创建/编辑页（步骤拖拽排序、配置表单）
- [ ] **P1** 执行记录详情（每步状态、耗时、上下文数据）
- [ ] **P2** 工作流可视化（流程图，展示步骤和分支）

### Phase 6 Checklist

```
[ ] Workflow/WorkflowStep/WorkflowRun 模型 + 迁移
[ ] WorkflowEngine 核心逻辑：trigger / execute_step / resume
[ ] on_issue_created 触发正常工作
[ ] Bug 自动处理流端到端测试通过
[ ] wait_approval 步骤暂停 → 人类审批 → 恢复执行
[ ] MCP create_workflow / trigger_workflow 可用
[ ] 前端工作流列表 + 详情页
[ ] APScheduler 定时触发（如已实现）
```

---

## 风险 & 待定

| 风险 | 应对 | 阶段 |
|------|------|------|
| 多项目迁移数据丢失 | 迁移前自动备份 SQLite；先 nullable 再回填 | Phase 4 |
| 旧 API 路由中断现有 MCP 配置 | 保留旧路由兼容（重定向到 default） | Phase 4 |
| SSE 在 Nginx 下断连 | `proxy_buffering off` + 前端自动重连 | Phase 4 |
| 拖拽看板性能（大量 Issue） | 虚拟滚动 + 分页加载 | Phase 5 |
| SQLite 并发写入瓶颈 | 工作流引擎队列缓冲；后续可切换 WAL 模式 | Phase 6 |
| 工作流引擎过度设计 | 先做 3 个内置模板，验证价值后再开放自定义 | Phase 6 |
| APScheduler 额外依赖 | 仅 Phase 6 P2 引入，不影响核心功能 | Phase 6 |

---

## 依赖关系

```
Phase 4（多项目 + 通知）
    ↓
Phase 5（看板 + 数据看板）  ← 依赖 Phase 4 的多项目路由结构
    ↓
Phase 6（工作流引擎）       ← 依赖 Phase 4 的通知系统
```

Phase 5 和 Phase 6 之间无强依赖，但建议按顺序实施，因为：
- Phase 5 的看板让人类更高效地管理 Issue
- Phase 6 的工作流让 Agent 更自主地执行
- 先优化人的体验，再优化 Agent 的自主性
