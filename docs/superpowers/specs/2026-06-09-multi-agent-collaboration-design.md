# 多 Agent 协作工作流设计文档

> 让多个 AI Coding Agent（IDE/工具）通过 MCP 接入 Project Manager System，实现角色分工与协作。  
> 版本: 1.1.0  
> 日期: 2026-06-09

---

## 1. 设计目标

- 支持 3+ 个编程工具（IDE/Agent）同时接入，每个分配明确角色
- Agent 之间能"喊话"（通知）和"交接"（评论模板）
- 用户通过 Dashboard 实时查看各 Agent 状态和待办

---

## 2. 角色与分工

| 角色 | 职责 | 推荐 IDE |
|------|------|---------|
| **agent** | 日常开发：编码、创建 issue、更新状态、完成 plan | Cursor / Trae |
| **mate** | 架构审查：审查代码、批准 plan、协调冲突 | Cline / Windsurf |
| **tester** | 测试验证：提交 bug、验证修复、退回不合格 | 独立终端 / 脚本 |
| **registrar** | 项目登记：初始化项目、创建里程碑 | CLI 脚本 |

每个角色对应独立的 MCP Server 实例，通过不同密码区分身份。

---

## 3. MCP 配置层

### 3.1 密码配置（`.env`）

```env
AGENT_PASSWORDS=trae:CHANGE-ME,cursor:cursor-2026,mate:mate-2026,tester:tester-2026,registrar:CHANGE-ME
```

### 3.2 IDE 配置示例

#### Cursor / Trae — Agent 角色（stdio 模式）

```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "python",
      "args": ["D:/project-manager-system/backend/mcp_server.py"],
      "env": {
        "PM_API_URL": "http://localhost:8000/api/v1",
        "PM_AGENT_PASSWORD": "cursor-2026"
      }
    }
  }
}
```

#### Cline — Mate 角色（stdio 模式）

```json
{
  "mcpServers": {
    "pm-mate": {
      "command": "python",
      "args": ["D:/project-manager-system/backend/mcp_server_mate.py"],
      "env": {
        "PM_API_URL": "http://localhost:8000/api/v1",
        "PM_AGENT_PASSWORD": "mate-2026"
      }
    }
  }
}
```

#### 远程 Tester — HTTP 模式

```json
{
  "mcpServers": {
    "CHANGE-MEer": {
      "url": "http://localhost:9002/mcp",
      "headers": {
        "X-PM-Password": "tester-2026"
      }
    }
  }
}
```

### 3.3 验证

Agent 启动后调用 `check_connection`，预期返回：

```
Connected OK. Identity: cursor (role=agent)
```

---

## 4. 角色间通信机制

### 4.1 通知层：`notify_role` MCP 工具

所有 MCP Server 增加此工具：

```python
@mcp.tool()
async def notify_role(
    target_role: str,        # "agent" | "mate" | "tester" | "registrar" | "admin"
    title: str,
    body: str,
    entity_type: Optional[str] = None,   # "issue" | "plan" | ...
    entity_id: Optional[int] = None,
) -> str:
    """给指定角色发送通知"""
```

**后端改动**：
- 通知模型 `recipient` 字段支持角色名（如 `"mate"`）
- `_recipient_filter` 扩展：当 recipient 为角色名时，该角色所有 Agent 可见
- 新增通知类型：`NotificationType.ROLE_NOTIFICATION`

**使用示例**：

```
Agent 完成 Issue #5 开发
→ notify_role(target_role="mate", title="Issue #5 开发完成待审查", entity_type="issue", entity_id=5)
→ Mate 的 check_notifications 看到此通知
```

### 4.2 评论层：HANDOVER 评论类型

扩展 `CommentType`：

```python
class CommentType:
    NORMAL = "normal"
    MANAGEMENT = "management"
    HANDOVER = "handover"       # 新增：交接评论
```

**MCP 改动**：
- `add_issue_comment` 新增 `comment_type` 参数，支持 `"handover"`
- 前端 `ActivityTimeline` 对 handover 类型显示 🔄 标识

---

## 5. 交接标准模板

Agent 调用 `get_handover_template(template_name)` 获取模板，填空后作为 handover 评论发送。

### 5.1 开发完成交接（Agent → Mate/Tester）

```markdown
## 交接: Issue #{id} 开发完成

### 改动范围
- 文件: 
- 涉及接口: 

### 测试情况
- [ ] 单元测试通过
- [ ] 集成测试通过

### 已知问题/注意点
- 

### 下一步
- 请 @mate 审查代码
- 或请 @tester 执行集成测试
```

### 5.2 审查反馈（Mate → Agent）

```markdown
## 审查反馈: Issue #{id}

### 通过项
- 

### 待修复
- [ ] 

### 优先级
- 建议修复后合并，不阻塞
- 或 必须修复，阻塞发布
```

### 5.3 测试报告（Tester → Agent/Mate）

```markdown
## 测试报告: Issue #{id}

### 测试环境
- 分支: 
- 数据库: 

### 结果
- [ ] 功能正常
- [ ] 发现 Bug（见下方）

### Bug 详情
- 步骤: 
- 预期: 
- 实际: 
- 建议: 修复后重新 @tester 验证
```

### 5.4 前端渲染

Handover 评论在前端渲染为**结构化卡片**：
- 提取标题、复选框、@提及
- 不同模板类型不同颜色边框
- 可点击复选框标记完成（仅相关角色可操作）

---

## 6. 前端 Agent 活动面板

