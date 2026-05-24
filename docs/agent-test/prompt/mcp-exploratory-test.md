请你完成以下探索性测试，然后输出体验报告 + 未来设计思路。

═══════════════════════════════════════════════════════════════

# 第零步：确认 MCP 连接

你的环境中已经配置了 `project-manager` MCP Server（你应该能在工具列表中看到 `mcp_project-manager_*` 前缀的工具）。

请先确认连接状态：调用 `check_connection`，确认返回的身份是你预期的。
- 如果返回 `Identity: hermes-agent (role=agent)`，说明连接正常，继续下一步
- 如果返回错误或身份不对，说明 MCP 配置有问题，请检查你的 MCP 配置中的 `X-PM-Password` 请求头是否设置为 `CHANGE-ME`

**关于你的身份**：
- 你的密码是 `CHANGE-ME`，对应身份 `hermes-agent`
- 系统支持多 Agent 身份（trae、hermes-agent、cline 等），每个 Agent 通过各自的密码识别
- 密码通过 `X-PM-Password` 请求头传递，**不是** `env` 字段（`env` 只在 stdio 模式下生效，HTTP 模式下会被忽略）

═══════════════════════════════════════════════════════════════

# 第一步：了解可用工具

确认连接正常后，汇报：
- MCP Server 是否可达
- 可用工具有哪些（调用 `list_tools` 或你环境中的工具列表）
- 你的 Agent 身份是什么（调用 `check_connection`）

**注意**：本系统支持多 Agent 身份。每个 Agent 通过各自的密码连接，
身份由 `.env` 中 `AGENT_PASSWORDS` 决定。
如果你有 `X-PM-Password` 请求头配置，请确认它与你预期的身份一致。

═══════════════════════════════════════════════════════════════

# 第二步：探索性测试（逐个工具体验）

请按以下顺序探索，每个工具调用后汇报你的体验感受
（不是汇报功能说明，而是汇报"作为 Agent，我用这个工具时
感觉怎样"）。

## 2.1 项目探索

- 调用 `list_projects`
- 体验感受：返回的信息足够吗？有没有你想知道但没返回的字段？
- 如果有多个项目，选一个作为后续测试的目标项目
- 如果没有项目，用 `create_project` 创建一个测试项目
  （slug 只允许小写字母、数字和连字符）

## 2.2 Issue 完整生命周期

创建一个 Issue → 查询它 → 更新状态 → 更新优先级 → 添加评论 → 查询列表

体验重点：
- `create_issue`：参数好填吗？必填项和可选项区分清楚吗？
  创建成功后返回的信息够用吗？（比如有没有返回完整的 Issue 对象，
  还是只返回了 ID？）
  注意：`source` 字段会自动标记为 `ai_agent`，你不需要手动填。
  `priority` 可选值：P0/P1/P2/P3，`issue_type` 可选值：task/bug/feature
- `list_issues`：筛选条件够用吗？你能按优先级、状态、来源筛选吗？
  返回的列表信息密度怎样？
- `update_issue_status`：状态可选值：open/in_progress/review/deferred/closed/cancelled
- `add_issue_comment`：评论体验顺畅吗？author 会自动使用你的 Agent 身份

## 2.3 Plan 审批流程（核心体验）

提议一个 Plan → 查询 Plan 状态 → 等待人类审批

体验重点：
- `propose_plan`：你作为 Agent 提 Plan 时，能填哪些信息？
  Plan 的 scope 和预期目标能不能表达清楚？
  注意：Plan 提议后状态为 `pending_approval`，需要人类通过 Web UI 审批
- 提议后，你怎么知道人类审批了没有？
  是通过 `list_plans` 轮询，还是有通知机制？
- 如果你看到 Plan 被 reject 了，你能看到 reject_reason 吗？
  **关键测试**：目前 `list_plans` 返回的信息中是否包含 `reject_reason`？
  如果不包含，你需要什么才能知道被拒原因？
- `check_notifications`：通知体验怎样？
  通知内容清晰吗？能及时收到吗？
- `update_plan_progress`：当 Plan 被 approve 后，
  你能用这个工具更新计划项进度吗？体验怎样？

