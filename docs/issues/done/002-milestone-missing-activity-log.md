# Milestone 路由缺少 ActivityLog 记录

## 优先级: P2
## 状态: open
## 类型: bug

## 问题描述

创建、更新、删除里程碑时没有调用 `log_activity`，而 Issues、Plans、Servers 路由都有活动日志记录。导致 ActivityTimeline 中看不到里程碑相关的操作记录。

## 影响范围

- 前端 ActivityTimeline 缺少里程碑操作记录
- 无法追踪谁在何时创建/修改了里程碑

## 建议方案

在 `backend/src/routes/milestones.py` 的以下位置添加 `log_activity` 调用：

1. `create_milestone` — 创建后记录 `action="created"`
2. `update_milestone` — 更新后记录 `action="updated"`
3. `delete_milestone` — 删除前记录 `action="deleted"`

参考 `issues.py` 或 `plans.py` 中的实现方式。
