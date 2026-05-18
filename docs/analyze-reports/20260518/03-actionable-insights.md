# 可执行借鉴方案

> 基于项目现状和竞品调研，提炼出 9 个具体可借鉴方向
> 按优先级排序：短期（1-2 周）→ 中期（1-2 月）→ 长期（3-6 月）

---

## 短期可借鉴（1-2 周实现）

### 1. Prompt-to-Structure：自然语言创建项目结构

**来源**: Plane.so AI "Structure work from a prompt"

**现状问题**: Agent 创建项目时需要逐个调用 create_milestone、create_issue、create_plan，步骤繁琐

**方案**: 新增 MCP tool `create_project_structure`

```python
# backend/mcp_server.py 新增工具
@register_tool("create_project_structure")
def create_project_structure(prompt: str, project_id: int = None):
    """
    根据自然语言描述自动创建项目结构。
    
    Args:
        prompt: 项目描述，如"做一个博客系统，需要用户认证、文章管理、评论功能"
        project_id: 可选，指定项目；不指定则自动创建新项目
    
    Returns:
        创建的 milestone、issues、plan 列表
    """
    # 1. 调用 LLM 分析 prompt，提取功能模块
    # 2. 自动创建 Milestone（Phase 1 - 基础功能）
    # 3. 自动创建 Issues（按优先级 P1/P2/P3）
    # 4. 自动创建 Plan（含 checklist）
    # 5. 返回创建结果摘要
```

**实现步骤**:
1. 在 `backend/mcp_server.py` 注册新工具
2. 在 `backend/src/core/` 新建 `project_generator.py`
3. 使用简单的规则引擎或调用 LLM API 解析 prompt
4. 复用现有 `create_milestone`、`create_issue`、`create_plan` 逻辑

**预期效果**:
```
User: "我要做一个博客系统"
Agent: 调用 create_project_structure("博客系统，需要用户认证、文章管理、评论功能")
→ 自动创建：
  - Milestone: Phase 1 - 基础功能
  - Issues: [P1] 用户登录注册, [P1] 文章CRUD, [P2] 评论功能, [P2] 标签管理
  - Plan: 博客系统开发计划（含 8 个 checklist items）
```

---

### 2. MCP Tool 描述优化：自然语言操作

**来源**: Kanboard MCP Plugin (ChristianJStarr/kanboard-mcp)

**现状问题**: 现有 tool description 偏技术化，Agent 需要精确理解参数

**方案**: 优化 tool description，支持自然语言意图

```python
# 优化前
def update_issue(issue_id: int, title: str = None, status: str = None):
    """Update an existing issue."""

# 优化后
def update_issue(issue_id: int, title: str = None, status: str = None):
    """
    Update an existing issue. You can:
    - "Move issue #3 to review" → status="review"
    - "Rename issue #5 to 'Fix login bug'" → title="Fix login bug"
    - "Close issue #10" → status="closed"
    """
```

**实现步骤**:
1. 审查所有 24+ MCP tools 的 description
2. 添加自然语言示例到 description
3. 考虑添加 alias 参数（如 `action="move_to_review"`）

---

### 3. 看板拖拽优化

**来源**: WeKan, Focalboard, Plane.so

**现状问题**: Board 页面有看板视图，但拖拽体验可能不够流畅

**方案**: 引入 react-beautiful-dnd 或 @dnd-kit

**实现步骤**:
1. 评估现有 Board 组件的拖拽实现
2. 如使用原生 HTML5 drag-drop，迁移到专用库
3. 添加拖拽动画和视觉反馈
4. 拖拽后自动调用 update_issue_status API

---

## 中期可借鉴（1-2 月实现）

### 4. Git 集成：Webhook 自动关联

**来源**: OneDev, Gitea

**现状问题**: 项目管理和代码完全割裂，Agent 提交代码后需要手动更新 issue

**方案**: 添加 Webhook 接收端点，自动关联 Git 事件

```python
# backend/main.py 新增路由
@app.post("/webhook/git")
async def git_webhook(payload: GitWebhookPayload):
    """
    接收 Git 平台（GitHub/Gitea/Forgejo）的 webhook 事件
    
    支持事件：
    - push: 解析 commit message，自动关闭/关联 issue
    - pull_request: PR 创建/合并时更新 plan 状态
    - issue_comment: 同步评论到项目 issue
    """
    
    # 1. 验证 webhook signature
    # 2. 解析事件类型
    # 3. 提取 issue 引用（fix #123, closes #456）
    # 4. 自动更新对应 issue 状态
    # 5. 添加活动日志
```

**实现步骤**:
1. 新建 `backend/src/integrations/git.py`
2. 实现 Webhook 接收和签名验证
3. 实现 commit message 解析（正则提取 #issue_id）
4. 实现自动状态转换规则
5. 前端添加 Git 配置页面（仓库 URL、Webhook 设置）

**预期效果**:
```
Agent: git commit -m "fix login bug, closes #15"
→ Webhook 触发
→ Issue #15 自动标记为 "closed"
→ 添加活动日志："Closed by commit abc123"
→ 通知用户
```

---

### 5. 知识库模块：Wiki/Pages

**来源**: Docmost, Outline, Plane.so Pages

**现状问题**: 项目知识分散，没有统一的文档管理

**方案**: 添加 Wiki 模块，支持 Markdown 编辑，与 issue/plan 关联

```python
# backend/src/models/wiki.py
class WikiPage(Base):
    __tablename__ = "wiki_pages"
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    title = Column(String)
    content = Column(Text)  # Markdown
    parent_id = Column(Integer, ForeignKey("wiki_pages.id"), nullable=True)  # 层级
    linked_issues = relationship("Issue", secondary="wiki_issue_links")
    linked_plans = relationship("Plan", secondary="wiki_plan_links")
```

