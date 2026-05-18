# Project Manager System — 项目分析报告

> 分析日期：2026-05-18
> 分析范围：项目自身代码 + 20+ 同类开源项目调研
> 结论：本项目定位独特（人机协作 + MCP 原生），建议保持核心优势、补齐短板、拥抱 AI 趋势

---

## 一、项目现状分析

### 1.1 项目定位

本项目是一个**人机协作项目管理系统**，核心定位非常清晰：

- **目标用户**：个人开发者 + AI Coding Agent（非团队协作场景）
- **核心场景**：用户与 Agent 共同管理项目，Agent 通过 MCP 协议录入 issues、提议计划、更新进展
- **技术栈**：FastAPI + SQLite + React 19 + TypeScript + Ant Design 6 + MCP

### 1.2 现有功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| Issue 管理 | 完整 | 含类型、优先级、来源标记、暂缓、评论 |
| Milestone 阶段 | 完整 | 分期管理，issue 统计 |
| Plan 计划审批 | 完整 | 审批流：pending_approval → active/abandoned |
| PlanItem 清单 | 完整 | checklist 进度追踪 |
| Server 服务器 | 完整 | 凭据加密存储，独立接口获取 |
| Workflow 工作流 | 完整 | trigger → execute → wait_approval → resume |
| 通知系统 | 完整 | 未读通知、标记已读 |
| 活动日志 | 完整 | 全实体变更追踪 |
| MCP Server | 完整 | 24+ 工具，Agent 原生调用 |
| 多项目支持 | 完整 | Phase 4 迁移完成 |
| 前端页面 | 完整 | Dashboard、Board、Issues、Plans、Servers 等 |

### 1.3 项目亮点

1. **MCP 原生集成**：核心差异化优势。Agent 不需要写 HTTP 请求，直接调用 MCP 工具
2. **人机协作设计**：source 字段区分 user/ai_agent/collaborative，审批流设计合理
3. **安全考量**：凭据隔离、JWT 认证、LIKE 转义防注入、Fernet 加密
4. **工作流引擎**：支持 trigger、wait_approval、resume、retry、指数退避
5. **文档完善**：设计文档、部署指南、MCP 配置说明、issue 追踪（done/later）

### 1.4 潜在改进空间

1. **缺少看板视图**：虽然有 Board 页面，但 WeKan/Focalboard 的拖拽看板体验更成熟
2. **缺少甘特图**：milestone 管理没有可视化时间线
3. **AI 能力有限**：目前只是 Agent 录入数据，没有 AI 分析、预测、建议
4. **缺少知识库**：没有文档/wiki 功能，项目知识分散
5. **移动端适配**：Ant Design 6 支持响应式，但可能没有专门优化
6. **缺少集成**：没有 Git 集成、没有 CI/CD 联动、没有 Webhook

---

## 二、同类优秀项目调研

### 2.1 综合型项目管理（Jira/Linear 替代）

| 项目 | Stars | 核心特点 | AI/MCP 支持 |
|------|-------|----------|-------------|
| **Plane.so** | 46k+ | 最热门的开源 Jira/Linear 替代，支持 self-hosted，现代 UI | AI-native，2026.3 推出 Plane AI，支持 agent workflow |
| **Tegon** | 3k+ | Dev-first 替代 Linear/Jira，MIT 协议 | Tegon Actions 自动化框架，支持 agent 分配任务 |
| **OpenProject** | 8k+ | 企业级，功能最全，合规性强 | 2025 投资 AI 集成，2026.3 推出 MCP Server（Enterprise） |
| **Taiga** | 6k+ | 敏捷导向，Scrum + Kanban，AngularJS | 无原生 AI，社区驱动 |
| **Redmine** | 5k+ | 老牌 Ruby 项目，插件生态丰富 | 无原生 AI，靠插件 |
| **Leantime** | 4k+ | 专为 ADHD/神经多样性设计，目标导向 | 无原生 AI，但有 AI 项目管理文章 |
| **Focalboard** | 8k+ | Mattermost 出品，Trello/Notion 替代 | 无 AI，维护模式 |
| **WeKan** | 19k+ | 最像 Trello 的开源 Kanban | 有 MCP server 集成（社区） |
| **Kanboard** | 8k+ | 极简 Kanban，PHP | 有 MCP Plugin（ChristianJStarr/kanboard-mcp） |
| **Vikunja** | 3k+ | Todoist/Trello 替代，多视图 | 有 Vikunja MCP Server（社区） |

### 2.2 Git 托管 + 项目管理一体化

| 项目 | Stars | 核心特点 | AI/MCP 支持 |
|------|-------|----------|-------------|
| **OneDev** | 5k+ | Git + CI/CD + Kanban + Packages，MIT 协议 | 原生 MCP Server，AI 辅助代码解释、构建失败调查 |
| **Gitea** | 46k+ | 轻量 GitHub 替代，Gitea Actions CI/CD | Gitea MCP Server（官方教程），AI Code Agent Feature Request |
| **Forgejo** | 5k+ | Gitea 分支，完全开源 | 有 forgejo-mcp（社区），但官方对 AI 谨慎 |

