# MCP Server 配置指南

Project Manager System 的 MCP Server 让 AI Coding Agent（如 CodeBuddy、Cline）可以直接与项目管理系统交互。

## 快速开始

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
# API 运行在 http://localhost:8000
```

### 2. 获取 Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password":"admin"}'
# 返回: {"access_token": "eyJ...", "token_type": "bearer"}
```

### 3. 配置 MCP

在 CodeBuddy / Cline 的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "project-manager": {
      "command": "python",
      "args": ["D:/AI-learning/tce_tiku/project_mananger_system/backend/mcp_server.py"],
      "env": {
        "PM_API_URL": "http://localhost:8000/api/v1",
        "PM_TOKEN": "your-jwt-token-here"
      }
    }
  }
}
```

> **注意**：将路径和 Token 替换为实际值。

### 4. 验证连接

配置完成后，AI Agent 可调用 `check_connection` 工具确认连通性。

---

## 可用工具一览

| 工具 | 功能 | 说明 |
|------|------|------|
| `check_connection` | 连接测试 | 验证 MCP 是否正常连接后端 |
| `create_issue` | 创建 Issue | 自动标记 `source=ai_agent` |
| `list_issues` | 查询 Issues | 支持 status/priority/source 筛选 |
| `update_issue_status` | 更新状态 | open/in_progress/review/deferred/closed/cancelled |
| `update_issue_priority` | 更新优先级 | P0/P1/P2/P3 |
| `defer_issue` | 暂缓 Issue | 推迟到指定 milestone |
| `add_issue_comment` | 添加评论 | 为 issue 添加 AI 评论 |
| `propose_plan` | 提议计划 | 创建 pending_approval 计划 |
| `list_plans` | 查询计划 | 可按状态筛选 |
| `update_plan_progress` | 更新计划进度 | 创建/更新 PlanItem |
| `list_milestones` | 查询阶段 | 列出所有 milestones |
| `list_servers` | 查询服务器 | 列出所有服务器 |
| `get_server_credentials` | 获取凭据 | 获取服务器用户名/密码 |

---

## 典型场景

### Agent 发现问题，创建 Issue

```
Agent 调用 create_issue(title="登录接口缺少参数校验", priority="P1", issue_type="bug")
→ Issue #5 创建成功，source=ai_agent
```

### Agent 发现代码可优化，提议计划

```
Agent 调用 propose_plan(title="重构数据访问层", description="统一使用 Repository 模式")
→ Plan #3 创建，status=pending_approval
→ 等待用户在仪表盘审批
```

### Agent 执行计划后更新进度

```
Agent 调用 update_plan_progress(plan_id=3, item_title="提取 BaseRepository", status="done")
→ PlanItem 标记为完成，前端可见
```

### Agent 发现低优先级问题，暂缓处理

```
Agent 调用 defer_issue(issue_id=7, milestone_id=2, reason="Phase 2 再处理")
→ Issue #7 标记为 deferred
```

---

## Docker 环境配置

如果使用 Docker 部署，MCP 配置中的 API 地址需指向宿主机：

```json
{
  "env": {
    "PM_API_URL": "http://host.docker.internal:8000/api/v1",
    "PM_TOKEN": "your-jwt-token"
  }
}
```

Windows 上使用 `host.docker.internal`，Linux 上使用 `localhost` 或宿主机 IP。

---

## 安全注意事项

- Token 有过期时间（JWT 24h），过期后需重新获取
- 服务器凭据（密码）为明文存储，仅用于本地单人环境
- 生产环境建议升级为 AES 加密存储
