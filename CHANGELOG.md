# Changelog

## [0.8.0] - 2026-05-18

### Phase 8：内网部署就绪

#### CORS 动态配置

| 文件 | 变更 |
|------|------|
| `docker-compose.yml` | CORS_ORIGINS 改为从 .env 读取：`${CORS_ORIGINS:-http://localhost:8080}` |

#### SQLite 备份脚本

| 文件 | 变更 |
|------|------|
| `backend/backup.sh` | 新增备份脚本：一致性备份 → gzip 压缩 → 自动清理旧备份 |

#### Issue 类型扩展

| 文件 | 变更 |
|------|------|
| `backend/src/models/issue.py` | IssueType 新增 `IDEA = "idea"` |
| `frontend/src/pages/Issues.tsx` | 类型列增加颜色渲染，新增 idea 选项 |
| `frontend/src/components/IssueCard.tsx` | 新增 idea 类型颜色（gold） |

#### 版本号

| 文件 | 变更 |
|------|------|
| `VERSION` | 0.7.0 → 0.8.0 |
| `backend/main.py` | 版本号同步 |
| `docker-compose.yml` | APP_VERSION 同步 |

#### Ideas 目录整理

| 变更 | 说明 |
|------|------|
| `docs/ideas/inbox/` | 新增未分类目录 |
| 文件重命名 | 02-07.md → 描述性命名（kanban-dashboard.md 等） |
| 归类 | doing/ + backlog/ + done/ + notconsider/ |

---

## [0.7.0] - 2026-05-18

### Phase 7：安全治理（P0 修复）

#### P0-1: 服务器凭据 Fernet 加密存储

| 文件 | 变更 |
|------|------|
| `backend/src/core/crypto.py` | 新增加密工具模块，Fernet 对称加密/解密 |
| `backend/src/models/server.py` | password/ssh_key 改为 property，写入自动加密，读取自动解密 |
| `backend/src/settings.py` | 新增 `ENCRYPTION_KEY` 配置项 |
| `backend/.env.example` | 新增 `ENCRYPTION_KEY` 说明 |
| `backend/main.py` | 迁移：自动加密已有明文凭据 |
| `backend/requirements.txt` | 新增 `cryptography>=42.0.0` 依赖 |

#### P0-2: 凭据 API 角色权限控制 + 审计日志

| 文件 | 变更 |
|------|------|
| `backend/src/routes/auth.py` | 新增 `get_admin_user` 依赖（仅 admin 角色可访问） |
| `backend/src/routes/servers.py` | `GET /servers/{id}/credentials` 限制 admin 角色 + 审计日志记录 |

#### P0-3: MCP 工具不再返回明文凭据

| 文件 | 变更 |
|------|------|
| `backend/mcp_server.py` | `get_server_credentials` 改为仅返回凭据元数据（是否已设置），不再返回明文密码/SSH Key |

#### P0-4: CORS 配置收紧

| 文件 | 变更 |
|------|------|
| `backend/main.py` | `allow_methods` 从 `["*"]` 改为 `["GET", "POST", "PUT", "DELETE", "OPTIONS"]`，`allow_headers` 从 `["*"]` 改为 `["Authorization", "Content-Type"]` |

### P1 修复

#### P1-7: 工作流 RETRY 策略实现指数退避重试

| 文件 | 变更 |
|------|------|
| `backend/src/core/workflow_engine.py` | `on_failure=RETRY` 实现指数退避重试（最多 3 次，延迟 2/4/8 秒），不再直接标记失败 |

#### P1-9: MCP Token 缓存 401 自动重试

| 文件 | 变更 |
|------|------|
| `backend/mcp_server.py` | 新增 `_api_request()` 统一请求函数，401 时自动清缓存 → 重新登录 → 重试一次 |

### P2 修复

#### P2-11: MCP 错误处理统一

| 文件 | 变更 |
|------|------|
| `backend/mcp_server.py` | 所有 MCP 工具统一使用 `_api_request()` 发送请求，替代散落的 `httpx.AsyncClient` 直接调用 |

#### P2-13: check_server 实现 TCP 连通性检查

| 文件 | 变更 |
|------|------|
| `backend/src/routes/servers.py` | `POST /servers/{id}/check` 新增 TCP 连通性测试：可连通时恢复 active，不可连通时标记 offline |

### 其他改进

