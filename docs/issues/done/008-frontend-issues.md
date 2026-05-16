# 008 - 前端问题汇总

- **优先级**: P1-P2
- **类型**: bug/ux
- **状态**: open

## 问题描述

### 8a. [P1] Dashboard 统计数据不准确

`Dashboard.tsx` 中"总 Issue 数"使用 `recentIssues.length`（最多5条），而不是实际的 issue 总数。

### 8b. [P1] Issue 详情页缺少评论功能

`IssueDetail.tsx` 没有展示评论列表和添加评论的表单，但后端已支持评论 API。

### 8c. [P2] Plans 列表不显示 plan_items 数量和进度

`Plans.tsx` 中 Plan 列表项没有显示 checklist 完成进度。

### 8d. [P2] 前端无 401 自动跳转处理

`client.ts` 中虽然 401 响应会跳转到 `/login`，但页面路由守卫（`PrivateRoute`）只检查 localStorage 是否有 token，不验证 token 是否过期。用户可能看到空白页面。

### 8e. [P2] 缺少 Servers 前端页面

后端已有 Servers CRUD API，但前端没有对应的 Servers 列表和详情页面。

### 8f. [P2] 缺少 Issue 列表排序选项

Issue 列表默认按创建时间倒序，但前端没有提供排序切换（按优先级、状态等排序）。

## 修复方案

- 8a: 调用单独的统计 API 或使用 `issuesApi.list({ limit: 1 })` 获取总数
- 8b: 在 IssueDetail 页面添加评论列表和评论表单
- 8c: Plan 列表显示 `done/total` 进度标签
- 8d: 定期验证 token 有效性
- 8e: 新增 Servers 页面
- 8f: 添加排序下拉框