### 6.1 后端 API：`GET /api/v1/dashboard/agents`

```json
{
  "agents": [
    {
      "role": "agent",
      "identity": "cursor",
      "last_active": "2026-06-09T10:30:00Z",
      "status": "online",
      "today_created": 3,
      "today_completed": 2,
      "pending_tasks": 1
    },
    {
      "role": "mate",
      "identity": "cline-mate",
      "last_active": "2026-06-09T09:15:00Z",
      "status": "online",
      "today_reviewed": 5,
      "pending_tasks": 2
    },
    {
      "role": "tester",
      "identity": "tester-1",
      "last_active": "2026-06-09T08:00:00Z",
      "status": "idle",
      "pending_tasks": 3
    }
  ],
  "pending_handovers": [
    {
      "issue_id": 5,
      "from_role": "agent",
      "to_role": "mate",
      "title": "登录接口重构完成",
      "created_at": "2026-06-09T10:00:00Z"
    }
  ]
}
```

**状态规则**：
- `online`：1 小时内有 activity_log 记录
- `idle`：4 小时内有记录
- `offline`：超过 4 小时无记录

**数据来源**：
- `last_active`：`activity_log` 按 identity 取最新
- `today_*`：当日 activity_log 聚合
- `pending_tasks`：按角色逻辑（agent=处理中 issue, mate=待审查, tester=待验证）

### 6.2 前端组件：`AgentActivityPanel`

放置在 Dashboard 页面顶部：

```
┌──────────────────────────────────────────────────────────────┐
│  🤖 Agent 协作看板                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ 🟢 cursor│  │ 🟢 mate  │  │ 🟡tester │                   │
│  │ 创建3    │  │ 审查5    │  │ 验证1    │                   │
│  │ 待办1    │  │ 待办2    │  │ 待办3    │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
│                                                              │
│  📋 待交接任务                                                │
│  Issue #5 登录接口重构 → mate审查 [查看]                      │
│  Issue #3 搜索缓存优化 → tester测试 [查看]                    │
└──────────────────────────────────────────────────────────────┘
```

**交互**：
- 点击角色卡片：展开该角色今日活动时间线
- 点击交接任务：跳转 Issue 详情，handover 评论高亮
- 数据每 60 秒自动刷新

---

## 7. 数据流图

```
┌──────────┐   notify_role    ┌──────────────┐
│ Agent A  │ ───────────────► │ Notification │
│ (agent)  │                  │   数据库      │
└──────────┘                  └──────┬───────┘
     │                               │
     │ add_comment(type=handover)    │ Agent B 轮询
     ▼                               ▼
┌──────────┐                  ┌──────────┐
│ Comment  │                  │ Agent B  │
│  数据库   │                  │ (mate)   │
└──────────┘                  └──────────┘
     │                               │
     │ ActivityLog                   │ 处理通知
     ▼                               ▼
┌──────────┐                  ┌──────────┐
│Dashboard │ ◄──────────────── │ 前端面板  │
│ Agents API│   聚合展示        │ 实时刷新  │
└──────────┘                  └──────────┘
```

---

## 8. 实现范围

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/src/routes/agent_status.py` | Agent 状态聚合 API |
| `frontend/src/components/AgentActivityPanel.tsx` | Agent 协作看板组件 |
| `frontend/src/api/agentStatus.ts` | 前端 API 封装 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `backend/mcp_server.py` | 新增 `notify_role`, `get_handover_template` |
| `backend/mcp_server_mate.py` | 同上 |
| `backend/mcp_server_tester.py` | 同上 |
| `backend/src/models/comment.py` | 新增 HANDOVER 类型 |
| `backend/src/models/notification.py` | 新增 ROLE_NOTIFICATION 类型 |
| `backend/src/routes/notifications.py` | 扩展 `_recipient_filter` 支持角色名 |
| `backend/src/routes/dashboard.py` | 新增 `/agents` 子路由 |
| `frontend/src/pages/Dashboard.tsx` | 嵌入 AgentActivityPanel |
| `frontend/src/components/ActivityTimeline.tsx` | 支持 handover 类型渲染 |
| `docs/mcp-config.md` | 扩展为角色配置手册 |

---

## 9. 典型工作流

### 场景：Agent 开发 → Mate 审查 → Tester 验证

1. **Agent (cursor)** 编码完成，调用 `get_handover_template("dev_complete")` 获取模板
2. Agent 填写后通过 `add_issue_comment(comment_type="handover")` 发送到 Issue #5
3. Agent 调用 `notify_role(target_role="mate", title="Issue #5 待审查", entity_id=5)`
4. **Mate (cline-mate)** 的 `check_notifications` 看到通知，打开 Issue #5 查看 handover 评论
5. Mate 审查通过，添加 handover 评论 `"审查通过，可进入测试"`，并 `notify_role(target_role="tester", ...)`
6. **Tester (tester-1)** 收到通知，执行测试，添加测试报告 handover 评论
7. 测试通过，Tester 更新 Issue 状态为 closed，Agent 和 Mate 收到通知

全程用户在 Dashboard 的 Agent 活动面板实时可见各角色状态和交接进度。

---

## 10. 安全与边界

- `notify_role` 只能通知角色，不能读取其他 Agent 的私有通知
- Handover 评论遵循 Issue 权限，未授权角色不可见
- Agent 状态面板仅展示聚合统计，不暴露具体操作内容
- 所有操作写入 ActivityLog，可审计追溯