| 文件 | 变更 |
|------|------|
| `backend/tests/test_security.py` | 新增 25 个安全测试（加密/解密、权限控制、审计日志、CORS、JWT） |
| `backend/pytest.ini` | 修复 `[tool:pytest]` → `[pytest]`，使 `asyncio_mode=auto` 正确生效 |
| `backend/tests/conftest.py` | 新增 `AGENT_PASSWORDS` 和 `ENCRYPTION_KEY` 环境变量 |

## [0.6.0] - 2026-05-17

### Phase 6：工作流引擎

#### 后端 — 模型

| 模型 | 说明 |
|------|------|
| `Workflow` | name, trigger, trigger_config, status, created_by |
| `WorkflowStep` | workflow_id, step_type, config, sort_order, timeout_seconds, on_failure |
| `WorkflowRun` | workflow_id, triggered_by, status, current_step_index, context |

#### 步骤类型

| step_type | 说明 |
|-----------|------|
| `create_issue` | 自动创建 Issue |
| `update_issue` | 更新 Issue 状态/优先级 |
| `notify` | 发送通知 |
| `wait_approval` | 暂停等待人类审批 |
| `propose_plan` | 提议 Plan |

#### 触发机制

| trigger | 说明 | 状态 |
|---------|------|------|
| `on_issue_created` | Issue 创建时自动触发 | ✅ 已接入 issues 路由 |
| `on_plan_approved` | Plan 审批后自动触发 | ✅ 已接入 plans 路由 |
| `manual` | 手动触发 | ✅ API + MCP |
| `on_schedule` | 定时触发 | ⬜ 需 APScheduler |

#### 工作流引擎

| 功能 | 说明 |
|------|------|
| `WorkflowEngine.trigger()` | 触发工作流，创建 Run 并执行步骤 |
| `WorkflowEngine.resume()` | 审批后恢复执行 |
| 失败策略 | skip / abort / retry / notify_human |
| 上下文传递 | 步骤间通过 `run.context` 传递数据 |
| 自动触发钩子 | `check_and_trigger_workflows()` 检查匹配的工作流 |

#### API

| 端点 | 说明 |
|------|------|
| `GET /api/v1/workflows` | 工作流列表 |
| `POST /api/v1/workflows` | 创建工作流（含步骤） |
| `GET /api/v1/workflows/{id}` | 工作流详情（含步骤） |
| `PUT /api/v1/workflows/{id}` | 更新工作流 |
| `DELETE /api/v1/workflows/{id}` | 删除工作流 |
| `POST /api/v1/workflows/{id}/steps` | 添加步骤 |
| `DELETE /api/v1/workflows/{id}/steps/{step_id}` | 删除步骤 |
| `POST /api/v1/workflows/{id}/trigger` | 手动触发 |
| `GET /api/v1/workflows/runs` | 执行记录列表 |
| `GET /api/v1/workflows/runs/{id}` | 执行记录详情 |
| `POST /api/v1/workflows/runs/{id}/resume` | 审批后恢复 |

#### MCP 新增工具

| 工具 | 说明 |
|------|------|
| `list_workflows` | 列出工作流 |
| `create_workflow` | 创建工作流（含步骤） |
| `trigger_workflow` | 手动触发工作流 |
| `list_workflow_runs` | 查看执行记录 |

#### 前端

| 变更 | 说明 |
|------|------|
| 工作流列表页 | 名称 + 触发方式 + 状态 + 触发按钮 |
| 工作流详情 | 步骤流程图 + 描述信息 |
| 执行记录 | Timeline 展示，支持审批/拒绝 |
| 新建弹窗 | 名称 + 触发方式选择 |
| 侧边栏菜单 | "工作流" + ⚡ 图标 |
| 路由 | `/projects/{slug}/workflows` |

---

## [0.5.0] - 2026-05-17

### Phase 5：看板 + 数据看板（第一阶段 — Stats API + Dashboard 增强）

#### Stats API（4 个统计端点）

| 端点 | 说明 |
|------|------|
| `GET /api/v1/stats/agent-productivity` | Agent 产出统计：按 actor 统计创建/完成的 Issue 数，支持 week/month/all |
| `GET /api/v1/stats/issue-resolution` | Issue 解决时长：平均值/中位数/P90，按类型分组 |
| `GET /api/v1/stats/plan-completion` | Plan 完成率：环形进度 + 按 Plan 分项统计 |
| `GET /api/v1/stats/agent-activity` | Agent 活跃度：每日操作次数时序 + 操作类型分布 |

