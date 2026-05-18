# 同类开源项目调研汇总

> 调研日期：2026-05-18
> 调研方法：SearXNG 搜索引擎（香港节点）+ GitHub 浏览
> 覆盖范围：PM 工具、Git+PM 一体化、知识库、无代码平台、AI Agent 编排

---

## 一、综合型项目管理（Jira/Linear 替代）

### 1.1 Plane.so
- **Stars**: 46k+
- **官网**: https://plane.so
- **协议**: AGPL + Enterprise
- **核心特点**:
  - 最热门的开源 Jira/Linear 替代
  - 支持 self-hosted（复杂，需 PostgreSQL）
  - 现代 UI，Cycles/Modules/Views 概念
  - 2026.3 推出 Plane AI，支持 agent workflow
  - "Structure work from a prompt" — 自然语言创建项目结构
- **AI/MCP**: AI-native，但暂无公开 MCP Server
- **与本项目关系**: 直接竞品，但定位团队 vs 个人+Agent

### 1.2 Tegon
- **Stars**: 3k+
- **官网**: https://tegon.ai
- **协议**: MIT
- **核心特点**:
  - Dev-first 替代 Linear/Jira
  - Tegon Actions 自动化框架（类似 GitHub Actions）
  - 支持 agent 分配任务
- **AI/MCP**: Actions 框架，非标准 MCP
- **与本项目关系**: 自动化规则设计可借鉴

### 1.3 OpenProject
- **Stars**: 8k+
- **官网**: https://www.openproject.org
- **协议**: AGPL + Enterprise
- **核心特点**:
  - 企业级，功能最全
  - 模块化、插件丰富
  - Gantt/Wiki/BCF 支持
  - 2025 投资 AI 集成
  - 2026.3 推出 MCP Server（Enterprise 版）
- **AI/MCP**: Enterprise 版有 MCP
- **与本项目关系**: 企业级对标，插件机制可借鉴

### 1.4 Taiga
- **Stars**: 6k+
- **官网**: https://taiga.io
- **协议**: AGPL
- **核心特点**:
  - 敏捷导向，Scrum + Kanban 双模式
  - AngularJS 前端（较老）
  - 社区驱动
- **AI/MCP**: 无原生 AI
- **与本项目关系**: 敏捷方法论可借鉴

### 1.5 Leantime
- **Stars**: 4k+
- **官网**: https://leantime.io
- **协议**: AGPL + Pro
- **核心特点**:
  - 专为 ADHD/神经多样性设计
  - 目标导向，非任务导向
  - 有 AI 项目管理文章
- **AI/MCP**: 无原生 AI，但有 AI 集成讨论
- **与本项目关系**: UX 设计可借鉴

### 1.6 Focalboard
- **Stars**: 8k+
- **官网**: https://www.focalboard.com
- **协议**: AGPL + Mattermost 许可
- **核心特点**:
  - Mattermost 出品
  - Trello/Notion 风格看板
  - 维护模式（Mattermost 战略调整）
- **AI/MCP**: 无 AI
- **与本项目关系**: 看板 UI 可借鉴

### 1.7 WeKan
- **Stars**: 19k+
- **官网**: https://wekan.github.io
- **协议**: MIT
- **核心特点**:
  - 最像 Trello 的开源 Kanban
  - 社区 MCP server 集成
- **AI/MCP**: 社区 MCP
- **与本项目关系**: 看板体验可借鉴

### 1.8 Kanboard
- **Stars**: 8k+
- **官网**: https://kanboard.org
- **协议**: MIT
- **核心特点**:
  - 极简 Kanban，PHP
  - ChristianJStarr/kanboard-mcp 插件
- **AI/MCP**: 有 MCP Plugin
- **与本项目关系**: MCP 集成方式可借鉴

### 1.9 Vikunja
- **Stars**: 3k+
- **官网**: https://vikunja.io
- **协议**: AGPL
- **核心特点**:
  - Todoist/Trello 替代
  - 多视图（列表、看板、甘特）
  - 社区 Vikunja MCP Server
- **AI/MCP**: 社区 MCP
- **与本项目关系**: 多视图设计可借鉴

---

## 二、Git 托管 + 项目管理一体化

### 2.1 OneDev
- **Stars**: 5k+
- **官网**: https://onedev.io
- **协议**: MIT
- **核心特点**:
  - Git + CI/CD + Kanban + Packages 一体化
  - 原生 MCP Server
  - AI 辅助代码解释、构建失败调查
- **AI/MCP**: 原生 MCP + AI
- **与本项目关系**: Git 集成最佳参考

### 2.2 Gitea
- **Stars**: 46k+
- **官网**: https://gitea.com
- **协议**: MIT
- **核心特点**:
  - 轻量 GitHub 替代
  - Gitea Actions CI/CD
  - Gitea MCP Server（官方教程）
- **AI/MCP**: 官方 MCP Server
- **与本项目关系**: MCP Server 设计范式参考

### 2.3 Forgejo
- **Stars**: 5k+
- **官网**: https://forgejo.org
- **协议**: GPL
- **核心特点**:
  - Gitea 分支，完全开源
  - forgejo-mcp（社区）
