# All-Agent 自动化方案：Delegate Agent 设计

## 一、核心思路

当前系统中，人类承担两个角色：

1. **审批者**：Plan 提议后需要人类 approve/reject
2. **决策者**：P0/P1 Issue 创建时通知人类，Agent 关闭 Issue 时通知人类

"全 Agent 化"的本质是：**让一个 Agent 扮演人类的审批/决策角色**，根据可配置的规则自动处理 P1 及以下的任务，只有 P0 仍然需要真正的人类介入。

我称之为 **Delegate Agent**（代理决策者）。

```
当前流程：
  Worker Agent → propose_plan → [人类审批] → approve/reject
  Worker Agent → create P1 issue → [人类收到通知]

目标流程：
  Worker Agent → propose_plan → Delegate Agent 自动审批 → approve/reject
  Worker Agent → create P1 issue → Delegate Agent 自动确认
  Worker Agent → create P0 issue → [人类收到通知] ← 仍然需要人
```

## 二、为什么不是给 Agent admin 权限

直接给某个 Agent admin 角色是最简单的方案，但**不可取**：

| 方案 | 问题 |
|------|------|
| 给 Agent admin 角色 | 无权限边界，Agent 可以删库、改密码、操作所有资源 |
| Delegate Agent + 权限边界 | 只授予特定操作的权限，所有行为可审计 |

Delegate 的设计原则：

- **最小权限**：只能审批 Plan、确认 Issue，不能删除资源、不能修改其他 Agent 的数据
- **规则透明**：审批逻辑由 .env 配置驱动，不是黑箱
- **行为可审计**：所有 Delegate 操作在 activity_log 中标记为 `delegate` 角色，与人类操作区分
- **人类兜底**：P0 永远不自动处理，人类随时可以覆盖 Delegate 的决定

## 三、角色体系重新设计

### 3.1 当前角色

```
admin  → 全部权限（人类）
agent  → 受限权限（AI Agent）
```

### 3.2 新增角色

```
admin    → 全部权限（人类）
delegate → 代理人类审批/决策（AI Agent，权限介于 admin 和 agent 之间）
agent    → 受限权限（AI Agent，只能创建和更新，不能审批）
```

### 3.3 权限矩阵

| 操作 | admin | delegate | agent |
|------|-------|----------|-------|
| 创建 Issue | ✅ | ✅ | ✅ |
| 更新 Issue 状态 | ✅ | ✅ | ✅ |
| 关闭 Issue | ✅ | ✅ | ⚠️ 通知 admin |
| 创建 P0/P1 Issue | ✅ | ✅ | ⚠️ 通知 admin/delegate |
| 审批 Plan (approve) | ✅ | ✅ (规则内) | ❌ |
| 拒绝 Plan (reject) | ✅ | ✅ (规则内) | ❌ |
| 删除资源 | ✅ | ❌ | ❌ |
| 修改其他 Agent 数据 | ✅ | ❌ | ❌ |
| 查看服务器凭据明文 | ✅ | ❌ | ❌ |
| 修改系统设置 | ✅ | ❌ | ❌ |

## 四、.env 配置设计

```env
# Delegate Agent 配置
# 格式: agent_name:password:threshold
# threshold = 该 delegate 自动处理的最高优先级
#   P0 = 不自动处理任何（等同于关闭 delegate）
#   P1 = 自动处理 P1/P2/P3，P0 仍需人类
#   P2 = 自动处理 P2/P3，P0/P1 仍需人类
#   P3 = 只自动处理 P3，P0/P1/P2 仍需人类
#   ALL = 自动处理所有优先级（危险，不推荐）
DELEGATE_AGENTS=delegate:delegate-2026:P1

# Delegate 自动审批 Plan 的规则
# auto_approve_plans = true 时，delegate 自动审批 Plan
# auto_approve_plans = false 时，delegate 只自动确认 Issue，Plan 仍需人类
AUTO_APPROVE_PLANS=true

# Delegate 审批 Plan 时的额外规则
# max_plan_items = 单个 Plan 的最大 item 数，超过则不自动审批（防止 Agent 提交巨型 Plan）
MAX_PLAN_ITEMS_AUTO_APPROVE=20

# Delegate 操作后是否通知人类
# always = 每次操作都通知
# summary = 每天汇总通知
# never = 不通知（不推荐）
DELEGATE_NOTIFY_MODE=summary
```