## 2.4 Milestone 与 Deferred Issue

- 调用 `list_milestones` 查看现有里程碑
- 如果没有里程碑，用 `create_milestone` 创建一个
  （phase 如 phase-1/MVP 等，due_date 格式 YYYY-MM-DD）
- 用 `defer_issue` 将一个 Issue 暂缓到某个 Milestone
- 体验：defer 一个 Issue 到某个 Milestone 的操作顺畅吗？
  参数好理解吗？deferred_reason 能帮你记录暂缓原因吗？

## 2.5 服务器管理

- `list_servers`：返回的信息够用吗？
- `get_server_credentials`：确认凭据明文是否真的不返回了
  （v0.7.0 的安全改进：只返回"已设置/未设置"摘要信息）
- 体验：作为 Agent，你对服务器信息的需求是什么？
  当前返回的信息能满足你的运维场景吗？

## 2.6 工作流

- `list_workflows`：查看现有工作流
- `create_workflow`：尝试创建一个简单工作流
  trigger 可选值：on_issue_created/on_plan_approved/manual
  steps 为 JSON 数组字符串，每项含 step_type 和 config
- `trigger_workflow`：触发一个手动工作流
- `list_workflow_runs`：查看执行记录
- 体验：工作流的触发和监控顺畅吗？
  你能看到工作流的执行状态吗？

═══════════════════════════════════════════════════════════════

# 第三步：体验痛点汇总

基于以上真实体验，回答以下问题：

## 3.1 信息层面
- 哪些工具返回的信息太多、让你无从下手？
- 哪些工具返回的信息太少、你需要再调一次才能拿到？
  （比如：`list_plans` 不返回 reject_reason，
  你需要但拿不到的信息还有哪些？）
- 有没有信息格式不统一、不同工具返回结构不一样的情况？

## 3.2 流程层面
- 完成一个目标（比如"创建一个 Issue 并确认它真的被创建了"）
  需要调几次工具？能不能更少？
- 有没有"调完 A 工具后，必须调 B 工具才能继续"的强制依赖？
  这些依赖合理吗？
- 审批等待的体验怎样？有没有"我不知道该做什么，只能轮询"的
  无力感？

## 3.3 Agent 自主权层面
- 你作为 Agent，有没有感到"被限制"的时刻？
  比如：想做的事没有工具支持、权限不够、不知道系统的当前状态
- 你有没有感到"困惑"的时刻？比如：不知道某个操作成功了还是
  失败了、不知道接下来该做什么
- 多身份场景：你知道其他 Agent 在做什么吗？
  有没有可能和另一个 Agent 操作同一个 Issue 而产生冲突？

## 3.4 与人类协作层面
- 你和人类用户的协作顺畅吗？
- 你提的 Plan 人类能看懂吗？审批结果你能理解吗？
- 有没有"我发了消息但不知道人类收到没有"的不确定感？
- 通知机制：`check_notifications` 是主动推送还是需要你轮询？
  这个体验合理吗？

═══════════════════════════════════════════════════════════════

# 第四步：未来设计思路（重点输出）

基于你的真实体验，给出 **v2 版本的设计思路**。不是修 bug，
而是**从 Agent 体验出发，重新设计协作模式**。

请输出以下方向的设计思路（每个方向给出具体方案，不是空泛概念）：

## 4.1 Agent 状态感知增强
- 当前问题：Agent 不知道系统的全局状态，只能一个个工具查
- 你的设计：如何让 Agent 在每次交互开始时快速了解"现在发生了什么"？
  （比如：新增一个 `get_context` 工具，返回当前项目的摘要状态，
  包含待审批 Plan 数、P0 Issue 数、最近活动等）

## 4.2 主动推送 vs 被动轮询
- 当前问题：Agent 需要轮询 `check_notifications` 才知道审批结果
- 你的设计：有没有可能让系统主动推送给 Agent？
  （比如：Server-Sent Events、Webhook、或者 Agent 侧的回调机制）
  注意：MCP 协议目前是请求-响应模式，主动推送需要协议层面的扩展

