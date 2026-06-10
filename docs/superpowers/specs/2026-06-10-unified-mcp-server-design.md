# 统一 MCP Server 模块化重构设计

> **日期**: 2026-06-10  
> **状态**: 待实施  
> **作者**: AI Agent  
> **关联**: 架构审查报告问题 #1（MCP 部署复杂性）

---

## 1. 背景与目标

### 1.1 当前问题

系统目前有 **5 个 MCP Server 文件**存在于代码库中：

| 文件 | 大小 | 工具数 | 角色 | 状态 |
|------|------|--------|------|------|
| `mcp_server.py` | 44KB | 35 | agent | 历史遗留，已停用 |
| `mcp_server_mate.py` | 24KB | 20 | mate | 历史遗留，已停用 |
| `mcp_server_tester.py` | 21KB | 16 | tester | 历史遗留，已停用 |
| `mcp_server_registrar.py` | 12KB | 7 | registrar | 历史遗留，已停用 |
| `mcp_server_unified.py` | 71KB | 55 | 全部 | **当前运行中** |

`mcp_server_unified.py` 虽然承担了所有角色，但存在以下问题：
- **单一文件过大**（1746 行），难以维护和定位
- **角色职责混杂**，Agent 专属工具和 Mate 专属工具混在一起
- **测试困难**，无法单独测试某个角色的工具集
- **代码重复**，共享工具在每个旧文件中都有一份副本

### 1.2 目标

- 将 `mcp_server_unified.py` **模块化拆分**，每个角色一个文件
- **删除 4 个历史遗留文件**，清理代码库
- 保留**单一进程**架构，docker-compose 配置不变
- 保持**向后兼容**，现有 MCP 客户端配置无需修改

---

## 2. 新架构设计

### 2.1 目录结构

```
backend/
├── mcp_server_unified.py          # 入口文件 (~150 行)
├── mcp_tools/                     # 工具模块包 (新)
│   ├── __init__.py               # 暴露 register_all_tools()
│   ├── shared.py                 # 共享工具 (所有角色可用)
│   ├── agent.py                  # Agent 专属工具
│   ├── mate.py                   # Mate 专属工具
│   ├── tester.py                 # Tester 专属工具
│   └── registrar.py              # Registrar 专属工具
└── mcp_common.py                 # 共享基础设施 (保持不变)
```

### 2.2 模块职责

#### `mcp_server_unified.py` — 入口与编排

职责：
- 创建 FastMCP 实例
- 初始化认证中间件 (`PasswordMiddleware`)
- 定义 `require_role` 和 `safe_tool` 装饰器
- 调用各模块的 `register_tools()` 注册工具
- 启动 HTTP 服务 (`mcp.run()`)

约束：**不定义任何工具函数**，只做入口和基础设施。

#### `mcp_tools/shared.py` — 共享工具

所有角色都能调用的工具：
- `check_connection()` — 健康检查
- `get_context()` — 全局态势感知
- `notify_role()` — 向指定角色发送通知
- `get_handover_template()` — 获取交接模板
- `list_projects()` — 项目列表
- `list_milestones()` — 里程碑列表
- `check_notifications()` — 检查通知
- `mark_notification_read()` — 标记通知已读

#### `mcp_tools/agent.py` — Agent 专属

Agent 角色（开发工人）的核心工具：
- `create_issue()` / `update_issue()` / `claim_issue()`
- `update_issue_status()` / `update_issue_priority()`
- `add_issue_comment()` / `list_comments()`
- `get_issue_detail()`
- `defer_issue()` / `undefer_issue()`
- `propose_plan()` / `revise_plan()` / `update_plan_progress()`
- `list_servers()` / `get_server_credentials()`
- `create_workflow()` / `trigger_workflow()` / `list_workflow_runs()`
- `set_agent_memory()` / `get_agent_memory()`
- `get_my_recent_actions()`

#### `mcp_tools/mate.py` — Mate 专属

First Mate（大副/审查者）的核心工具：
- `list_pending_plans()` — 待审批计划
- `get_plan_detail()` — 计划详情
- `approve_plan()` / `reject_plan()` — 审批操作
- `list_active_plans_progress()` — 活跃计划进度
- `assign_issue()` — 分配 Issue
- `set_issue_priority()` — 设置优先级
- `get_agent_activities()` — 查看 Agent 活动

#### `mcp_tools/tester.py` — Tester 专属

测试者角色的核心工具：
- `report_bug()` — 提交 Bug
- `request_feature()` — 提交需求
- `verify_issue()` — 验证 Issue
- `reject_fix()` — 退回修复
- `list_my_issues()` — 我的 Issue 列表
- `list_all_issues()` — 全部 Issue 列表
- `add_comment()` — 添加评论

#### `mcp_tools/registrar.py` — Registrar 专属

项目登记角色的核心工具：
- `register_project()` — 登记新项目
- `list_registrations()` — 登记列表
- `get_registration()` — 登记详情
- `update_registration()` — 更新登记
- `mark_scanned()` — 标记已扫描
- `delete_registration()` — 删除登记

---

## 3. 关键设计决策

### 3.1 如何避免循环导入？

**方案**：模块不直接 import 主文件的 `mcp` 实例，而是暴露 `register_tools(mcp_instance)` 函数。