### 4.1 配置示例

**激进模式**（大部分自动化，P0 才需要人）：
```env
DELEGATE_AGENTS=delegate:delegate-2026:P1
AUTO_APPROVE_PLANS=true
MAX_PLAN_ITEMS_AUTO_APPROVE=20
DELEGATE_NOTIFY_MODE=summary
```

**保守模式**（只自动处理 P2/P3，P0/P1 需要人，Plan 需要人）：
```env
DELEGATE_AGENTS=delegate:delegate-2026:P2
AUTO_APPROVE_PLANS=false
MAX_PLAN_ITEMS_AUTO_APPROVE=10
DELEGATE_NOTIFY_MODE=always
```

**关闭 Delegate**（回到纯人类审批）：
```env
DELEGATE_AGENTS=
```

## 五、系统变更清单

### 5.1 后端变更

#### settings.py — 新增配置解析

```python
class Settings(BaseSettings):
    # ... 现有字段 ...
    DELEGATE_AGENTS: str = ""
    AUTO_APPROVE_PLANS: bool = True
    MAX_PLAN_ITEMS_AUTO_APPROVE: int = 20
    DELEGATE_NOTIFY_MODE: str = "summary"

    @property
    def delegate_map(self) -> dict[str, dict]:
        result = {}
        if not self.DELEGATE_AGENTS:
            return result
        for entry in self.DELEGATE_AGENTS.split(","):
            parts = entry.strip().split(":")
            if len(parts) >= 3:
                name, pwd, threshold = parts[0], parts[1], parts[2]
                result[name] = {"password": pwd, "threshold": threshold}
        return result

    def resolve_identity(self, password: str) -> tuple[str, str] | None:
        if password == self.ADMIN_PASSWORD:
            return ("admin", "admin")
        for name, info in self.delegate_map.items():
            if password == info["password"]:
                return (name, "delegate")
        for name, pwd in self.agent_password_map.items():
            if password == pwd:
                return (name, "agent")
        return None
```

#### auth.py — 新增 delegate 角色支持

```python
async def get_delegate_or_admin_user(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") in ("admin", "delegate"):
        return user
    raise HTTPException(status_code=403, detail="Delegate or admin access required")
```

#### plans.py — Plan 审批权限开放给 delegate

```python
@router.post("/{plan_id}/approve", response_model=PlanRead)
async def approve_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_delegate_or_admin_user),  # 改为允许 delegate
):
    # ... 现有逻辑 ...
    plan.approved_by = user["sub"]
    # 如果是 delegate 审批，记录额外标记
    if user["role"] == "delegate":
        plan.approved_by = f"delegate:{user['sub']}"
```

#### issues.py — Agent 创建 Issue 时通知 delegate 而非 admin

```python
# 当前：Agent 创建 P0/P1 issue → 通知 admin
# 改为：Agent 创建 P0 issue → 通知 admin
#        Agent 创建 P1 issue → 通知 delegate（如果配置了）
#        Agent 创建 P2/P3 issue → 无需通知

if user["role"] == "agent" and issue.priority == IssuePriority.P0:
    await create_notification(
        db, recipient="admin",
        type=NotificationType.TASK_CREATED,
        title=f"P0 Issue: {issue.title}",
        ...
    )
elif user["role"] == "agent" and issue.priority in (IssuePriority.P1,):
    delegates = settings.delegate_map.keys()
    for delegate_name in delegates:
        await create_notification(
            db, recipient=delegate_name,
            type=NotificationType.TASK_CREATED,
            title=f"P1 Issue 需确认: {issue.title}",
            ...
        )
```

### 5.2 MCP Server 变更

#### 新增工具：approve_plan / reject_plan

当前 MCP 没有审批工具，这是自动化的前提。

```python
@mcp.tool()
async def approve_plan(plan_id: int) -> str:
    """审批通过一个待审批的 Plan。仅 delegate 和 admin 身份可用。"""
    headers = await get_headers()
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_BASE}/plans/{plan_id}/approve", headers=headers)
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        data = resp.json()
        return f"Plan #{data['id']} approved: {data['title']} (status={data['status']})"


@mcp.tool()
async def reject_plan(plan_id: int, reason: str = "") -> str:
    """拒绝一个待审批的 Plan，可附上拒绝原因。仅 delegate 和 admin 身份可用。"""
    headers = await get_headers()
    params = {}
    if reason:
        params["reason"] = reason
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_BASE}/plans/{plan_id}/reject", params=params, headers=headers)
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        data = resp.json()
        return f"Plan #{data['id']} rejected: {data['title']} (reason={data.get('reject_reason', 'N/A')})"
```