**实现步骤**:
1. 新建数据模型 `WikiPage`
2. 实现 CRUD API
3. 前端添加 Markdown 编辑器（react-markdown-editor-lite 或 @uiw/react-md-editor）
4. 支持在 issue/plan 中引用 wiki 页面
5. 支持 wiki 页面引用 issue/plan（双向链接）

---

### 6. Action 自动化框架

**来源**: Tegon Actions, GitHub Actions

**现状问题**: Workflow 引擎功能完整，但定义方式偏代码化，不够灵活

**方案**: 扩展为 YAML/JSON 定义的 Action 框架

```yaml
# .pms/actions/auto-triage.yml
name: "Auto-triage Agent Issues"
description: "Automatically set priority for AI-created issues"
trigger:
  type: issue_created
  condition: "issue.source == 'ai_agent'"
actions:
  - type: update_issue
    fields:
      priority: "P2"
  - type: add_comment
    content: "🤖 Auto-triaged: Agent-created issue set to P2"
  - type: send_notification
    message: "New agent issue created: {{issue.title}}"
```

**实现步骤**:
1. 设计 Action YAML schema
2. 新建 `backend/src/core/action_engine.py`
3. 实现 trigger 监听（基于现有 Workflow 引擎）
4. 实现 action 执行器（update_issue, add_comment, send_notification, webhook）
5. 前端添加 Action 编辑器（YAML + 可视化）

---

## 长期可借鉴（3-6 月实现）

### 7. AI Triage：智能分类与优先级评估

**来源**: Linear Triage, Plane AI

**现状问题**: 新 issue 需要人工分类和设置优先级

**方案**: 添加 AI triage 工作流，自动分析 issue 内容

```python
# backend/src/core/ai_triage.py
async def triage_issue(issue_id: int):
    """
    使用 LLM 分析 issue 内容，建议：
    - 优先级（P0/P1/P2/P3）
    - 类型（bug/feature/improvement）
    - 关联 milestone
    - 是否需要拆分
    """
    issue = get_issue(issue_id)
    
    prompt = f"""
    分析以下 issue，给出分类建议：
    
    标题：{issue.title}
    描述：{issue.description}
    来源：{issue.source}
    
    当前项目阶段：{current_milestone.name}
    已有 issue 分布：{issue_distribution}
    
    请输出 JSON：
    {{
        "priority": "P1",
        "type": "feature",
        "suggested_milestone": "Phase 2",
        "should_split": false,
        "reasoning": "..."
    }}
    """
    
    result = await llm.analyze(prompt)
    # 应用建议或提交审批
```

**实现步骤**:
1. 集成 LLM API（OpenAI/Claude/本地模型）
2. 设计 triage prompt 模板
3. 实现 triage 工作流节点
4. 添加审批机制（AI 建议 → 人工确认/自动应用）
5. 收集反馈，持续优化 prompt

---

### 8. 主动 Agent 工作流

**来源**: Plane.so "Issue Tracking is Dead", Linear Agent Workflow

**现状问题**: Agent 被动响应用户指令，没有主动行为

**方案**: 添加定时任务和事件监听，让 Agent 主动工作

```python
# backend/src/core/agent_worker.py
class AgentWorker:
    """后台 Agent，主动执行项目管理任务"""
    
    async def daily_digest(self):
        """每日总结：生成昨日进展、今日计划、风险预警"""
        
    async def progress_monitor(self):
        """进度监控：检测 milestone 延期风险，自动预警"""
        
    async def code_change_analyzer(self):
        """代码变更分析：监控 Git 提交，发现潜在 issue"""
        
    async def plan_health_check(self):
        """计划健康检查：检测 plan 完成度，建议调整"""
```

**实现步骤**:
1. 添加定时任务框架（APScheduler 或 Celery Beat）
2. 实现各 Worker 逻辑
3. 添加配置页面（启用/禁用、频率设置）
4. 实现通知机制（邮件/WebSocket/前端通知）

---

### 9. 多 Agent 角色协作

**来源**: CrewAI

**现状问题**: 只有一个通用 Agent，没有角色分工

**方案**: 定义不同 Agent 角色，协作完成项目管理

```yaml
# .pms/agents/pm-agent.yml
name: "PM Agent"
role: "project_manager"
persona: "经验丰富的项目经理，擅长规划和风险评估"
tools:
  - create_milestone
  - create_plan
  - analyze_progress
  - send_alert

---
# .pms/agents/dev-agent.yml
name: "Dev Agent"
role: "developer"
persona: "全栈开发工程师，擅长技术实现和代码审查"
tools:
  - create_issue
  - update_issue
  - analyze_code
  - create_tech_doc

---
# .pms/agents/qa-agent.yml
name: "QA Agent"
role: "qa_engineer"
persona: "质量工程师，擅长测试设计和缺陷分析"
tools:
  - create_test_plan
  - analyze_coverage
  - report_bug
```

**实现步骤**:
1. 设计 Agent 角色定义格式
2. 实现 Agent 编排引擎
3. 实现 Agent 间通信机制
4. 前端添加 Agent 管理页面
5. 实现 Agent 协作工作流

---

## 实施路线图建议

```
Phase 1（现在 - 2 周后）
├── ✅ Prompt-to-Structure MCP tool
├── ✅ MCP tool 描述优化
└── ✅ 看板拖拽优化

Phase 2（2 周 - 2 月后）
├── Git Webhook 集成
├── Wiki 知识库模块
└── Action 自动化框架

Phase 3（2 月 - 6 月后）
├── AI Triage 智能分类
├── 主动 Agent 工作流
└── 多 Agent 角色协作
```

---

*报告生成时间：2026-05-18*
*基于：项目代码分析 + 20+ 同类开源项目调研*