### 2.3 知识库/文档

| 项目 | Stars | 核心特点 | AI/MCP 支持 |
|------|-------|----------|-------------|
| **Docmost** | 5k+ | Notion/Confluence 替代，协作 wiki | 无原生 AI，但社区讨论多 |
| **Outline** | 15k+ | 团队知识库，React + Node.js | 无原生 AI，但可集成 |
| **AppFlowy** | 30k+ | Notion 替代，离线优先，AI 模型选择 | AI 协作工作区，支持本地模型 |

### 2.4 无代码/低代码平台

| 项目 | Stars | 核心特点 | AI/MCP 支持 |
|------|-------|----------|-------------|
| **NocoBase** | 12k+ | AI + 无代码平台，可构建 CRM/项目管理 | AI 驱动，agent 协作构建 |
| **Baserow** | 2k+ | Airtable 替代，AI 功能 | 2025 成为"all-in-one AI-powered no-code platform" |
| **Budibase** | 22k+ | 内部工具构建，AI agent + 工作流 | AI-powered workflow toolkit |

### 2.5 AI 工作流/Agent 编排

| 项目 | Stars | 核心特点 | 项目管理集成 |
|------|-------|----------|--------------|
| **Dify** | 85k+ | 可视化 Agent + Workflow + RAG，生产级 | 通用平台，需自定义集成 |
| **Flowise** | 35k+ | 可视化 AI Agent 构建，LangChain 基础 | 通用平台，需自定义集成 |
| **Langflow** | 45k+ | 低代码 AI Agent + MCP Server 构建 | 通用平台，需自定义集成 |
| **CrewAI** | 25k+ | 多 Agent 编排，角色扮演工作流 | 通用框架，需自定义集成 |
| **n8n** | 65k+ | 工作流自动化，400+ 集成，AI Agent 节点 | 通用平台，需自定义集成 |

---

## 三、关键发现与趋势

### 3.1 2025-2026 关键趋势

1. **AI-native 成为标配**：Plane.so、Linear 都在推 AI Agent 工作流，不再只是辅助
2. **MCP 成为标准接口**：OneDev、Gitea、Kanboard、Vikunja 都在加 MCP Server
3. **Self-hosted AI**：Plane AI 2026.3 进入 self-hosted，OpenProject 2026.3 推出 MCP Server
4. **Issue Tracking 正在死亡**：Linear 2026.3 宣布 "Issue tracking is dead"，转向 Agent workflow

### 3.2 本项目 vs 竞品对比

| 维度 | 本项目 | Plane.so | Tegon | OneDev | OpenProject |
|------|--------|----------|-------|--------|-------------|
| **定位** | 人机协作（个人+Agent） | 团队+Agent | Dev-first | Git+DevOps | 企业级 |
| **MCP** | 原生（24+ 工具） | 暂无 | Actions | 原生 | Enterprise |
| **Self-hosted** | 极简（SQLite） | 复杂（PostgreSQL） | 支持 | 支持 | 支持 |
| **工作流引擎** | 轻量（审批+retry） | 暂无 | Actions | CI/CD | 有限 |
| **Git 集成** | 无 | 有限 | 有限 | 原生 | 插件 |
| **知识库** | 无 | Pages | 无 | 无 | 有限 |
| **看板** | 基础 | 完整 | 完整 | 完整 | 完整 |
| **移动端** | 响应式 | App | 响应式 | 响应式 | 响应式 |
| **社区规模** | 个人项目 | 46k stars | 3k stars | 5k stars | 8k stars |

---

## 四、可借鉴的具体方向

### 4.1 短期可借鉴（1-2 周实现）

#### A. Plane.so 的 AI 工作流设计

- **借鉴点**：Plane AI 的 "Structure work from a prompt" —— 用自然语言创建项目结构
- **应用场景**：在 MCP 里加一个 `create_project_from_prompt` 工具，Agent 描述需求，自动创建 milestone + issues + plan
- **实现难度**：低（复用现有模型，加一个新 MCP tool）

#### B. Tegon Actions 的自动化框架

- **借鉴点**：Tegon Actions 用代码定义自动化规则（类似 GitHub Actions）
- **应用场景**：把现有 Workflow 引擎扩展为 "Action"，支持 YAML/JSON 定义，trigger 更丰富
- **实现难度**：中（需要设计 DSL）

#### C. Kanboard MCP Plugin 的自然语言控制

- **借鉴点**：ChristianJStarr/kanboard-mcp 让 AI 用自然语言操作看板
- **应用场景**：优化 MCP tool 描述，让 Agent 更自然地理解 "把 issue #3 移到 review"
- **实现难度**：低（改 tool description + 加 alias）

