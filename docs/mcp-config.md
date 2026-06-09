# MCP Server 配置指南

Project Manager System 的 MCP Server 让 AI Coding Agent（如 CodeBuddy、Cline）可以直接与项目管理系统交互。

> 适用版本: v0.7.0+
> 最后更新: 2026-05-18

## 零、角色与分工

Project Manager System 支持多角色 Agent 协作：

| 角色 | 职责 | 推荐 IDE | MCP Server |
|------|------|---------|-----------|
| **agent** | 日常开发：编码、创建 issue、完成 plan | Cursor / Trae | `mcp_server.py` |
| **mate** | 架构审查：审查代码、批准 plan | Cline / Windsurf | `mcp_server_mate.py` |
| **tester** | 测试验证：提交 bug、验证修复 | 独立终端 | `mcp_server_tester.py` |
| **registrar** | 项目登记：初始化项目、创建里程碑 | CLI 脚本 | `mcp_server_registrar.py` |

每个角色使用独立的密码，在 `.env` 中配置：

```env
AGENT_PASSWORDS=trae:CHANGE-ME,cursor:cursor-2026,mate:mate-2026,tester:tester-2026,registrar:CHANGE-ME
```

---

## 一、快速开始（HTTP 模式）

### 1. 确保后端已运行

```bash
# Docker 部署（推荐，自动启动所有 MCP Server）
docker compose up -d

# 或本地开发
cd backend && python main.py
```

### 2. 配置 MCP

在 IDE（Cursor / Cline / Trae）的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "pm-agent": {
      "url": "http://localhost:9000/mcp",
      "headers": {
        "X-PM-Password": "your-agent-password"
      }
    }
  }
}
```

**配置项说明**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `url` | ✅ | MCP Server 地址，Docker 为 `http://localhost:9000/mcp`，内网为 `http://192.168.1.100:9000/mcp` |
| `headers.X-PM-Password` | ✅ | Agent 密码，对应 `.env` 中 `AGENT_PASSWORDS` 的某一项 |

### 3. 验证连接

在 AI Agent 对话中请求：

```
请用 check_connection 工具测试连接
```

预期返回：

```
Connected OK. Identity: trae (role=agent)
```

---

## 二、内网部署配置

当后端部署到内网服务器时（如 Tailscale/家服），修改 `url` 为服务器内网 IP：

```json
{
  "mcpServers": {
    "pm-agent": {
      "url": "http://192.168.1.100:9000/mcp",
      "headers": {
        "X-PM-Password": "CHANGE-ME"
      }
    }
  }
}
```

> 详见 [内网部署指南](deploy-guide.md)

---

## 三、角色配置实例

### 统一入口（推荐）

所有角色**共用同一个 URL**，通过不同的 `X-PM-Password` 自动识别角色：

```json
{
  "mcpServers": {
    "pm-agent": {
      "url": "http://localhost:9000/mcp",
      "headers": {
        "X-PM-Password": "CHANGE-ME"
      }
    },
    "pm-mate": {
      "url": "http://localhost:9000/mcp",
      "headers": {
        "X-PM-Password": "mate-2026"
      }
    },
    "CHANGE-MEer": {
      "url": "http://localhost:9000/mcp",
      "headers": {
        "X-PM-Password": "tester-2026"
      }
    }
  }
}
```

> **关键区别**：所有角色使用**同一个端口 9000**，只需修改密码即可切换角色权限。身份由 `.env` 中的 `AGENT_PASSWORDS` 自动解析。

---

## 四、可用工具一览（22 个）

### 通用

| 工具 | 功能 |
|------|------|
| `check_connection` | 测试 MCP 与后端 API 连接 |

### 项目

| 工具 | 功能 |
|------|------|
| `list_projects` | 列出所有项目（含统计） |
| `create_project` | 创建新项目（slug 只允许小写字母/数字/连字符） |

### Issue

| 工具 | 功能 |
|------|------|
| `create_issue` | 创建 Issue，source 自动标记为 ai_agent |
| `list_issues` | 查询 Issues，支持 status/priority/source/milestone 筛选 |
| `update_issue_status` | 更新状态: open/in_progress/review/deferred/closed/cancelled |
| `update_issue_priority` | 更新优先级: P0/P1/P2/P3 |
| `defer_issue` | 暂缓 Issue 到指定 milestone |
| `add_issue_comment` | 为 Issue 添加评论 |

### 计划

| 工具 | 功能 |
|------|------|
| `propose_plan` | 提议计划（status=pending_approval，等待人类审批） |
| `list_plans` | 查询计划列表 |
| `update_plan_progress` | 更新计划项进度（不存在则自动创建） |

### 里程碑

| 工具 | 功能 |
|------|------|
| `list_milestones` | 查询里程碑列表（含 Issue 统计） |
| `create_milestone` | 创建里程碑（支持 phase/due_date） |

### 服务器

| 工具 | 功能 |
|------|------|
| `list_servers` | 查询服务器列表 |
| `get_server_credentials` | 查询凭据元数据（**仅返回是否已设置，不含明文密码**） |

> 🔒 出于安全考虑，`get_server_credentials` 仅返回"密码: 已设置/未设置"等元信息。如需查看完整凭据，请通过 Web UI 以 admin 身份访问。

### 通知

| 工具 | 功能 |
|------|------|
| `check_notifications` | 检查当前 Agent 的通知 |
| `mark_notification_read` | 标记通知已读 |

### 工作流

| 工具 | 功能 |
|------|------|
| `list_workflows` | 列出工作流 |
| `create_workflow` | 创建工作流（trigger: on_issue_created/on_plan_approved/manual） |
| `trigger_workflow` | 手动触发工作流 |
| `list_workflow_runs` | 查看工作流执行记录 |

### 协作工具（新增）

| 工具 | 功能 |
|------|------|
| `notify_role` | 给指定角色发送通知（如通知 mate 审查） |
| `get_handover_template` | 获取交接评论模板（dev_complete / review_feedback / test_report） |

#### notify_role 示例

```
Agent 完成开发后调用：
notify_role(target_role="mate", title="Issue #5 开发完成待审查", entity_type="issue", entity_id=5)
→ Mate 的 check_notifications 会收到此通知
```

#### get_handover_template 示例

```
get_handover_template(template_name="dev_complete")
→ 返回 Markdown 格式的开发完成交接模板
Agent 填写后通过 add_issue_comment(comment_type="handover") 发送
```

---

## 五、典型场景

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

### Agent 触发自动化工作流

```
Agent 调用 trigger_workflow(workflow_id=5)
→ WorkflowRun 创建，步骤自动执行
```

---

## 六、安全注意事项

- **凭据已加密**：服务器密码和 SSH Key 使用 Fernet 对称加密存储，密钥从 `ENCRYPTION_KEY` 环境变量读取
- **凭据 API 限 admin**：`GET /servers/{id}/credentials` 仅 admin 角色可访问，且有审计日志
- **MCP 不泄露明文**：`get_server_credentials` 工具仅返回元数据，密码/密钥不会进入 AI 上下文
- **JWT 24h 过期**：Token 签发后 24 小时过期，MCP Server 遇 401 自动重新登录
- **CORS 已收紧**：仅允许配置的前端地址访问 API
