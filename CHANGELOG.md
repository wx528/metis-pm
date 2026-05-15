# Changelog

## [0.3.0] - 2026-05-16

### 多 Agent 身份认证系统

之前所有操作者只有 `admin` 和 `ai_agent` 两种身份，无法区分不同 AI Coding Agent。现在每个 Agent 拥有独立密码和身份，ActivityLog 可精确追踪谁做了什么。

| 变更 | 说明 |
|------|------|
| JWT 多身份支持 | `create_token(sub, role)` 生成包含 `sub` 和 `role` 的 JWT，不再固定 `sub=admin` |
| Agent 密码配置 | 新增 `AGENT_PASSWORDS` 环境变量，格式 `name:password,name2:password2` |
| 身份解析 | `settings.resolve_identity(password)` 自动识别 admin 或 agent 身份 |
| ActivityLog 精确追踪 | 所有路由的 `actor` 字段从 JWT `sub` 读取，如 `cline`、`codebuddy`、`admin` |
| MCP 自动登录 | MCP Server 改用 `PM_AGENT_PASSWORD` 自动登录获取 token，无需手动获取 |
| MCP 身份标记 | `source`/`proposed_by`/`author` 等字段自动使用 Agent 名称而非硬编码 `ai_agent` |
| 前端身份显示 | Header 显示当前登录身份（用户名 + 角色 Tag），`useAuth` 新增 `sub`/`role` |
| `/auth/me` 增强 | 返回 `sub` + `role` 而非仅 `role` |
| `/auth/login` 增强 | 返回 `token` + `sub` + `role` |
| Plan 审批追踪 | `approved_by` 使用 JWT 身份而非硬编码 `"user"` |

### Bug 修复

| 问题 | 修复 |
|------|------|
| 登录后页面闪回 login | `isLoggedIn` 初始状态改为同步读取 `localStorage`；`navigate` 替代 `window.location.replace` |
| Dashboard 500 错误 | 添加数据库迁移逻辑，自动补齐 `plans` 表缺失的 `reject_reason`、`current_milestone_id` 列 |
| Docker 构建失败 | 修复 TypeScript 编译错误、`.env` 缺失、`VERSION` 文件路径问题 |

### 前端改进

| 变更 | 说明 |
|------|------|
| 全局 Footer | 所有页面（含登录页）底部显示项目名和版本号 |
| 版本号注入 | Vite 构建时从 `VERSION` 文件读取版本号，通过 `__APP_VERSION__` 全局变量使用 |

### 配置示例

```bash
# .env
SECRET_KEY=your-secret-key-min-32-chars
ADMIN_PASSWORD=CHANGE-ME                                              # 人类用户
AGENT_PASSWORDS=cline:CHANGE-ME,codebuddy:CHANGE-ME     # AI Agent（name:password 逗号分隔）
```

```json
// MCP 配置（Cline / CodeBuddy / Cursor Agent）
// ⚠️ args 必须使用绝对路径
{
  "mcpServers": {
    "project-manager": {
      "command": "python",
      "args": ["D:/AI-learning/tce_tiku/project_mananger_system/backend/mcp_server.py"],
      "env": {
        "PM_API_URL": "http://localhost:8000/api/v1",
        "PM_AGENT_PASSWORD": "CHANGE-ME"
      }
    }
  }
}
```

### 验证结果

| 测试 | 结果 |
|------|------|
| `admin` 密码登录 → `sub: "admin"`, `role: "admin"` | ✅ |
| `CHANGE-ME` 密码登录 → `sub: "cline"`, `role: "agent"` | ✅ |
| `CHANGE-ME` 密码登录 → `sub: "codebuddy"`, `role: "agent"` | ✅ |
| 错误密码 → 401 拒绝 | ✅ |
| cline 创建 issue → ActivityLog `actor: "cline"` | ✅ |
| codebuddy 创建 issue → ActivityLog `actor: "codebuddy"` | ✅ |

---

## [0.2.0] - 2026-05-16

### 安全修复（P0）

| # | 问题 | 修复 |
|---|------|------|
| 001 | API 端点缺少身份认证保护 | 所有路由添加 `Depends(get_current_user)` JWT 保护 |
| 002 | 服务器密码明文存储且 API 完整返回 | `ServerRead` 移除 `password`/`ssh_key`，新增 `has_password`/`has_ssh_key` 标志；凭据通过 `/servers/{id}/credentials` 单独接口获取 |
| 003 | CORS 允许所有来源 + 硬编码密钥 | CORS 改用 `CORS_ORIGINS` 环境变量；`SECRET_KEY`/`ADMIN_PASSWORD` 移除默认值，启动时强制校验；新增 `.env.example` |

### 功能修复（P1）

| # | 问题 | 修复 |
|---|------|------|
| 004 | CommentRead 重复定义且字段不一致 | 统一为 `src/schemas/comment.py` 单一定义，消除跨模块不一致 |
| 005 | `get_db` 函数重复定义 | 统一为 `src/core/dependencies.py` 单一定义 |
| 006 | API 输入缺少枚举值校验 | Schema 使用 Pydantic `Literal` 类型约束枚举值（Issue/Plan/Server） |
| 007 | Plan 审批逻辑缺陷 | reject 不再错误设置 `approved_by`/`approved_at`；新增 `reject_reason` 字段；前端拒绝增加确认弹窗 |
| 009 | MCP Server 没有身份验证 | 添加 `PM_TOKEN` 环境变量，所有请求携带 Bearer Token；启动时检查并警告 |

### 前端改进（P2）

| # | 问题 | 修复 |
|---|------|------|
| 008a | Dashboard 统计数据不准确 | 后端 Dashboard API 使用聚合查询返回真实统计 |
| 008b | Issue 详情页缺少评论功能 | 添加评论列表 + 评论输入框，支持 `addComment` API |
| 008c | Plans 列表不显示进度 | 后端 list 接口新增 `item_count`/`item_done_count` 统计；前端显示进度条 |
| 008d | 前端 401 未自动跳转登录 | Axios 拦截器检测 401 自动清除 token 并跳转 `/login` |
| 008e | 缺少 Servers 前端页面 | 新增 Servers 页面（列表、创建、凭据查看），添加路由和侧边栏菜单 |
| 008f | Issue 列表缺少排序选项 | 后端新增 `sort_by` 参数；前端添加排序选择器（创建时间/更新时间/优先级） |

### 代码质量

| # | 问题 | 修复 |
|---|------|------|
| 010a | `__import__("datetime")` 写法不规范 | 改为 `datetime.now(timezone.utc)` |
| 010b | `Comment.author` 默认值不一致 | 统一默认值为 `"user"` |
| 010c | Ant Design 按需导入 | Ant Design v6 + Vite 原生 tree-shaking，无需额外插件 |
| — | LIKE 通配符注入 | Issue 搜索转义 `%`、`_`、`\` 通配符 |
| — | Milestones N+1 查询 | 后端 list 接口聚合统计，前端单次请求获取全部数据 |
| — | Issues 分页 | 后端支持 `skip`/`limit` 分页，前端 Table 分页组件 |
| — | Auth 上下文 | `useAuth` 改为 Context Provider，全局共享登录状态 |

---

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