#### Dashboard 增强

| 变更 | 说明 |
|------|------|
| Agent 产出对比 | 水平柱状图显示各 Agent 创建/完成的 Issue 数 |
| Plan 完成率 | 环形进度图 + 分项进度条 |
| 时间筛选 | 本周/本月/全部 切换 |

#### 看板视图

| 变更 | 说明 |
|------|------|
| 5 列看板 | Open / In Progress / Review / Deferred / Closed |
| 拖拽改状态 | 拖到另一列自动调用 `update_issue_status` API |
| Deferred 处理 | 拖到 Deferred 列自动选择第一个里程碑暂缓 |
| Issue 卡片 | 显示 ID + 标题 + 优先级 + 类型 + 来源图标 |
| 里程碑筛选 | 看板顶部 Select 按里程碑筛选 |
| 乐观更新 | 拖拽后先更新 UI，API 失败时回滚 |
| 侧边栏菜单 | 新增"看板"菜单项 + `AppstoreOutlined` 图标 |

#### 前端路由

| 路由 | 说明 |
|------|------|
| `/projects/{slug}/board` | 看板视图 |

#### 新增依赖

| 包 | 说明 |
|------|------|
| `@dnd-kit/core` | 拖拽核心 |
| `@dnd-kit/sortable` | 排序扩展 |
| `@dnd-kit/utilities` | 工具函数 |

| 变更 | 说明 |
|------|------|
| Milestone ActivityLog | 创建/更新/删除里程碑时记录活动日志（N002） |
| Notification.updated_at | 新增 updated_at 字段 + 数据库迁移（N005） |
| 前端 Notification 类型 | 补充 updated_at 字段 |

---

## [0.4.1] - 2026-05-17

### v0.4.0 评审修复

| 优先级 | 问题 | 修复 |
|--------|------|------|
| P0 | 删除项目无级联检查，产生孤立数据 | 有关联数据时返回 409 拒绝删除 |
| P0 | Agent 创建 Issue 使用 `TASK_COMPLETED` 通知类型，语义错误 | 新增 `TASK_CREATED` 类型 |
| P0 | SSE 断线无自动重连 | 添加指数退避重连（1s→2s→4s→…最大30s），401 不重连 |
| P1 | Project 列表 N+1 查询 | 抽取 `_get_project_stats()` 公共函数，条件聚合优化 |
| P1 | `mark_all_read` 逐条更新 | 改为批量 `UPDATE` 语句 |
| P1 | `update_project` 允许修改 slug | `ProjectUpdate` schema 移除 `slug` 字段 |
| P1 | 通知列表不支持 `project_id` 过滤 | `list_notifications` 新增 `project_id` 参数 |
| P2 | Project 模型缺少 `notifications` relationship | 补充声明 |
| P2 | ActivityLog 缺少 `project` relationship | 补充声明 |
| P2 | 前端 SSE URL 拼接逻辑混乱 | 清理为直接构建 URL，去掉冗余 `replace` |
| P2 | LIKE 搜索手动转义 `autoescape=False` | 改为 `autoescape=True`，使用 SQLAlchemy 内建安全机制 |

---

## [0.4.0] - 2026-05-17

### Phase 4：多项目 + 通知 + SSE

#### 多项目支持

| 变更 | 说明 |
|------|------|
| `Project` 模型 | 新增 name, slug, description, repo_url, status, owner, default_milestone_id |
| `project_id` 外键 | Issue, Milestone, Plan, Server, ActivityLog 均新增 `project_id` 列 |
| 数据迁移 | 自动创建 "default" 项目，回填所有现有数据的 `project_id` |
| Project CRUD | `GET/POST/PUT/DELETE /api/v1/projects` |
| Project 统计 | 列表和详情返回 issue_count, plan_count, milestone_count, server_count |
| 前端项目切换器 | 侧边栏顶部 Dropdown 切换项目，localStorage 记住选择 |
| URL 结构 | `/projects/{slug}/dashboard`, `/projects/{slug}/issues` 等 |
| 旧路由兼容 | `/issues`, `/plans` 等旧路由自动重定向到 default 项目 |

#### 通知系统