#### 新增工具：get_dashboard（Agent 状态感知）

Delegate 需要快速了解系统状态才能做决策。

```python
@mcp.tool()
async def get_dashboard() -> str:
    """获取系统全局状态摘要：待审批 Plan、各优先级 Issue 数量、最近活动"""
    headers = await get_headers()
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/dashboard", headers=headers)
        if resp.status_code >= 400:
            return f"Error: {resp.status_code} - {resp.text}"
        data = resp.json()
        lines = ["=== 系统状态摘要 ==="]
        lines.append(f"项目: {data.get('project_count', 0)}")
        lines.append(f"Issue: {data.get('issue_count', 0)} (P0={data.get('p0_count',0)}, P1={data.get('p1_count',0)})")
        lines.append(f"待审批 Plan: {data.get('pending_plans', 0)}")
        lines.append(f"待处理通知: {data.get('unread_notifications', 0)}")
        return "\n".join(lines)
```

### 5.3 Delegate Agent 的运行方式

Delegate 不是一直在线的，有两种运行模式：

#### 模式 A：被动触发（推荐）

Delegate 作为一个普通 Agent，通过 MCP 连接。当系统有待审批项时：
1. 系统创建通知 → 通知 recipient 为 delegate
2. Delegate 的宿主环境（如 Hermes）定期调用 `check_notifications`
3. Delegate 看到通知后，调用 `approve_plan` 或 `reject_plan`

**优点**：不需要额外进程，复用现有 MCP 基础设施
**缺点**：依赖 Delegate Agent 的宿主环境主动轮询

#### 模式 B：主动轮询（独立进程）

Delegate 作为独立后台进程运行：

```python
# delegate_daemon.py
async def delegate_loop():
    while True:
        # 1. 检查待审批 Plan
        plans = await list_pending_plans()
        for plan in plans:
            decision = await evaluate_plan(plan)
            if decision.approve:
                await approve_plan(plan.id)
            else:
                await reject_plan(plan.id, decision.reason)

        # 2. 检查需要确认的 Issue
        issues = await list_unconfirmed_issues()
        for issue in issues:
            await confirm_issue(issue.id)

        await asyncio.sleep(60)  # 每分钟检查一次
```

**优点**：完全自动化，无需人工触发
**缺点**：需要额外进程，需要 LLM 调用成本

#### 模式 C：混合模式（推荐长期方案）

- 简单规则（优先级阈值、Plan item 数量）→ 后台进程自动处理
- 复杂决策（Plan 内容评估、reject 原因生成）→ 调用 LLM，由 Delegate Agent 处理

```python
async def evaluate_plan(plan) -> Decision:
    # 规则层：快速判断
    if plan.item_count > settings.MAX_PLAN_ITEMS_AUTO_APPROVE:
        return Decision(approve=False, reason="Plan items 超过自动审批上限")

    # LLM 层：内容评估（可选）
    if settings.DELEGATE_USE_LLM:
        return await llm_evaluate(plan)

    # 默认：规则内自动通过
    return Decision(approve=True)
```

## 六、Delegate 的决策逻辑

### 6.1 Plan 审批规则

```
输入：Plan（title, description, item_count, proposed_by）

规则链（按顺序执行，命中即停止）：
1. item_count > MAX_PLAN_ITEMS_AUTO_APPROVE → reject（"Plan 规模超过自动审批上限"）
2. proposed_by 的历史 reject 率 > 50% → reject（"近期提案通过率过低，建议人工审核"）
3. AUTO_APPROVE_PLANS = true → approve
4. AUTO_APPROVE_PLANS = false → 不处理，等待人类

审批结果：
- approve → Plan 状态变为 active，通知提议者
- reject → Plan 状态变为 abandoned，附上 reject_reason，通知提议者
- 跳过 → Plan 保持 pending_approval，等待人类
```

### 6.2 Issue 确认规则

```
输入：Issue（priority, source, created_by）

规则链：
1. priority = P0 → 不自动处理，通知 admin
2. priority 在 delegate 阈值内 → 自动确认（标记为 reviewed）
3. priority 超出阈值 → 不处理，通知 admin

确认动作：
- 标记 Issue 为已审阅（新增 reviewed_by 字段）
- 如果是 bug 类型且 P1，自动分配 milestone
```