- **AI/MCP**: 社区 MCP，官方对 AI 谨慎
- **与本项目关系**: 社区驱动参考

---

## 三、知识库/文档

### 3.1 Docmost
- **Stars**: 5k+
- **官网**: https://docmost.com
- **协议**: AGPL
- **核心特点**:
  - Notion/Confluence 替代
  - 协作 wiki
- **AI/MCP**: 无原生 AI
- **与本项目关系**: 知识库模块参考

### 3.2 Outline
- **Stars**: 15k+
- **官网**: https://www.getoutline.com
- **协议**: BSL + AGPL
- **核心特点**:
  - 团队知识库
  - React + Node.js
- **AI/MCP**: 无原生 AI
- **与本项目关系**: 编辑器设计参考

### 3.3 AppFlowy
- **Stars**: 30k+
- **官网**: https://appflowy.io
- **协议**: AGPL
- **核心特点**:
  - Notion 替代
  - 离线优先
  - AI 模型选择
- **AI/MCP**: AI 协作工作区
- **与本项目关系**: AI 集成方式参考

---

## 四、无代码/低代码平台

### 4.1 NocoBase
- **Stars**: 12k+
- **官网**: https://www.nocobase.com
- **协议**: AGPL + Enterprise
- **核心特点**:
  - AI + 无代码平台
  - 可构建 CRM/项目管理
- **AI/MCP**: AI 驱动
- **与本项目关系**: 可扩展性设计参考

### 4.2 Baserow
- **Stars**: 2k+
- **官网**: https://baserow.io
- **协议**: MIT + Enterprise
- **核心特点**:
  - Airtable 替代
  - 2025 转型 "AI-powered no-code platform"
- **AI/MCP**: AI 原生
- **与本项目关系**: AI 转型路径参考

### 4.3 Budibase
- **Stars**: 22k+
- **官网**: https://budibase.com
- **协议**: GPL + Enterprise
- **核心特点**:
  - 内部工具构建
  - AI agent + 工作流
- **AI/MCP**: AI-powered workflow
- **与本项目关系**: 工作流自动化参考

---

## 五、AI 工作流/Agent 编排

### 5.1 Dify
- **Stars**: 85k+
- **官网**: https://dify.ai
- **协议**: Apache 2.0 + Enterprise
- **核心特点**:
  - 可视化 Agent + Workflow + RAG
  - 生产级，企业采用率高
- **项目管理集成**: 通用平台，需自定义集成
- **与本项目关系**: 工作流可视化参考

### 5.2 Flowise
- **Stars**: 35k+
- **官网**: https://flowiseai.com
- **协议**: Apache 2.0 + Enterprise
- **核心特点**:
  - 可视化 AI Agent 构建
  - LangChain 基础
- **项目管理集成**: 通用平台，需自定义集成
- **与本项目关系**: 节点编排参考

### 5.3 Langflow
- **Stars**: 45k+
- **官网**: https://www.langflow.org
- **协议**: MIT
- **核心特点**:
  - 低代码 AI Agent
  - MCP Server 构建
- **项目管理集成**: 通用平台，需自定义集成
- **与本项目关系**: MCP 集成参考

### 5.4 CrewAI
- **Stars**: 25k+
- **官网**: https://www.crewai.com
- **协议**: MIT
- **核心特点**:
  - 多 Agent 编排
  - 角色扮演工作流
- **项目管理集成**: 通用框架，需自定义集成
- **与本项目关系**: 多 Agent 角色设计参考

### 5.5 n8n
- **Stars**: 65k+
- **官网**: https://n8n.io
- **协议**: Sustainable Use License + Enterprise
- **核心特点**:
  - 工作流自动化
  - 400+ 集成
  - AI Agent 节点
- **项目管理集成**: 通用平台，需自定义集成
- **与本项目关系**: 触发器-动作模式参考

---

## 六、调研数据来源

| 查询关键词 | 结果数 | 关键发现 |
|-----------|--------|----------|
| "open source project management tool self-hosted 2025" | 10 | Plane.so, Tegon, OpenProject 领先 |
| "Plane.so open source features" | 10 | AI-native, self-hosted, Cycles/Modules |
| "Tegon open source project management" | 10 | Dev-first, MIT, Actions 框架 |
| "OpenProject AI integration MCP" | 10 | 2026.3 MCP Server Enterprise |
| "OneDev Git project management" | 10 | Git+CI/CD+Kanban, 原生 MCP |
| "Gitea MCP server" | 10 | 官方 MCP Server 教程 |
| "self-hosted project management tool AI agent" | 10 | 趋势：AI-native 成为标配 |
| "best open source project management 2025" | 10 | Plane.so, OpenProject, Taiga 领先 |
| "AI agent project management 2026" | 10 | "Issue tracking is dead" 趋势 |
| "open source kanban tool MCP" | 10 | WeKan, Kanboard, Vikunja 有 MCP |

---

*报告生成时间：2026-05-18*
*搜索引擎：SearXNG (香港节点)*
