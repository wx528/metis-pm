# RBAC (Role-Based Access Control) 文档

## 概述

Project Manager System 使用基于角色的访问控制 (RBAC) 来管理不同 Agent 的权限。系统定义了 5 个角色，每个角色具有不同的工具访问权限和 API 操作权限。

## 角色定义

| 角色 | 标识 | 说明 |
|------|------|------|
| **Admin** | `admin` | 系统管理员，拥有所有权限 |
| **Agent** | `agent` | 开发工人，执行日常开发任务 |
| **Mate** | `mate` | 大副/审查员，负责审批和分配 |
| **Tester** | `tester` | 测试员，负责质量验证 |
| **Registrar** | `registrar` | 登记员，负责项目和用户管理 |

## 权限矩阵

### MCP 工具权限

| 工具 | Admin | Agent | Mate | Tester | Registrar |
|------|:-----:|:-----:|:----:|:------:|:---------:|
| **共享工具 (18个)** |
| `check_connection` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `get_context` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `get_project_summary` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `list_issues` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `get_issue` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `add_issue_comment` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `list_comments` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `notify_role` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `check_notifications` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `mark_notification_read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `mark_handover_read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `check_unread_handovers` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `list_workflows` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `get_workflow` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `trigger_workflow` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `get_handover_template` | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Agent 专属 (19个)** |
| `get_my_recent_actions` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `create_issue` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `update_issue` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `delete_issue` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `create_plan` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `get_plan` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `update_plan` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `delete_plan` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `list_my_plans` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `create_milestone` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `update_milestone` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `list_milestones` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `create_workflow` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `update_workflow` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `delete_workflow` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `update_workflow_step` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `add_workflow_step` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `remove_workflow_step` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `get_workflow_step` | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Mate 专属 (7个)** |
| `list_pending_plans` | ✅ | ❌ | ✅ | ❌ | ❌ |
| `approve_plan` | ✅ | ❌ | ✅ | ❌ | ❌ |
| `list_active_plans_progress` | ✅ | ❌ | ✅ | ❌ | ❌ |
| `reject_plan` | ✅ | ❌ | ✅ | ❌ | ❌ |
| `assign_issue` | ✅ | ❌ | ✅ | ❌ | ❌ |
| `set_issue_priority` | ✅ | ❌ | ✅ | ❌ | ❌ |
| `get_agent_activities` | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Tester 专属 (7个)** |
| `report_bug` | ✅ | ❌ | ❌ | ✅ | ❌ |
| `create_test_plan` | ✅ | ❌ | ❌ | ✅ | ❌ |
| `get_test_plan` | ✅ | ❌ | ❌ | ✅ | ❌ |
| `update_test_plan` | ✅ | ❌ | ❌ | ✅ | ❌ |
| `delete_test_plan` | ✅ | ❌ | ❌ | ✅ | ❌ |
| `list_test_plans` | ✅ | ❌ | ❌ | ✅ | ❌ |
| `execute_test` | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Registrar 专属 (6个)** |
| `register_project` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `list_registrations` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `get_registration` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `update_registration` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `mark_scanned` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `delete_registration` | ✅ | ❌ | ❌ | ❌ | ✅ |

### API 路由权限

| 路由 | 允许角色 |
|------|---------|
| `GET /api/v1/issues` | admin, agent, tester |
| `POST /api/v1/issues` | admin, agent, tester |
| `PUT /api/v1/issues/{id}` | admin, agent |
| `DELETE /api/v1/issues/{id}` | admin |
| `POST /api/v1/plans` | admin, agent |
| `PUT /api/v1/plans/{id}` | admin, agent |
| `POST /api/v1/plans/{id}/approve` | admin, mate |
| `POST /api/v1/plans/{id}/reject` | admin, mate |
| `GET /api/v1/servers` | admin, agent |
| `POST /api/v1/servers` | admin |
| `GET /api/v1/servers/{id}/credentials` | admin |

## 认证流程

1. **密码验证**: Agent 使用密码登录，`settings.resolve_identity()` 使用 bcrypt 验证密码哈希
2. **JWT 签发**: 验证通过后签发 JWT Token，包含 `sub` (身份) 和 `role` (角色)
3. **请求验证**: 后续请求携带 JWT Token，`get_current_user()` 验证 Token 有效性
4. **权限检查**: `require_role()` 装饰器检查用户角色是否在允许列表中

## 安全配置

### 密码格式 (JSON)

```json
{
  "agent1": {
    "password_hash": "$2b$12$...",
    "role": "agent"
  },
  "mate1": {
    "password_hash": "$2b$12$...",
    "role": "mate"
  }
}
```

### 环境变量

| 变量 | 说明 | 必需 |
|------|------|------|
| `SECRET_KEY` | JWT 签名密钥 (≥32字符) | ✅ |
| `ADMIN_PASSWORD_HASH` | Admin 密码 bcrypt 哈希 | ✅ |
| `AGENT_PASSWORDS_JSON` | Agent 密码 JSON 配置 | ✅ |
| `ENCRYPTION_KEY` | 服务器凭据加密密钥 | ✅ |

### 密码哈希生成

```bash
python -c "import bcrypt; print(bcrypt.hashpw('your_password'.encode(), bcrypt.gensalt()).decode())"
```

## 审计日志

系统记录以下安全事件到 `activity_logs` 表：
- 登录成功/失败
- 权限拒绝
- 敏感操作（查看凭据、删除资源）