| 变更 | 说明 |
|------|------|
| `Notification` 模型 | 新增 recipient, type, title, body, entity_type, entity_id, read, created_by |
| 通知类型 | `approval_needed`, `task_completed`, `task_failed`, `mention`, `workflow_paused`, `info` |
| 通知 CRUD | `GET /api/v1/notifications`, `PUT /{id}/read`, `PUT /read-all`, `GET /unread-count` |
| 通知触发 | Plan 待审批 → 通知 admin；Agent 完成 Issue → 通知 admin；审批结果 → 通知提议者 |
| SSE 推送 | `GET /api/v1/notifications/stream` 实时推送新通知 |
| 前端铃铛 | Header 显示未读数 Badge + 通知抽屉列表 |
| SSE 客户端 | 前端 fetch ReadableStream 接收实时通知 + 30s 心跳 |

#### MCP 工具新增/更新

| 工具 | 变更 |
|------|------|
| `list_projects` | 新增：列出所有项目含统计 |
| `create_issue` | 新增 `project_id` 参数 |
| `list_issues` | 新增 `project_id` 筛选 |
| `propose_plan` | 新增 `project_id` 参数 |
| `list_plans` | 新增 `project_id` 筛选 |
| `list_milestones` | 新增 `project_id` 筛选 |
| `list_servers` | 新增 `project_id` 筛选 |
| `check_notifications` | 新增：检查当前 Agent 的通知 |
| `mark_notification_read` | 新增：标记通知已读 |

#### Nginx SSE 支持

| 变更 | 说明 |
|------|------|
| `proxy_buffering off` | 禁用 Nginx 缓冲，确保 SSE 实时推送 |
| `proxy_read_timeout 86400s` | 长连接超时 24h |

### 验证清单

```
[x] 创建 Project 模型 + 迁移，现有数据归入 default 项目
[x] 所有查询支持 project_id 过滤
[x] Notification 模型 + CRUD + 触发逻辑
[x] SSE 推送端点 + 前端实时接收
[x] 前端项目切换器 + URL 结构变更
[x] 前端通知铃铛 + 通知列表
[x] MCP 新增 list_projects / check_notifications
[x] Nginx 配置更新（SSE 支持）
[x] 旧路由兼容：重定向到 default 项目
```

---

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

### Trae IDE 项目级 MCP 配置

新增 `.trae/mcp.json`，支持 Trae IDE 自动加载 project-manager MCP Server，无需手动在设置中添加。

```json
// .trae/mcp.json（项目级配置，Trae IDE 自动加载）
{
  "mcpServers": {
    "project-manager": {
      "command": "python",
      "args": ["d:/AI-learning/tce_tiku/project_mananger_system/backend/mcp_server.py"],
      "env": {
        "PM_API_URL": "http://localhost:8000/api/v1",
        "PM_AGENT_PASSWORD": "CHANGE-ME"
      }
    }
  }
}
```

> 注意：需在 Trae 设置 → MCP 中开启「启用项目级 MCP」开关。

### v2 设计文档

新增 [system-design-02.md](docs/design/system-design-02.md) 和 [phase-plan-02.md](docs/plan/phase-plan-02.md)，规划从"人机协作工具"到"一人项目组操作系统"的演进路线：

| Phase | 版本 | 核心功能 |
|-------|------|----------|
| Phase 4 | v0.4.0 | 多项目支持 + 通知系统 + SSE 推送 |
| Phase 5 | v0.5.0 | 拖拽看板 + 数据看板 + Agent 统计 |
| Phase 6 | v0.6.0 | 工作流引擎 + 内置模板 + 自动触发 |

### 验证结果

| 测试 | 结果 |
|------|------|
| `admin` 密码登录 → `sub: "admin"`, `role: "admin"` | ✅ |
| `CHANGE-ME` 密码登录 → `sub: "cline"`, `role: "agent"` | ✅ |
| `CHANGE-ME` 密码登录 → `sub: "codebuddy"`, `role: "agent"` | ✅ |
| `CHANGE-ME` 密码登录 → `sub: "trae"`, `role: "agent"` | ✅ |
| 错误密码 → 401 拒绝 | ✅ |
| cline 创建 issue → ActivityLog `actor: "cline"` | ✅ |
| codebuddy 创建 issue → ActivityLog `actor: "codebuddy"` | ✅ |
| trae MCP 连接 → Identity: trae (role=agent) | ✅ |
| trae MCP 创建 Issue #10 → ActivityLog `actor: "trae"` | ✅ |

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
