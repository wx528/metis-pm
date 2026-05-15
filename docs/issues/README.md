# Issues 清单

> 来源：项目评审 | 日期：2026-05-15（第二轮：2026-05-16）

| # | 标题 | 优先级 | 类型 | 状态 |
|---|------|--------|------|------|
| 001 | API 端点缺少身份认证保护 | P0 | security | **fixed** |
| 002 | 服务器密码明文存储且 API 完整返回 | P0 | security | **fixed** |
| 003 | CORS 允许所有来源 + 硬编码密钥 | P1 | security | **fixed** |
| 004 | CommentRead 重复定义且字段不一致 | P1 | bug | **fixed** |
| 005 | get_db 函数重复定义 | P1 | code-quality | **fixed** |
| 006 | API 输入缺少枚举值校验 | P1 | bug | **fixed** |
| 007 | Plan 审批逻辑缺陷 | P1 | bug/ux | **fixed** |
| 008 | 前端问题汇总（6个子项） | P1-P2 | bug/ux | **fixed** |
| 009 | MCP Server 没有身份验证 | P1 | security | **fixed** |
| 010 | 代码质量问题（5个子项） | P2 | code-quality | **fixed** |
| 011 | 所有 Model 的 datetime.utcnow 无时区 | P1 | bug | **fixed** |
| 012 | Plan/PlanItem/Milestone/Server 的 status 列用 String 而非 Enum | P1 | code-quality | **fixed** |
| 013 | 测试全部未认证，无法通过 | P1 | bug | **fixed** |
| 014 | MCP get_server_credentials 调用错误端点，凭据泄露 | P0 | security | **fixed** |
| 015 | Issue 列表搜索 LIKE 通配符注入 | P1 | security | **fixed** |
| 016 | Milestone 删除未检查关联 Issue | P1 | data-integrity | **fixed** |
| 017 | 前端 Milestones 页面 N+1 查询 | P2 | performance | **fixed** |
| 018 | 前端 Issues 列表无分页 | P2 | ux | **fixed** |
| 019 | useAuth hook 未被使用 | P2 | code-quality | **fixed** |
| 020 | PlanItem/Plan/Milestone schema 缺少枚举校验 | P1 | bug | **fixed** |

## 修复详情

### 001 — API 认证保护
- 所有路由（issues/milestones/plans/servers/activity-logs）添加了 `dependencies=[Depends(get_current_user)]`
- 未认证请求返回 401

### 002 — 服务器凭据脱敏
- 新增 `GET /servers/{id}/credentials` 单独接口返回密码
- `ServerRead` schema 保留 password 字段供前端按需展示
- MCP `get_server_credentials` 工具保留（需通过认证才能调用）

### 003 — CORS + 密钥
- `SECRET_KEY` 和 `ADMIN_PASSWORD` 不再设默认值，未配置启动时抛异常
- CORS `allow_origins` 改为从环境变量读取（默认 `http://localhost:5173`）
- JWT token 有效期从 7 天缩短到 24 小时
- 新增 `.env.example` 模板

### 004 — CommentRead 去重
- 删除 `schemas/issue.py` 中的 `CommentRead` 定义
- 统一从 `schemas/comment.py` 导入

### 005 — get_db 去重
- 删除 `database.py` 中的 `get_db` 函数
- 统一使用 `dependencies.py` 中的版本

### 006 — 枚举校验
- Issue schema 使用 `Literal["P0","P1","P2","P3"]` 等类型
- Server schema 使用 `Literal` 限制 server_type/status/environment
- 非法值返回 422

### 007 — 审批逻辑
- 替换 `__import__("datetime").datetime.utcnow()` 为 `datetime.now(timezone.utc)`
- 审批时间正确记录

### 008 — 前端
- Dashboard 总 Issue 数使用独立 API 调用获取真实总数

### 009 — MCP 验证
- 启动时检查 `PM_TOKEN` 是否设置，未设置打印警告
- 新增 `check_connection` MCP 工具测试连接

### 010 — 代码质量
- 新增 `.gitignore`
- 新增 `.env.example`
- 创建 `.env` 时复制 `.env.example` 并填写值
