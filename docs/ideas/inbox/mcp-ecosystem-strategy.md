# Idea: 强化 MCP 生态位战略

**来源**: 项目核心差异化优势 + Gitea/OneDev MCP 演进观察
**优先级**: 🟢 长期（构建护城河）
**预计工期**: 持续迭代
**价值**: 成为 MCP-native PM 工具的先行者和标准制定者

---

## 现状

你的项目有一个**非常独特的定位**：
- Plane.so / Tegon / OpenProject 都在推 AI，但**没有公开 MCP Server**
- OneDev / Gitea 有 MCP，但定位是 Git 托管，不是 PM
- 市场上**几乎没有 MCP-first 的项目管理工具**

这是你的**护城河机会**。

---

## 战略方向

### 1. MCP Server 独立化

**目标**: 让其他项目也能 `pip install pms-mcp` 接入你的系统

```python
# 独立包结构
pms-mcp/
├── pms_mcp/
│   ├── __init__.py
│   ├── server.py          # MCP server 核心
│   ├── tools/
│   │   ├── projects.py    # 项目管理工具
│   │   ├── issues.py      # Issue 管理工具
│   │   ├── plans.py       # 计划管理工具
│   │   └── workflow.py    # 工作流工具
│   ├── client.py          # 客户端封装
│   └── config.py          # 配置管理
├── tests/
└── setup.py
```

**使用方式**:
```python
# 其他项目接入
from pms_mcp import PMSClient

client = PMSClient(base_url="http://localhost:8000")
client.create_issue(title="Bug fix", priority="P1")
```

**为什么重要**:
- 降低接入门槛
- 形成生态
- 其他 AI Agent 框架（CrewAI, AutoGen）可以集成

---

### 2. MCP 工具设计指南

**目标**: 分享设计经验，成为社区参考标准

**文档结构**:
```
docs/mcp-design-guide/
├── 01-tool-granularity.md      # 工具粒度设计
├── 02-naming-conventions.md    # 命名规范
├── 03-parameter-design.md      # 参数设计原则
├── 04-error-handling.md        # 错误处理
├── 05-context-management.md    # 上下文管理
└── examples/
    ├── simple-crud.md
    ├── workflow-trigger.md
    └── multi-step-operation.md
```

**核心原则**:

| 原则 | 说明 | 示例 |
|------|------|------|
| **原子性** | 每个工具只做一件事 | `create_issue` vs `create_project_with_issues` |
| **幂等性** | 重复调用结果一致 | `update_issue` 带 idempotent_key |
| **自描述** | description 包含使用示例 | "Create a new issue. Example: 'Fix login bug'" |
| **容错性** | 参数错误时给出清晰提示 | 返回 `"error": "Priority must be one of: P0, P1, P2, P3"` |
| **上下文感知** | 工具能感知当前项目/用户 | 自动使用当前激活的项目 |

**示例：好的 tool description**:
```python
{
    "name": "update_issue_status",
    "description": """
    Update the status of an issue. Common usage:
    - "Move issue #3 to review" → status="review"
    - "Close issue #10" → status="closed"
    - "Reopen issue #5" → status="open"
    
    Available statuses: open, in_progress, review, testing, closed, deferred
    """,
    "parameters": {
        "issue_id": {"type": "integer", "description": "The issue number"},
        "status": {"type": "string", "description": "New status"},
        "reason": {"type": "string", "description": "Optional reason for the change"}
    }
}
```

---

### 3. 竞品 MCP 动态跟踪

**目标**: 持续关注 Gitea/OneDev/Plane 的 MCP 演进，保持领先

**跟踪清单**:

| 项目 | MCP 状态 | 关注点 | 检查频率 |
|------|----------|--------|----------|
| Gitea | ✅ 官方 MCP Server | 工具设计、认证方式 | 每月 |
| OneDev | ✅ 原生 MCP | AI 辅助功能集成 | 每月 |
| OpenProject | ⚠️ Enterprise 版 | 何时开源/社区版 | 每季度 |
| Plane.so | ❌ 暂无 | AI 工作流是否开放 MCP | 每季度 |
| Tegon | ❌ Actions 框架 | 是否会转标准 MCP | 每季度 |
| Kanboard | ⚠️ 社区插件 | 插件生态发展 | 每半年 |
| Vikunja | ⚠️ 社区 MCP | 功能完整性 | 每半年 |

**跟踪方法**:
1. 订阅项目 Release Notes RSS
2. 关注 GitHub Issues 标签 `mcp`, `ai`, `agent`
3. 加入相关 Discord/Forum 频道
4. 每季度做一次竞品 MCP 功能对比

---

### 4. 社区建设

**目标**: 吸引其他开发者使用和贡献 MCP 工具

**具体行动**:

1. **开源 MCP Server 独立包**
   - 单独仓库：`pms-mcp-server`
   - MIT 协议
   - 完整文档和示例

2. **提供 Docker 快速启动**
   ```bash
   docker run -p 8000:8000 pms-mcp-server
   ```

3. **编写集成教程**
   - "在 Claude Desktop 中使用 PMS MCP"
   - "在 Cursor 中集成项目管理"
   - "用 CrewAI 自动管理项目进度"

4. **建立 Showcase**
   - 收集社区使用案例
   - 展示不同 Agent 框架的集成方式

---

## 实施路线图

```
Phase 1（现在 - 1 月）
├── 编写 MCP 工具设计指南（内部文档）
├── 优化现有 24+ tools 的 description
└── 建立竞品 MCP 跟踪机制

Phase 2（1-3 月）
├── 抽取 MCP Server 为独立模块
├── 发布 pms-mcp PyPI 包
└── 编写集成教程（Claude/Cursor/CrewAI）

Phase 3（3-6 月）
├── 开源 MCP Server 仓库
├── 建立社区 Showcase
└── 推动成为 MCP-native PM 的标准参考
```

---

## 风险与应对

| 风险 | 可能性 | 应对 |
|------|--------|------|
| Plane.so / Tegon 突然推出 MCP | 中 | 保持工具设计领先，深耕人机协作场景 |
| MCP 协议本身演进 | 高 | 关注 Anthropic MCP 规范更新，及时适配 |
| 社区参与度低 | 中 | 先从内部打磨，再逐步开放 |
| 维护成本增加 | 中 | 独立包保持精简，核心功能优先 |

---

## 成功指标

- [ ] pms-mcp PyPI 包下载量 > 100
- [ ] 3+ 个社区集成案例
- [ ] MCP 设计指南被引用/参考
- [ ] 竞品 MCP 功能对比中保持领先
- [ ] 至少 1 个外部贡献者

---

## 参考

- Gitea MCP Server: https://about.gitea.com/resources/tutorials/gitea-mcp-server
- OneDev MCP: https://code.onedev.io/onedev/server
- MCP Protocol Spec: https://modelcontextprotocol.io
- Anthropic MCP Blog: https://www.anthropic.com/news/model-context-protocol
