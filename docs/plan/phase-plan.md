# Project Manager System — 分期实施计划

## 总览

| 阶段 | 名称 | 核心目标 | 状态 |
|------|------|----------|------|
| Phase 1 | 基础 CRUD + 前端骨架 | Issues/Milestones/Plans 增删改查 + React 前端 | **已完成** |
| Phase 2 | 人机协作 + MCP | MCP Server、ActivityLog 自动记录、前端时间线 | **已完成** |
| Phase 3 | 仪表盘 + 部署 | Dashboard 数据聚合、Docker 化、MCP 打包 | **已完成** |

---

## Phase 1：基础 CRUD + 前端骨架 — 已完成

### 后端

- [x] Issue 模型改造：`source`, `deferred_to_milestone_id`, `deferred_reason`
- [x] Plan/PlanItem/Server/ActivityLog 模型
- [x] 完整 CRUD 路由 + JWT 认证 + Plan 审批流

### 前端

- [x] React + TS + Ant Design，Login/Dashboard/Issues/Milestones/Plans 页面
- [x] Axios 封装 + Vite proxy

---

## Phase 2：人机协作 + MCP — 已完成

### 2.1 MCP Server

- [x] **P0** MCP Server 骨架：`mcp_server.py`，基于 `FastMCP`
- [x] **P0** `create_issue` — 自动标记 `source=ai_agent`
- [x] **P0** `list_issues` — 支持筛选参数
- [x] **P0** `update_issue_status` / `update_issue_priority`
- [x] **P1** `defer_issue` — 暂缓到指定 milestone
- [x] **P1** `add_issue_comment` — 添加评论
- [x] **P1** `propose_plan` — 提议计划（`pending_approval`）
- [x] **P1** `list_plans` — 查询计划
- [x] **P2** `update_plan_progress` — 更新/创建 PlanItem
- [x] **P2** `list_milestones` — 查询阶段
- [x] **P2** `list_servers` — 查询服务器
- [x] **P2** `get_server_credentials` — 获取凭据

### 2.2 ActivityLog 自动记录

- [x] **P1** Issue 创建/更新/删除/暂缓/评论 自动记录
- [x] **P1** Plan 创建/审批/拒绝 自动记录
- [x] **P2** PlanItem 创建/完成 自动记录
- [x] **P2** 前端 `ActivityTimeline` 组件（时间线展示）
- [x] **P2** IssueDetail / PlanDetail 页面集成时间线

### Phase 2 Checklist

```
[x] MCP Server 可独立运行（python mcp_server.py）
[x] Agent 能通过 MCP 创建 issue（source=ai_agent）
[x] Agent 能通过 MCP 提议计划（pending_approval）
[x] Agent 能通过 MCP 更新 PlanItem 进度
[x] Agent 能通过 MCP 查询服务器凭据
[x] ActivityLog 正确记录所有状态变更
[x] 前端详情页展示活动时间线（区分 user/ai_agent）
```

### MCP 配置方式

在 CodeBuddy/Cline 的 MCP 配置中添加：

```json
{
  "mcpServers": {
    "project-manager": {
      "command": "python",
      "args": ["D:/AI-learning/tce_tiku/project_mananger_system/backend/mcp_server.py"],
      "env": {
        "PM_API_URL": "http://localhost:8000/api/v1",
        "PM_TOKEN": "your-jwt-token"
      }
    }
  }
}
```

获取 Token：
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password":"admin"}'
```

---

## Phase 3：仪表盘 + 部署 — 已完成

> 目标：Dashboard 数据聚合，Docker 化部署，MCP 打包

### 3.1 Dashboard 完善

- [x] **P1** Dashboard 数据聚合 API：`GET /api/v1/dashboard`
- [x] **P1** Dashboard 展示：服务器状态概览（active/maintenance/offline 计数）
- [x] **P2** Dashboard 展示：最近 Activity 流
- [x] **P2** 前端来源标识：issue/plan 卡片用图标区分 user/ai_agent/collaborative

### 3.2 部署

- [x] **P2** Docker 化：Dockerfile + docker-compose.yml
- [x] **P2** 前端生产构建配置（API base URL 环境变量 VITE_API_URL）
- [x] **P3** MCP Server 打包为可安装的 Python 包（pyproject.toml + entry point）
- [x] **P3** MCP 配置文档（docs/mcp-config.md）
- [x] **P3** 数据库备份脚本（scripts/backup_db.py）

### Phase 3 Checklist

```
[x] Dashboard 展示 P0/P1 issues + 待审批计划 + 服务器状态 + Activity 流
[x] 来源标识在前端清晰可见（user/ai_agent/collaborative 三色区分）
[x] Docker 一键启动（docker-compose up）
[x] MCP Server 配置文档完成（docs/mcp-config.md）
[x] 数据库备份脚本（scripts/backup_db.py）
```

---

## 风险 & 待定

| 风险 | 应对 |
|------|------|
| MCP SDK 版本变化 | 锁定版本，关注 changelog |
| 明文密码安全 | 仅本地部署，Phase 后续可升级 AES |
| SQLite 并发 | 单人使用足够，必要时换 PostgreSQL |