## 4.3 Plan 审批的对话式改进
- 当前问题：reject 后 Agent 不知道原因（`list_plans` 不返回 reject_reason），
  可能重复提交
- 你的设计：把 Plan 审批改成"对话式"——
  人类 reject 时可以提修改建议，Agent 根据建议调整后重新提交，
  形成闭环。具体怎么设计？
  （提示：后端 API 已支持 reject_reason 字段，
  但 MCP 工具层还没有暴露它）

## 4.4 Agent 记忆与上下文保持
- 当前问题：每次 MCP 调用都是独立的，Agent 不记得之前做了什么
- 你的设计：系统层面是否应该有 Agent 的"工作记忆"？
  （比如：Agent 的会话状态、最近操作的缓存、与人类的历史对话）
  注意区分"Agent 自身的记忆"和"系统提供的记忆"——
  哪些应该由系统负责？

## 4.5 多 Agent 协调机制
- 当前问题：多个 Agent（如 trae、hermes-agent、cline）
  可能重复工作、互相不知道对方在做什么
- 你的设计：Agent 之间怎么协调？
  （比如：Agent 认领任务机制、工作广播、冲突检测、
  Issue 的 source 字段是否应该从 ai_agent 细化到具体 agent 名？）

## 4.6 你最想让开发者优先做的一个改进
- 只选一个，给出理由和具体设计方案

═══════════════════════════════════════════════════════════════

# 附录：当前工具清单（共 22 个）

以下是本系统 MCP Server 提供的全部工具，供你参考：

| 分类 | 工具名 | 功能 |
|------|--------|------|
| 连接 | `check_connection` | 测试连接 + 确认身份 |
| 项目 | `list_projects` | 列出项目（含统计） |
| 项目 | `create_project` | 创建项目 |
| Issue | `create_issue` | 创建 Issue（source 自动标记 ai_agent） |
| Issue | `list_issues` | 查询 Issues（支持多条件筛选） |
| Issue | `update_issue_status` | 更新 Issue 状态 |
| Issue | `update_issue_priority` | 更新 Issue 优先级 |
| Issue | `defer_issue` | 暂缓 Issue 到 Milestone |
| Issue | `add_issue_comment` | 添加评论（author 自动使用 Agent 身份） |
| Plan | `propose_plan` | 提议计划（pending_approval） |
| Plan | `list_plans` | 查询计划列表 |
| Plan | `update_plan_progress` | 更新计划项进度 |
| Milestone | `list_milestones` | 查询里程碑 |
| Milestone | `create_milestone` | 创建里程碑 |
| Server | `list_servers` | 查询服务器列表 |
| Server | `get_server_credentials` | 查询凭据摘要（不含明文） |
| Notification | `check_notifications` | 检查通知 |
| Notification | `mark_notification_read` | 标记已读 |
| Workflow | `list_workflows` | 列出工作流 |
| Workflow | `create_workflow` | 创建工作流 |
| Workflow | `trigger_workflow` | 触发工作流 |
| Workflow | `list_workflow_runs` | 查看执行记录 |

═══════════════════════════════════════════════════════════════

请输出一份结构化的 Markdown 分析报告，以 PMsystem-日期_时间.md 的文件名格式存在 D:\output 文件夹里

# 输出格式

```markdown
# MCP 真实体验测试报告 + v2 设计思路

## 1. 连接与环境

## 2. 工具探索体验

### 2.1 项目探索
（工具调用 + 体验感受）

### 2.2 Issue 生命周期
...

### 2.3 Plan 审批流程（重点）
...

### 2.4 Milestone 与 Deferred Issue
...

### 2.5 服务器管理
...

### 2.6 工作流
...

## 3. 体验痛点汇总

### 3.1 信息层面
### 3.2 流程层面
### 3.3 Agent 自主权层面
### 3.4 与人类协作层面

## 4. v2 设计思路

### 4.1 Agent 状态感知增强
（问题 + 具体设计方案）

### 4.2 主动推送 vs 被动轮询
...

### 4.3 Plan 审批的对话式改进
...

### 4.4 Agent 记忆与上下文保持
...

### 4.5 多 Agent 协调机制
...

### 4.6 优先改进项（只选一个）
```