### 6.3 人类覆盖机制

Delegate 的任何决定都可以被人类覆盖：

```
人类操作：
1. 在 Web UI 中看到 Delegate 审批的 Plan → 可以点击"撤回审批"
2. 在 Web UI 中看到 Delegate 确认的 Issue → 可以重新打开
3. 在 .env 中调整 DELEGATE_AGENTS 的阈值 → 实时生效
4. 在 .env 中清空 DELEGATE_AGENTS → 立即关闭所有 Delegate
```

## 七、安全考量

### 7.1 防止 Delegate 失控

| 风险 | 应对 |
|------|------|
| Delegate 自动审批了错误的 Plan | MAX_PLAN_ITEMS_AUTO_APPROVE 限制规模；人类可撤回 |
| Delegate 和 Worker Agent 串通 | Delegate 和 Worker 不能是同一个身份；Delegate 的审批逻辑是规则驱动的，不受 Worker 影响 |
| Delegate 密码泄露 | 与其他 Agent 密码一样，通过 .env 管理；可随时更换 |
| Delegate 无限循环审批 | 每个 Plan 只能被审批一次；Delegate 审批后 Plan 状态变为 active，不会重复审批 |

### 7.2 审计追踪

所有 Delegate 操作在 activity_log 中标记为 `delegate:delegate-name`：

```
actor: "delegate:delegate"  （而非 "admin" 或 "agent:hermes-agent"）
action: "approved"
new_value: {"status": "active", "approved_by": "delegate:delegate"}
```

这样在 Web UI 的活动流中，可以清晰区分：
- 人类审批 → `admin approved`
- Delegate 自动审批 → `delegate:delegate approved`
- Agent 提议 → `hermes-agent proposed`

## 八、实施路线

### Phase 1：基础设施（1-2 天）

- [ ] settings.py 新增 DELEGATE_AGENTS 配置解析
- [ ] auth.py 新增 delegate 角色
- [ ] resolve_identity 支持 delegate
- [ ] .env 新增 DELEGATE_AGENTS 配置

### Phase 2：MCP 工具补全（1 天）

- [ ] mcp_server.py 新增 `approve_plan` 工具
- [ ] mcp_server.py 新增 `reject_plan` 工具
- [ ] mcp_server.py 新增 `get_dashboard` 工具
- [ ] mcp_server.py 的 `list_plans` 返回 `reject_reason` 和 `item_count`

### Phase 3：权限与通知（1 天）

- [ ] plans.py 审批接口开放给 delegate 角色
- [ ] issues.py 通知逻辑区分 admin 和 delegate
- [ ] activity_log 中标记 delegate 操作
- [ ] 通知系统支持 recipient=delegate_name

### Phase 4：Delegate 运行时（2-3 天）

- [ ] 实现 delegate_daemon.py（模式 B）
- [ ] 实现规则引擎（Plan 审批规则 + Issue 确认规则）
- [ ] Docker Compose 新增 delegate 服务
- [ ] 人类覆盖机制（Web UI 撤回审批）

### Phase 5：LLM 增强（可选）

- [ ] Delegate 接入 LLM 进行 Plan 内容评估
- [ ] reject 时自动生成修改建议
- [ ] 复杂 Issue 自动分类和分配

## 九、Docker Compose 变更

```yaml
delegate:
  build: ./backend
  container_name: pm-delegate
  env_file:
    - .env
  environment:
    - PM_API_URL=http://backend:8000/api/v1
    - PM_AGENT_PASSWORD=${DELEGATE_PASSWORD:-delegate-2026}
  depends_on:
    backend:
      condition: service_healthy
  restart: on-failure
  entrypoint: ["python", "delegate_daemon.py"]
```

## 十、与现有系统的兼容性

- **不配置 DELEGATE_AGENTS**：系统行为与现在完全一致，无任何变化
- **配置了 DELEGATE_AGENTS**：Delegate 自动处理阈值内的任务，人类仍可通过 Web UI 操作
- **已有 Agent 不受影响**：trae、hermes-agent 等继续以 agent 角色工作
- **Web UI 不受影响**：人类仍然可以通过 Web UI 审批 Plan、管理 Issue
- **Delegate 的决定可以被人类覆盖**：人类始终是最终决策者
