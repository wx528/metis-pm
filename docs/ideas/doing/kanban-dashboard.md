# "一人项目组" 打磨方向

> 日期: 2026-05-18
> 核心价值：人做决策（审批/拒绝/优先级调整），执行全交给 Agent

## 完成情况

| # | 方向 | 状态 | 说明 |
|---|------|------|------|
| 1 | 多项目支持 | ✅ 已实现 | Project 模型 + CRUD API + MCP 工具 + 前端项目列表/详情 |
| 2 | Agent 工作流编排 | ✅ 已实现 | Workflow/WorkflowStep/WorkflowRun，5 种步骤类型，4 种触发方式（含 on_issue_created/on_plan_approved 自动钩子） |
| 3 | 通知系统 | ✅ 已实现 | Notification 模型 + MCP check_notifications/mark_notification_read + 前端通知页面 |
| 4 | 看板视图 | ❌ 待实现 | 优先级高，后端 API 已完备，只需前端 Kanban 组件 |
| 5 | 数据看板 | ❌ 待实现 | 优先级中，需新增统计 API，等数据积累后再做更有价值 |

## 待实现规划

### 看板视图（优先级 P1）

- 前端 Kanban 组件，按状态分列（open / in_progress / done）
- 拖拽改状态，调用已有 `update_issue_status` API
- 后端无需改动

### 数据看板（优先级 P2）

- 每个 Agent 的效率统计
- Issue 解决时长分布
- 项目/里程碑进度
- 需新增统计 API 端点
