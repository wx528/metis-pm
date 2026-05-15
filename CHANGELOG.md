# Changelog

## [0.1.0] - 2026-05-15

### 项目总览

Project Manager System — 人机协作项目管理系统，专为 **用户 + AI Coding Agent** 协同管理项目而设计。三个 Phase 全部完成。

| 阶段 | 名称 | 核心目标 | 状态 |
|------|------|----------|------|
| Phase 1 | 基础 CRUD + 前端骨架 | Issues/Milestones/Plans 增删改查 + React 前端 | **已完成** |
| Phase 2 | 人机协作 + MCP | MCP Server、ActivityLog 自动记录、前端时间线 | **已完成** |
| Phase 3 | 仪表盘 + 部署 | Dashboard 数据聚合、Docker 化、MCP 打包 | **已完成** |

---

### Phase 1：基础 CRUD + 前端骨架

#### 后端

- Issue 模型改造：`source`, `deferred_to_milestone_id`, `deferred_reason`
- Plan/PlanItem/Server/ActivityLog 模型
- 完整 CRUD 路由 + JWT 认证 + Plan 审批流

#### 前端

- React + TypeScript + Ant Design，Login/Dashboard/Issues/Milestones/Plans 页面
- Axios 封装 + Vite proxy

---

### Phase 2：人机协作 + MCP

#### MCP Server（13 个工具）

| 工具 | 功能 |
|------|------|
| `check_connection` | 连接测试 |
| `create_issue` | 创建 Issue，自动标记 `source=ai_agent` |
| `list_issues` | 查询 Issues，支持筛选 |
| `update_issue_status` | 更新状态 |
| `update_issue_priority` | 更新优先级 |
| `defer_issue` | 暂缓到指定 milestone |
| `add_issue_comment` | 添加评论 |
| `propose_plan` | 提议计划（`pending_approval`） |
| `list_plans` | 查询计划 |
| `update_plan_progress` | 更新/创建 PlanItem |
| `list_milestones` | 查询阶段 |
| `list_servers` | 查询服务器 |
| `get_server_credentials` | 获取凭据 |

#### ActivityLog 自动记录

- Issue 创建/更新/删除/暂缓/评论 自动记录
- Plan 创建/审批/拒绝 自动记录
- PlanItem 创建/完成 自动记录
- 前端 `ActivityTimeline` 时间线组件

---

### Phase 3：仪表盘 + 部署

#### Dashboard

- 数据聚合 API：`GET /api/v1/dashboard`
- P0/P1 issues、待审批计划、服务器状态、Activity 流
- 来源标识：user/ai_agent/collaborative 三色区分

#### Docker 部署

- `Dockerfile`（后端 Python + 前端 Node/Nginx）
- `docker-compose.yml`（named volume 解决 SQLite 权限问题）
- 前端生产构建配置（`VITE_API_URL` 环境变量）
- nginx 缓存控制头

#### MCP 打包

- `pyproject.toml`：可安装 Python 包
- `project-manager-mcp` CLI 入口
- `docs/mcp-config.md`：完整配置文档

#### 数据库备份

- `scripts/backup_db.py`：定时备份、压缩、自动清理旧备份

---

### 安全修复（10 个评审 issues）

| # | 问题 | 修复 |
|---|------|------|
| 001 | API 端点缺少身份认证 | 所有路由添加 JWT 保护 |
| 002 | 服务器密码明文暴露 | 新增 `/servers/{id}/credentials` 单独接口 |
| 003 | CORS 允许所有来源 + 硬编码密钥 | 环境变量配置，JWT 有效期 24h |
| 004 | CommentRead 重复定义 | 统一从 `schemas/comment.py` 导入 |
| 005 | `get_db` 重复定义 | 统一使用 `dependencies.py` |
| 006 | API 缺少枚举校验 | Schema 使用 `Literal` 枚举 |
| 007 | Plan 审批逻辑缺陷 | 使用 `timezone.utc` |
| 008 | Dashboard 总 Issue 数错误 | 独立 API 调用获取真实总数 |
| 009 | MCP 无身份验证 | 启动检查 `PM_TOKEN`，新增 `check_connection` |
| 010 | 代码质量问题 | 新增 `.gitignore`、`.env.example` |

---

### 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), SQLite, JWT |
| 前端 | React 19, TypeScript, Ant Design 6, Vite, React Router 7 |
| MCP | FastMCP, httpx |
| 部署 | Docker, Docker Compose, Nginx |

---

### 快速启动

```bash
# 1. 配置环境
cp .env.example .env
# 编辑 .env：SECRET_KEY 和 ADMIN_PASSWORD

# 2. Docker 一键启动
docker compose up -d

# 3. 访问
# 前端: http://localhost:8080
# API:  http://localhost:8000
# 文档: http://localhost:8000/docs
```

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
python main.py

# 前端
cd frontend
npm install
npm run dev
```
