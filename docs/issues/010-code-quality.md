# 010 - 代码质量问题

- **优先级**: P2
- **类型**: code-quality
- **状态**: open

## 问题描述

### 10a. SQLAlchemy `datetime.utcnow` 已弃用

多个 model 文件使用 `default=datetime.utcnow`，Python 3.12 已弃用此用法。应改为 `default=lambda: datetime.now(timezone.utc)`。

### 10b. `Comment.author` 默认值不一致

- `schemas/comment.py` 中 `CommentCreate.author` 默认值为 `"anonymous"`
- `mcp_server.py` 中 `add_issue_comment` 硬编码 `author: "ai_agent"`
- Issue 路由中 `log_activity` 的 `actor` 使用 `data.author or "user"`

当 AI Agent 通过 MCP 添加评论时，`author` 是 `"ai_agent"`，但 ActivityLog 的 `actor` 可能是 `"user"`（取决于请求来源）。

### 10c. 前端构建体积过大

生产构建输出 1.2MB+，Ant Design 应使用按需导入减少体积。

### 10d. 缺少 `.gitignore`

项目缺少 `.gitignore` 文件，`__pycache__/`、`.env`、`project_manager.db`、`node_modules/` 等可能被提交。

### 10e. 缺少后端测试覆盖

Phase 1/2 的测试都是临时脚本，没有持久化的测试文件。原有 `tests/` 目录下的测试文件没有更新以覆盖新模型（PlanItem、Server、ActivityLog）。

## 影响文件

- `src/models/*.py` — datetime.utcnow
- `src/schemas/comment.py` — author 默认值
- `frontend/` — Ant Design 全量导入
- 项目根目录 — 缺 .gitignore
- `backend/tests/` — 测试未更新
