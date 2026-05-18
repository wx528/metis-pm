# 集中式白板 + Agent 角色协作

> 优先级: P2（中期规划）
> 状态: 已确认方向
> 日期: 2026-05-18

## 核心决策

**保持轻量，不做分布式。** 深化角色权限和工作流自动化，让 Agent 像团队成员一样使用同一个 PM 白板。

## 方案对比

| | 方案 A：分布式自治 | 方案 B：集中式白板 ✅ |
|---|---|---|
| 架构 | 每个 Agent 本地运行 Node + PM | 一个 PM 服务器，Agent 通过 MCP 访问 |
| 一致性 | 分布式共识（Raft/Paxos），极复杂 | 单数据源，天然一致 |
| 故障 | 无单点，但脑裂/选主复杂 | 单点故障（内网概率低，L1 缓存兜底） |
| 开发成本 | 当前的 5-10 倍 | 在现有基础上演进 |
| 适用规模 | 100+ 节点 | 5-6 台机器绑绑有余 |

**结论：5-6 台机器用分布式是杀鸡用牛刀，集中式白板 + Agent 角色才是正确方向。**

## 当前架构已经具备

| 能力 | 对应 |
|------|------|
| MCP 22 个工具 | Agent 访问 PM 的接口 |
| RBAC（admin/agent） | 角色权限 |
| `AGENT_PASSWORDS` | 每个 Agent 有独立身份 |
| 工作流 + 自动触发 | Agent 自主协作规则 |
| `on_issue_created` / `on_plan_approved` | Agent 钩子 |

## 演进路径

### Phase 9：Agent 角色细化

当前只有 admin / agent 两个角色，细化为：

```python
AGENT_ROLES = {
    "admin":     ["*"],                                    # 全部权限
    "coder":     ["issue:read", "issue:update", "plan:read", "plan:propose"],
    "reviewer":  ["issue:read", "issue:comment", "plan:approve"],
    "tester":    ["issue:read", "issue:create", "issue:update_status"],
    "observer":  ["issue:read", "plan:read"],              # 只读
}
```

### Phase 10：Agent 自主协作

基于工作流的自动化协作，无需分布式：

```
1. Agent A (coder) 完成 Issue → 自动触发工作流
2. 工作流创建 Review Issue → 指派 Agent B (reviewer)
3. Agent B 审批通过 → 自动触发 Agent C (tester) 验证
4. Agent C 验证通过 → Issue 自动关闭
```

### 核心洞察

Agent 不需要"自治节点"，它们需要的是**明确的角色 + 清晰的协作规则**，这正是集中式 PM + 工作流提供的。复制人类 PM 的模式——一个白板，不同角色的人（和 Agent）协同工作。