### 4.2 中期可借鉴（1-2 月实现）

#### D. OneDev 的 Git + PM 一体化

- **借鉴点**：OneDev 把 Git 托管、CI/CD、Kanban、Issue 跟踪全整合
- **应用场景**：加 Git 集成（webhook 接收 commit、PR、branch 事件，自动关联 issue）
- **实现难度**：中（需要 webhook 接收 + 解析 + 关联逻辑）
- **价值**：Agent 提交代码后自动更新 issue 状态

#### E. AppFlowy/Docmost 的知识库

- **借鉴点**：项目文档、需求文档、技术方案统一管理
- **应用场景**：加 Wiki/Pages 模块，支持 Markdown，与 issue/plan 关联
- **实现难度**：中（新模型 + 前端页面 + 编辑器）
- **价值**：Agent 可以读文档理解需求，写技术方案

#### F. Dify/Flowise 的 AI 工作流编排

- **借鉴点**：可视化编排 AI Agent 工作流
- **应用场景**：把 Workflow 引擎升级为支持 LLM 节点的编排（如：trigger → LLM 分析 → 创建 issue → 通知）
- **实现难度**：高（需要 LLM 集成 + 节点设计）

### 4.3 长期可借鉴（3-6 月实现）

#### G. Plane.so 的 "Issue Tracking is Dead" 理念

- **借鉴点**：从被动录入转向主动 Agent 工作流
- **应用场景**：
  - Agent 自动监控代码变更，发现潜在 issue
  - Agent 自动分析 plan 进度，提前预警风险
  - Agent 自动总结每日进展，生成日报
- **实现难度**：高（需要代码分析 + LLM + 定时任务）

#### H. Linear 的 Triage + Agent Workflow

- **借鉴点**：新 issue 进入时触发 Agent 分类、优先级评估、自动分配
- **应用场景**：加 `triage` 工作流，Agent 自动分析 issue 内容，建议优先级和 milestone
- **实现难度**：高（需要 LLM 分析 + 训练/提示工程）

#### I. CrewAI 的多 Agent 协作

- **借鉴点**：多个 Agent 角色协作（产品经理、开发、测试）
- **应用场景**：定义不同 Agent 角色，如 `pm_agent` 负责规划，`dev_agent` 负责实现，`qa_agent` 负责测试
- **实现难度**：高（需要 Agent 编排框架）

---

## 五、最推荐的 3 个借鉴方向

基于项目现状（个人项目、时间有限、核心优势是 MCP 集成），最推荐：

### 第一名：Plane AI 的 "Prompt-to-Structure"（短期）

**为什么**：最符合"人机协作"定位，实现简单，价值明显

**怎么做**：加一个 MCP tool `create_project_structure(prompt: str)`，Agent 描述项目，自动创建 milestone + issues + plan_items

**示例**：

```
Agent: "我要做一个博客系统，需要用户认证、文章管理、评论功能"
→ 自动创建：
  - Milestone: Phase 1 - 基础功能
  - Issues: [P1] 用户登录, [P1] 文章CRUD, [P2] 评论功能
  - Plan: 博客系统开发计划（含 checklist）
```

### 第二名：OneDev 的 Git 集成（中期）

**为什么**：开发者项目管理离不开代码，Git 事件自动关联 issue 是刚需

**怎么做**：
1. 加 Webhook 接收端点（GitHub/Gitea/Forgejo）
2. commit message 解析（`fix #123` 自动关闭 issue）
3. PR 创建自动关联 plan

**价值**：Agent 提交代码后，项目状态自动更新，减少手动操作

### 第三名：Tegon Actions 的自动化规则（中期）

**为什么**：Workflow 引擎已经有基础，扩展为 Action 框架很自然

**怎么做**：
1. 设计 Action YAML 格式（trigger → condition → action）
2. 支持 trigger：on_issue_created, on_plan_approved, on_milestone_closed
3. 支持 action：create_issue, update_issue, send_notification, call_webhook

**示例**：

```yaml
name: "Auto-triage new issues"
trigger: on_issue_created
condition: issue.source == "ai_agent"
action:
  - type: update_issue
    priority: "P2"
  - type: add_comment
    content: "Agent created issue, auto-set to P2"
```

---

## 六、总结与建议

本项目有一个**非常独特的定位**（人机协作 + MCP 原生），这是 Plane.so、Tegon 等大众项目没有专注的。建议：

1. **保持核心优势**：继续深耕 MCP 集成，让 Agent 调用体验做到最好
2. **补齐短板**：优先加 Git 集成和知识库，这是开发者刚需
3. **拥抱 AI 趋势**：逐步加入 AI 分析、自动分类、智能建议
4. **不要追求大而全**：优势是"小而美、专而精"，不要变成第二个 Plane

---

*报告生成时间：2026-05-18*
*数据来源：项目代码阅读 + SearXNG 搜索引擎（20+ 次查询）*
