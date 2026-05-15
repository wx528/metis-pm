# Project Manager System

人机协作项目管理系统 — 专为 **用户 + AI Coding Agent** 协同管理项目而设计。

## 快速启动

### 后端
```bash
cd backend
pip install -r requirements.txt
python main.py
# API: http://localhost:8000
# Swagger 文档: http://localhost:8000/docs
```

### 前端
```bash
cd frontend
npm install
npm run dev
# 前端: http://localhost:5173
# 自动代理 API 请求到 localhost:8000
```

默认密码：`admin`

## 核心理念

这个系统不是给团队用的，而是给 **你和一个 AI Coding Agent** 一起用的：
- 你和 Agent 都可以录入 issues、设定 plan、标记优先级
- 你说"这个先不管"，Agent 会把 issue 标记为 deferred 并推迟到后期阶段
- Agent 发现问题可以自动创建 issue 并标记来源为 `ai_agent`
- 你和 Agent 可以对同一个 issue 添加各自的评论

## 系统架构

```
┌─────────────┐     HTTP API      ┌─────────────┐     SQLite
│  React 前端  │ ◄──────────────► │ FastAPI 后端 │ ◄────────►
│  (你用的)    │                   │             │  project_manager.db
└─────────────┘                   └──────┬──────┘
                                         │
                                    MCP Server
                                         │
                                    ┌────┴────┐
                                    │ AI Agent │
                                    └─────────┘
```

## 数据模型

### Issue（问题/需求/缺陷）

| 字段 | 说明 |
|------|------|
| `title` | 标题 |
| `description` | 详细描述 |
| `issue_type` | bug / feature / task / improvement / documentation |
| `status` | open / in_progress / review / **deferred** / closed / cancelled |
| `priority` | **P0** / **P1** / **P2** / **P3** |
| `source` | **user** / **ai_agent** / **collaborative** |
| `milestone_id` | 所属阶段 |
| `deferred_to_milestone_id` | 推迟到哪个阶段 |
| `deferred_reason` | 推迟原因 |

### Milestone（阶段/分期）

| 字段 | 说明 |
|------|------|
| `title` | 阶段名称 |
| `phase` | 分期标识，如 `phase-1`、`MVP` |
| `status` | open / closed |

### Plan（计划）— 含审批流

| 字段 | 说明 |
|------|------|
| `title` | 计划名称 |
| `status` | draft / **pending_approval** / active / completed / abandoned |
| `proposed_by` | 谁提议的：user / ai_agent |
| `approved_by` | 谁审批的 |

**审批流：**
```
Agent 提议 → pending_approval → 你点击"审批通过" → active → Agent 更新进展
                     ↓
                  你点击"拒绝" → abandoned
```

### PlanItem（计划项/Checklist）

| 字段 | 说明 |
|------|------|
| `title` | 项标题 |
| `status` | pending / in_progress / **done** / blocked |
| `completed_by` | user / ai_agent |

### Server（服务器/基础设施）

| 字段 | 说明 |
|------|------|
| `name` | 服务器名称 |
| `ip_address` | IP |
| `username` / `password` | 凭据（明文，仅本地） |
| `status` | active / maintenance / offline / decommissioned |
| `environment` | production / staging / development |

## 前端页面

| 页面 | 功能 |
|------|------|
| Dashboard | P0/P1 issues、待审批计划、服务器状态概览 |
| Issues | 列表、筛选、新建、详情、评论、暂缓 |
| Milestones | 阶段卡片、issue 统计 |
| Plans | 计划列表、审批操作、详情 checklist |

## API 接口

### Auth
```
POST /api/v1/auth/login          # 登录（密码 admin）
GET  /api/v1/auth/me             # 当前用户
```

### Issues
```
GET    /api/v1/issues                    # 列表（支持筛选）
POST   /api/v1/issues                    # 创建
GET    /api/v1/issues/{id}               # 详情
PUT    /api/v1/issues/{id}               # 更新
DELETE /api/v1/issues/{id}               # 删除
POST   /api/v1/issues/{id}/defer         # 暂缓
POST   /api/v1/issues/{id}/comments      # 添加评论
```

### Milestones
```
GET    /api/v1/milestones                # 列表
POST   /api/v1/milestones                # 创建
GET    /api/v1/milestones/{id}           # 详情（含统计）
PUT    /api/v1/milestones/{id}           # 更新
DELETE /api/v1/milestones/{id}           # 删除
```

### Plans
```
GET    /api/v1/plans                     # 列表
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

### Servers
```
GET    /api/v1/servers                   # 列表
POST   /api/v1/servers                   # 创建
GET    /api/v1/servers/{id}              # 详情
PUT    /api/v1/servers/{id}              # 更新
DELETE /api/v1/servers/{id}              # 删除
POST   /api/v1/servers/{id}/check        # 手动检查
```

## 典型工作流

### 1. 创建项目分期
```bash
curl -X POST http://localhost:8000/api/v1/milestones \
  -H "Content-Type: application/json" \
  -d '{"title": "Phase 1 - 基础功能", "phase": "phase-1"}'
```

### 2. 录入 Issue（人/Agent 各自标记来源）
```bash
# 你创建一个 P1 issue
curl -X POST http://localhost:8000/api/v1/issues \
  -H "Content-Type: application/json" \
  -d '{"title": "登录页面无法跳转", "issue_type": "bug", "priority": "P1", "source": "user"}'

# AI Agent 发现一个优化点
curl -X POST http://localhost:8000/api/v1/issues \
  -H "Content-Type: application/json" \
  -d '{"title": "搜索接口可加缓存", "issue_type": "improvement", "priority": "P3", "source": "ai_agent"}'
```

### 3. 暂缓不需要现在处理的 Issue
```bash
curl -X POST "http://localhost:8000/api/v1/issues/2/defer?deferred_to_milestone_id=2&deferred_reason=当前阶段聚焦核心功能"
```

### 4. Agent 提议计划，你审批
```bash
# Agent 提议
curl -X POST http://localhost:8000/api/v1/plans \
  -H "Content-Type: application/json" \
  -d '{"title": "重构认证模块", "proposed_by": "ai_agent", "status": "pending_approval"}'

# 你审批通过
curl -X POST http://localhost:8000/api/v1/plans/1/approve
```
