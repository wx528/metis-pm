# Issues 清单

> 来源：项目评审 | 初始日期：2026-05-15 | 最后更新：2026-05-17

## 目录结构

```
docs/issues/
├── README.md        # 本文件：汇总索引
├── done/            # 已修复
├── later/           # 待后续版本处理
└── new/             # 待评估/待修复
```

---

## 按分类汇总

### 🔒 安全 (security)

| # | 标题 | 优先级 | 状态 | 修复版本 |
|---|------|--------|------|----------|
| 001 | API 端点缺少身份认证保护 | P0 | **fixed** | v0.2.0 |
| 002 | 服务器密码明文存储且 API 完整返回 | P0 | **fixed** | v0.2.0 |
| 003 | CORS 允许所有来源 + 硬编码密钥 | P1 | **fixed** | v0.2.0 |
| 009 | MCP Server 没有身份验证 | P1 | **fixed** | v0.2.0 |
| 014 | MCP get_server_credentials 调用错误端点，凭据泄露 | P0 | **fixed** | v0.2.0 |
| 015 | Issue 列表搜索 LIKE 通配符注入 | P1 | **fixed** | v0.2.0 |

### 🐛 Bug

| # | 标题 | 优先级 | 状态 | 修复版本 |
|---|------|--------|------|----------|
| 004 | CommentRead 重复定义且字段不一致 | P1 | **fixed** | v0.2.0 |
| 006 | API 输入缺少枚举值校验 | P1 | **fixed** | v0.2.0 |
| 007 | Plan 审批逻辑缺陷 | P1 | **fixed** | v0.2.0 |
| 011 | 所有 Model 的 datetime.utcnow 无时区 | P1 | **fixed** | v0.2.0 |
| 013 | 测试全部未认证，无法通过 | P1 | **fixed** | v0.2.0 |
| 020 | PlanItem/Plan/Milestone schema 缺少枚举校验 | P1 | **fixed** | v0.2.0 |
| N002 | Milestone 路由缺少 ActivityLog 记录 | P2 | **fixed** | v0.5.0 |

### 🎨 用户体验 (ux)

| # | 标题 | 优先级 | 状态 | 修复版本 |
|---|------|--------|------|----------|
| 008 | 前端问题汇总（6 个子项） | P1-P2 | **fixed** | v0.2.0 |
| 018 | 前端 Issues 列表无分页 | P2 | **fixed** | v0.2.0 |

### ⚡ 性能 (performance)

| # | 标题 | 优先级 | 状态 | 修复版本 |
|---|------|--------|------|----------|
| 017 | 前端 Milestones 页面 N+1 查询 | P2 | **fixed** | v0.2.0 |
| N001 | SSE 跨 Worker 广播 | P1 | later | — |
| N004 | SSE 连接内存泄漏与超时清理 | P2 | later | — |

### 🔧 代码质量 (code-quality)

| # | 标题 | 优先级 | 状态 | 修复版本 |
|---|------|--------|------|----------|
| 005 | get_db 函数重复定义 | P1 | **fixed** | v0.2.0 |
| 010 | 代码质量问题（5 个子项） | P2 | **fixed** | v0.2.0 |
| 012 | Plan/PlanItem/Milestone/Server 的 status 用 String 而非 Enum | P1 | **fixed** | v0.2.0 |
| 019 | useAuth hook 未被使用 | P2 | **fixed** | v0.2.0 |

### 🛡️ 数据完整性 (data-integrity)

| # | 标题 | 优先级 | 状态 | 修复版本 |
|---|------|--------|------|----------|
| 016 | Milestone 删除未检查关联 Issue | P1 | **fixed** | v0.2.0 |
| N003 | project_id nullable 导致潜在孤立数据 | P2 | later | — |

### 🏗️ 架构 (architecture)

| # | 标题 | 优先级 | 状态 | 修复版本 |
|---|------|--------|------|----------|
| N005 | Notification 缺少 updated_at 字段 | P2 | **fixed** | v0.5.0 |
| N006 | 前端 SSE 解析不健壮 | P2 | later | — |

---

## 待处理 Issues (later/)

以下问题计划在后续版本处理，按优先级排序：

| # | 标题 | 优先级 | 类型 | 目标版本 |
|---|------|--------|------|----------|
| N001 | SSE 跨 Worker 广播 | P1 | performance | v0.5.0 |
| N003 | project_id nullable 孤立数据 | P2 | data-integrity | v0.5.0+ |
| N004 | SSE 连接内存泄漏与超时清理 | P2 | performance | v0.5.0 |
| N006 | 前端 SSE 解析不健壮 | P2 | architecture | v0.5.0 |

---

## 统计

| 状态 | 数量 |
|------|------|
| 已修复 (done/) | 22 |
| 待后续处理 (later/) | 4 |
| 待评估 (new/) | 0 |
| **合计** | **26** |

| 类型 | 已修复 | 待处理 |
|------|--------|--------|
| security | 6 | 0 |
| bug | 7 | 0 |
| ux | 2 | 0 |
| performance | 1 | 2 |
| code-quality | 4 | 0 |
| data-integrity | 1 | 1 |
| architecture | 1 | 1 |