```python
# mcp_tools/agent.py
def register_tools(mcp):
    @mcp.tool()
    @require_role("agent", "admin")
    async def create_issue(...):
        ...
    
    @mcp.tool()
    @require_role("agent", "admin")
    async def update_issue(...):
        ...
```

主文件统一注册：

```python
# mcp_server_unified.py
from mcp_tools import shared, agent, mate, tester, registrar

mcp = FastMCP("project-manager")

shared.register_tools(mcp)
agent.register_tools(mcp)
mate.register_tools(mcp)
tester.register_tools(mcp)
registrar.register_tools(mcp)
```

### 3.2 装饰器如何共享？

**决策**：采用"参数传入"方案，彻底避免循环导入。

主文件定义装饰器后，在注册阶段传入：

```python
# mcp_server_unified.py
import functools

def require_role(*roles):
    ...

def safe_tool(func):
    ...

# 注册时传入
from mcp_tools import agent, mate, tester, registrar, shared

shared.register_tools(mcp, require_role, safe_tool)
agent.register_tools(mcp, require_role, safe_tool)
mate.register_tools(mcp, require_role, safe_tool)
tester.register_tools(mcp, require_role, safe_tool)
registrar.register_tools(mcp, require_role, safe_tool)
```

各模块接收这三个参数，**不在模块内 import 主文件**：

```python
# mcp_tools/agent.py
def register_tools(mcp, require_role, safe_tool):
    @mcp.tool()
    @require_role("agent", "admin")
    @safe_tool
    async def create_issue(...):
        ...
```

### 3.3 旧文件如何迁移？

1. 确认 `mcp_server_unified.py` 中所有工具已经完整（55 个）
2. 把工具按角色拆分到新文件
3. 单元测试：确保每个角色的工具列表与旧文件一致
4. 集成测试：运行完整的 MCP 测试套件
5. 删除旧文件并提交

### 3.4 docker-compose 是否需要修改？

**不需要**。`docker-compose.yml` 已经指向 `mcp_server_unified.py` 的 Streamable HTTP 模式。重构只改变文件内部结构，不改变入口点。

---

## 4. 测试策略

### 4.1 工具数量验证

编写测试确保每个角色的工具数量与重构前一致：

```python
def test_agent_tools_count():
    mcp = FastMCP("test")
    agent.register_tools(mcp, require_role, safe_tool)
    assert len(mcp._tools) == 35  # Agent 应有 35 个工具
```

### 4.2 角色权限验证

确保每个工具都有正确的 `@require_role` 装饰器：

```python
def test_agent_only_tools():
    # create_issue 只有 agent/admin 能调用
    assert "agent" in create_issue._roles
    assert "mate" not in create_issue._roles
```

### 4.3 集成测试

运行已有的测试套件：
- `test_fault_tolerance.py` — 确保 safe_tool 仍然有效
- `test_p1_p2_fixes.py` — 确保工作流工具正常
- 手动测试 MCP 连接

---

## 5. 实施步骤

1. **创建目录结构** — 新建 `mcp_tools/` 包
2. **提取共享工具** — 从 unified.py 提取 `shared.py`
3. **拆分角色模块** — 逐个提取 agent.py, mate.py, tester.py, registrar.py
4. **重构入口文件** — 精简 `mcp_server_unified.py`
5. **添加工具计数测试** — 验证工具完整性
6. **运行全量测试** — 确保 99 个测试全部通过
7. **删除旧文件** — mcp_server.py, mcp_server_mate.py, mcp_server_tester.py, mcp_server_registrar.py
8. **更新 CHANGELOG** — 记录架构变更

---

## 6. 风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 工具遗漏 | 中 | 高 | 编写工具计数对比测试 |
| 循环导入 | 低 | 高 | 使用 `register_tools()` 模式，模块不 import 主文件 |
| 装饰器失效 | 低 | 中 | 测试 safe_tool 和 require_role 功能 |
| docker 构建失败 | 低 | 高 | 保持入口文件路径不变 |

---

## 7. 附录：工具清单

### Agent 工具（35个）
check_connection, get_context, get_my_recent_actions, list_projects, create_project, create_issue, list_issues, update_issue_status, claim_issue, update_issue_priority, update_issue, defer_issue, undefer_issue, add_issue_comment, list_comments, get_issue_detail, propose_plan, list_plans, get_plan_detail, revise_plan, update_plan_progress, list_milestones, create_milestone, list_servers, get_server_credentials, check_notifications, mark_notification_read, list_workflows, create_workflow, trigger_workflow, list_workflow_runs, set_agent_memory, get_agent_memory, notify_role, get_handover_template

### Mate 工具（24个）
check_connection, get_context, list_pending_plans, get_plan_detail, approve_plan, list_active_plans_progress, reject_plan, list_issues, get_issue_detail, assign_issue, set_issue_priority, update_issue_status, add_issue_comment, check_notifications, mark_notification_read, get_agent_activities, notify_role, get_handover_template, list_projects, list_milestones

### Tester 工具（23个）
check_connection, get_context, report_bug, request_feature, verify_issue, reject_fix, list_my_issues, get_issue_detail, list_all_issues, add_comment, check_notifications, mark_notification_read, notify_role, get_handover_template, list_projects, list_milestones

### Registrar 工具（22个）
check_connection, register_project, list_registrations, get_registration, update_registration, mark_scanned, delete_registration, get_context, list_projects, list_milestones, check_notifications, mark_notification_read, notify_role, get_handover_template

> 注：共享工具跨多个角色重复列出。
