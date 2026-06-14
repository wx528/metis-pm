# Project Copilot 技术方案

## 基于 pm-copilot-engine 框架的项目管理系统设计

> **设计哲学：引擎提供骨架，业务赋予血肉。**
>
> `pm-copilot-engine` 是从 Hermes 萃取的 AI 引擎——负责 LLM 调度、工具注册、对话循环。项目管理系统是这个引擎的消费者——提供业务模型、PM 工具、Web 界面。二者是**引擎层 + 业务层**的关系，物理上分离为两个仓库，运行时通过 Python import 融为一体。
>
> **但 AI 是涡轮增压器，不是发动机。** 系统必须能在零 AI 依赖下正常运行。关闭 Copilot，它是一辆完整的汽车；开启 Copilot，它获得主动感知、智能决策、自主行动的能力。切换只需一个环境变量。

---

## 1. 架构总览

```
┌──────────────────────────────────────────────────────────────────────┐
│                         双仓库架构                                    │
│                                                                      │
│  ┌──────────────────────────┐        ┌────────────────────────────┐ │
│  │   pm-copilot-engine       │        │   your-pm-system            │ │
│  │   (独立仓库 + PyPI)       │        │   (独立仓库)                │ │
│  │                          │        │                             │ │
│  │  pm_copilot_engine/      │        │  copilot/                   │ │
│  │  ├── agent/              │        │  ├── models.py             │ │
│  │  │   └── agent.py        │        │  ├── tools.py              │ │
│  │  ├── tools/              │        │  │   └── register_all()    │ │
│  │  │   ├── registry.py     │        │  ├── scheduler.py          │ │
│  │  │   ├── web_tools.py    │        │  ├── trigger_hub.py        │ │
│  │  │   └── ...             │        │  ├── services/             │ │
│  │  ├── toolsets.py         │        │  └── web/                  │ │
│  │  └── run_agent.py        │        │                             │ │
│  │                          │        │  main.py                    │ │
│  │  pyproject.toml          │        │  pyproject.toml             │ │
│  │  name = "pm-copilot-eng" │        │  dependencies = [           │ │
│  │                          │        │      "pm-copilot-engine"    │ │
│  └──────────┬──────────────┘        └──────────────┬─────────────┘ │
│             │                                      │                 │
│             └────────── pip install ───────────────┘                 │
│                                                                      │
│  运行时融合：                                                          │
│  from pm_copilot_engine import AIAgent, registry                     │
│  from copilot.tools import register_all_tools                        │
│  register_all_tools()        ← 业务工具注册到引擎注册表                 │
│  agent = AIAgent(enabled_toolsets=["pm"])                            │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.1 架构分层

| 层级 | 仓库 | 职责 | 代码归属 |
|------|------|------|----------|
| **引擎层** | `pm-copilot-engine` | LLM 调度、工具注册表、对话循环、内建工具 | 可复用基础框架 |
| **业务层** | `your-pm-system` | 业务模型、PM 工具实现、Copilot 调度、Web 界面 | 项目管理系统专属 |

### 1.2 关键交互边界

```
业务层 import 引擎层：
  from pm_copilot_engine import AIAgent              ← 创建 Agent
  from pm_copilot_engine.tools.registry import registry  ← 注册工具
  from pm_copilot_engine.toolsets import TOOLSETS    ← 注册 toolset

引擎层不感知业务层：
  registry.register(name="list_projects", ...)  ← 业务调用，引擎只收参数
  AIAgent(enabled_toolsets=["pm"])              ← 引擎只按 toolset 名过滤

运行时融合后：
  AIAgent.run_conversation() → LLM → function call → registry.dispatch()
                                                         ↓
                                                copilot.tools.list_projects()
                                                         ↓
                                                copilot.models.db_session.query()
```

### 1.3 可选启用架构（核心设计约束）

AI 是增强层，不是必要层。系统必须能在零 AI 依赖下正常运行。

```
启动路径分叉（由 PM_COPILOT_ENABLED 控制）：

┌─────────────────────────────────────────────────────────────┐
│                    python main.py                            │
│                                                             │
│   PM_COPILOT_ENABLED=true?                                  │
│        │                                                    │
│   ┌────┴────┐                                              │
│   │         │                                               │
│  Yes       No                                               │
│   │         │                                               │
│   ▼         ▼                                               │
│ ┌──────────────┐      ┌──────────────────────────────┐    │
│ │ 完整智能模式  │      │ 常规管理模式（降级模式）       │    │
│ │              │      │                              │    │
│ │ pip install   │      │ pip install pm-copilot-engine│    │
│ │ pm-copilot-en│      │ （可选，不装也行）            │    │
│ │ gine          │      │                              │    │
│ │              │      │                              │    │
│ │ register_all_│      │ 跳过工具注册                   │    │
│ │ tools()       │      │ 不创建 Copilot                 │    │
│ │ 注册 PM 工具  │      │ TriggerHub 为 no-op            │    │
│ │ 创建 Copilot  │      │ 不启动调度器                   │    │
│ │ 启动调度器    │      │                              │    │
│ │ 启动 Web     │◄────►│ 启动 Web（无 AI 界面）          │    │
│ └──────────────┘      └──────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**关键设计原则：**

| 原则 | 说明 |
|------|------|
| **引擎独立发版** | `pm-copilot-engine` 可独立打 tag、发 PyPI，语义化版本控制 |
| **延迟加载** | AI 相关模块（含引擎）延迟 import，启动时不加载 |
| **Graceful Degradation** | AI 禁用时所有触发点正常调用，静默无效果，不抛异常 |
| **数据库无关** | 引擎不依赖任何业务数据库，数据库在业务层管理 |
| **前端自适应** | Web 界面根据开关自动显示/隐藏 AI 相关功能 |
| **一键切换** | 仅通过 `PM_COPILOT_ENABLED` 环境变量控制，无需改代码 |

---

## 2. 引擎层设计（pm-copilot-engine）

### 2.1 引擎仓库结构

```
pm-copilot-engine/                  # 引擎仓库
├── pm_copilot_engine/              # Python 包
│   ├── __init__.py                 # 导出 AIAgent, registry, TOOLSETS
│   ├── agent/                      # LLM 调度核心（完整保留）
│   │   ├── __init__.py
│   │   ├── agent.py                # Agent 核心逻辑
│   │   ├── auxiliary_client.py     # 辅助模型客户端
│   │   ├── web_search_registry.py  # 网络搜索 provider 注册
│   │   └── ...
│   ├── tools/                      # 工具系统
│   │   ├── __init__.py             # 工具发现机制
│   │   ├── registry.py             # 全局注册表（核心，必须保留）
│   │   ├── model_tools.py          # 工具调度、LLM function call 映射
│   │   ├── web_tools.py            # 网络搜索/抓取（可选保留）
│   │   ├── terminal_tool.py        # 终端操作（可选保留）
│   │   ├── file_tools.py           # 文件读写（可选保留）
   │   │   ├── browser_tool.py       # 浏览器自动化（可选保留）
│   │   ├── memory_tool.py          # 持久记忆（可选保留）
│   │   └── ...                     # 其他内建工具按需保留
│   ├── toolsets.py                 # Toolset 框架定义
│   ├── run_agent.py                # AIAgent 类（业务层主要入口）
│   ├── model_tools.py              # 工具调度入口
│   ├── providers/                  # LLM Provider 支持
│   │   └── ...
│   └── utils.py
│
├── pyproject.toml                  # name = "pm-copilot-engine"
├── README.md                       # 引擎使用文档
├── NOTICE                          # 声明 Fork 自 Hermes
└── tests/                          # 引擎核心测试
```

### 2.2 引擎裁剪清单（删除 vs 保留）

Fork `hermes-agent` 后大刀阔斧裁剪，只保留骨架：

| 保留 | 删除 | 理由 |
|------|------|------|
| `pm_copilot_engine/agent/` | `gateway/` | 消息网关（Telegram/Discord/Slack），PM 系统不需要 |
| `pm_copilot_engine/tools/registry.py` | `tui_gateway/` | TUI 网关，不需要 |
| `pm_copilot_engine/tools/model_tools.py` | `web/` | Hermes 自带的 Web 界面，业务层自己实现 |
| `pm_copilot_engine/tools/web_tools.py` | `ui-tui/` | 终端 UI，不需要 |
| `pm_copilot_engine/tools/file_tools.py` | `docker/` | Docker 配置，业务层自行管理 |
| `pm_copilot_engine/tools/terminal_tool.py` | `cron/` | 定时任务，业务层用 APScheduler 自行管理 |
| `pm_copilot_engine/tools/browser_tool.py` | `hermes_cli/` | CLI 命令行工具，PM 系统不需要 |
| `pm_copilot_engine/tools/memory_tool.py` | `hermes_bootstrap.py` | 引导脚本，不需要 |
| `pm_copilot_engine/providers/` | `setup-hermes.sh` | 安装脚本，不需要 |
| `pm_copilot_engine/run_agent.py` | `optional-mcps/` | 可选 MCP 服务器，按需保留 |
| `pm_copilot_engine/toolsets.py` | `optional-skills/` | 可选技能，按需保留 |
| `pm_copilot_engine/utils.py` | `docs/` | Hermes 文档，替换为引擎自己的文档 |

### 2.3 引擎导出的公共 API

引擎层通过 `pm_copilot_engine/__init__.py` 显式导出以下接口，业务层只应使用这些：

```python
# pm_copilot_engine/__init__.py

"""
pm-copilot-engine: AI Agent Engine for Project Management
Forked from Hermes by NousResearch, tailored for PM Copilot.
"""

from pm_copilot_engine.run_agent import AIAgent
from pm_copilot_engine.tools.registry import registry
from pm_copilot_engine.toolsets import TOOLSETS

__version__ = "0.1.0"
__all__ = ["AIAgent", "registry", "TOOLSETS"]
```

| 导出项 | 类型 | 业务层用途 |
|--------|------|-----------|
| `AIAgent` | 类 | 创建 Agent 实例 |
| `registry` | 单例 | 注册业务工具 |
| `TOOLSETS` | 字典 | 注册业务 toolset |

### 2.4 引擎 pyproject.toml

```toml
# pm-copilot-engine/pyproject.toml

[project]
name = "pm-copilot-engine"
version = "0.1.0"
description = "AI Agent Engine for Project Management — forked from Hermes"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
authors = [
    {name = "Your Name", email = "you@example.com"},
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "openai>=1.0",
    "anthropic>=0.30",
    "httpx>=0.27",
    "pyyaml>=6.0",
    "tiktoken>=0.7",
    # ... 其他必要的核心依赖
]

[project.urls]
Homepage = "https://github.com/your-org/pm-copilot-engine"
Repository = "https://github.com/your-org/pm-copilot-engine"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["pm_copilot_engine"]
```

### 2.5 许可证合规（NOTICE 文件）

```
pm-copilot-engine/NOTICE

This project is derived from Hermes by NousResearch.
Original repository: https://github.com/NousResearch/hermes-agent
Original license: MIT License
Copyright (c) NousResearch

Modifications: Package renamed, codebase pruned to core engine,
               restructured as standard Python package.
```

---

## 3. 业务层设计（your-pm-system）

### 3.1 目录结构

```
your-pm-system/                     # 项目管理系统仓库
├── copilot/                        # 业务系统主包
│   ├── __init__.py
│   ├── models.py                   # SQLAlchemy ORM：Project / Task / User / Message / RiskAlert
│   ├── database.py                 # DB session 管理、初始化
│   ├── tools.py                    # PM 工具实现 + register_all_tools() 函数
│   ├── scheduler.py                # PMCopilot + CopilotScheduler
│   ├── trigger_hub.py              # 触发决策中心（TriggerHub + NoOpTriggerHub）
│   ├── services/
│   │   ├── __init__.py
│   │   ├── notifications.py        # 告警推送（WebSocket / 企业微信 / 钉钉 / Slack）
│   │   └── reports.py              # 报告渲染（Markdown / PDF）
│   └── web/                        # 管理后台 Web 服务
│       ├── __init__.py
│       ├── app.py                  # FastAPI 主应用
│       ├── routes/
│       │   ├── projects.py         # 项目 CRUD
│       │   ├── tasks.py            # 任务 CRUD
│       │   ├── messages.py         # 消息/讨论
│       │   ├── copilot.py          # Copilot 交互接口
│       │   └── mcp.py              # 外部 MCP 服务端点
│       └── static/                 # 前端静态资源
│
├── main.py                         # 系统统一入口
├── pyproject.toml                  # 业务系统依赖
└── .env                            # 环境变量配置
```

### 3.2 业务层 pyproject.toml

```toml
# your-pm-system/pyproject.toml

[project]
name = "your-pm-system"
version = "0.1.0"
description = "Project Management System with AI Copilot"
requires-python = ">=3.10"

dependencies = [
    # 引擎依赖（PyPI 直接安装）
    "pm-copilot-engine>=0.1.0",

    # Web 框架
    "fastapi>=0.100",
    "uvicorn[standard]",
    "websockets",

    # 数据库
    "sqlalchemy>=2.0",
    "psycopg2-binary",          # PostgreSQL（可选）

    # 调度
    "apscheduler",

    # 工具
    "python-dotenv",
    "pydantic>=2.0",
]
```

---

## 4. 数据模型

```python
# copilot/models.py

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text,
    ForeignKey, Boolean, Table
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Project(Base):
    """项目"""
    __tablename__ = "projects"

    id          = Column(String(36), primary_key=True)
    name        = Column(String(200), nullable=False)
    description = Column(Text)
    status      = Column(String(20), default="active")          # active / archived / cancelled
    progress_percent = Column(Integer, default=0)               # 0-100
    risk_level  = Column(String(20), default="low")             # low / medium / high / critical
    deadline    = Column(DateTime)                               # 项目截止日期
    budget_used = Column(Float, default=0)
    budget_total= Column(Float, default=0)
    owner_id    = Column(String(36), ForeignKey("users.id"))
    owner       = relationship("User", back_populates="owned_projects")
    tasks       = relationship("Task", back_populates="project")
    members     = relationship("User", secondary="project_members")
    created_at  = Column(DateTime, default=datetime.now)
    updated_at  = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Task(Base):
    """任务"""
    __tablename__ = "tasks"

    id          = Column(String(36), primary_key=True)
    title       = Column(String(300), nullable=False)
    description = Column(Text)
    status      = Column(String(20), default="open")            # open / in_progress / blocked / completed / cancelled
    priority    = Column(String(10), default="medium")          # low / medium / high / urgent
    deadline    = Column(DateTime)
    completion_percent = Column(Integer, default=0)             # 0-100
    notes       = Column(Text)                                   # 备注（含 Copilot 操作记录）
    project_id  = Column(String(36), ForeignKey("projects.id"))
    project     = relationship("Project", back_populates="tasks")
    assignee_id = Column(String(36), ForeignKey("users.id"))
    assignee    = relationship("User", back_populates="tasks")
    created_at  = Column(DateTime, default=datetime.now)
    updated_at  = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class User(Base):
    """用户/团队成员"""
    __tablename__ = "users"

    id          = Column(String(36), primary_key=True)
    name        = Column(String(100), nullable=False)
    email       = Column(String(200))
    role        = Column(String(50), default="developer")       # developer / pm / designer / qa / ops
    department  = Column(String(50))
    is_active   = Column(Boolean, default=True)
    owned_projects = relationship("Project", back_populates="owner")
    tasks       = relationship("Task", back_populates="assignee")


class Message(Base):
    """消息/讨论"""
    __tablename__ = "messages"

    id          = Column(String(36), primary_key=True)
    content     = Column(Text, nullable=False)
    type        = Column(String(20), default="comment")         # comment / decision / alert / file / system
    project_id  = Column(String(36), ForeignKey("projects.id"))
    project     = relationship("Project")
    author_id   = Column(String(36), ForeignKey("users.id"))
    author      = relationship("User")
    created_at  = Column(DateTime, default=datetime.now)


class RiskAlert(Base):
    """风险告警"""
    __tablename__ = "risk_alerts"

    id              = Column(String(36), primary_key=True)
    title           = Column(String(300), nullable=False)
    description     = Column(Text)
    level           = Column(String(20), default="medium")      # critical / high / medium / low
    source          = Column(String(50), default="manual")      # manual / copilot / system
    is_resolved     = Column(Boolean, default=False)
    suggested_action= Column(Text)
    project_id      = Column(String(36), ForeignKey("projects.id"), nullable=True)
    created_at      = Column(DateTime, default=datetime.now)
    resolved_at     = Column(DateTime)
```

---

## 5. 工具层设计（引擎接口 + 业务实现）

### 5.1 注册机制：引擎提供接口，业务层实现并注册

引擎层只提供注册接口，业务层在运行时注册自己的工具。

```python
# copilot/tools.py — 业务层的工具实现和注册

import json
import logging
from datetime import datetime, timedelta

from copilot.models import Project, Task, User, Message, RiskAlert, db_session

logger = logging.getLogger(__name__)


# ── 工具实现 ──

def list_projects(query: str = "", status: str = "active", **kwargs) -> str:
    """列出项目"""
    q = db_session.query(Project)
    if status != "all":
        q = q.filter_by(status=status)
    if query:
        q = q.filter(Project.name.contains(query))
    projects = q.all()
    return json.dumps({
        "count": len(projects),
        "projects": [
            {
                "id": str(p.id),
                "name": p.name,
                "owner": p.owner.name if p.owner else None,
                "progress_percent": p.progress_percent,
                "status": p.status,
                "deadline": p.deadline.isoformat() if p.deadline else None,
                "risk_level": p.risk_level,
            }
            for p in projects
        ]
    }, ensure_ascii=False, indent=2)


def get_project_detail(project_id: str = "", **kwargs) -> str:
    """获取项目详情"""
    project = db_session.query(Project).get(project_id)
    if not project:
        return json.dumps({"error": f"Project {project_id} not found"})
    tasks = db_session.query(Task).filter_by(project_id=project_id).all()
    return json.dumps({
        "project": {"id": str(project.id), "name": project.name, "status": project.status},
        "tasks": [{"id": str(t.id), "title": t.title, "status": t.status} for t in tasks],
    }, ensure_ascii=False, indent=2)


def get_overdue_tasks(days: int = 7, **kwargs) -> str:
    """获取逾期任务"""
    deadline = datetime.now() + timedelta(days=days)
    tasks = db_session.query(Task).filter(
        Task.deadline <= deadline,
        Task.status.notin_(["completed", "cancelled"])
    ).order_by(Task.deadline).all()
    return json.dumps({
        "count": len(tasks),
        "tasks": [
            {
                "id": str(t.id), "title": t.title,
                "project": t.project.name,
                "deadline": t.deadline.isoformat() if t.deadline else None,
            }
            for t in tasks
        ]
    }, ensure_ascii=False, indent=2)


def get_team_workload(**kwargs) -> str:
    """获取团队负载"""
    members = db_session.query(User).filter_by(is_active=True).all()
    result = []
    for m in members:
        active = m.tasks.filter(Task.status.in_(["open", "in_progress"])).count()
        result.append({"name": m.name, "active_tasks": active})
    return json.dumps({"members": result}, ensure_ascii=False, indent=2)


def search_messages(hours: int = 24, keyword: str = "", **kwargs) -> str:
    """搜索消息"""
    since = datetime.now() - timedelta(hours=hours)
    q = db_session.query(Message).filter(Message.created_at >= since)
    if keyword:
        q = q.filter(Message.content.contains(keyword))
    messages = q.order_by(Message.created_at.desc()).limit(50).all()
    return json.dumps({
        "messages": [
            {"author": m.author.name, "content": m.content[:300], "created_at": m.created_at.isoformat()}
            for m in messages
        ]
    }, ensure_ascii=False, indent=2)


def create_risk_alert(title: str = "", description: str = "", level: str = "medium",
                      project_id: str = "", suggested_action: str = "", **kwargs) -> str:
    """创建风险告警"""
    alert = RiskAlert(
        title=title, description=description, level=level,
        project_id=project_id or None,
        source="copilot", suggested_action=suggested_action,
    )
    db_session.add(alert)
    db_session.commit()
    return json.dumps({"success": True, "alert_id": str(alert.id)}, ensure_ascii=False)


def get_project_metrics(**kwargs) -> str:
    """获取项目健康指标"""
    total = db_session.query(Project).filter_by(status="active").count()
    overdue = db_session.query(Task).filter(Task.deadline < datetime.now(), Task.status != "completed").count()
    return json.dumps({"active_projects": total, "overdue_tasks": overdue}, ensure_ascii=False)


def update_task_status(task_id: str = "", status: str = "", note: str = "", **kwargs) -> str:
    """更新任务状态"""
    task = db_session.query(Task).get(task_id)
    if not task:
        return json.dumps({"error": f"Task {task_id} not found"})
    old_status = task.status
    task.status = status
    if note:
        task.notes = f"{task.notes or ''}\n[{datetime.now().strftime('%m-%d %H:%M')} Copilot] {note}".strip()
    db_session.commit()
    return json.dumps({"success": True, "old_status": old_status, "new_status": status}, ensure_ascii=False)


# ── 注册函数 ──

def register_all_tools():
    """
    将所有 PM 工具注册到引擎的 registry。
    在系统启动时调用一次。
    """
    from pm_copilot_engine.tools.registry import registry

    registry.register(
        name="list_projects", toolset="pm",
        schema={
            "name": "list_projects",
            "description": "列出所有项目概览（进度、风险等级、截止日期）",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "default": ""},
                    "status": {"type": "string", "enum": ["active", "archived", "all"], "default": "active"}
                }
            }
        },
        handler=lambda args, **kw: list_projects(**args, **kw),
        emoji="📁",
    )

    registry.register(
        name="get_project_detail", toolset="pm",
        schema={
            "name": "get_project_detail",
            "description": "获取指定项目的详细信息（含任务列表）",
            "parameters": {
                "type": "object",
                "properties": {"project_id": {"type": "string"}},
                "required": ["project_id"]
            }
        },
        handler=lambda args, **kw: get_project_detail(**args, **kw),
        emoji="📋",
    )

    registry.register(
        name="get_overdue_tasks", toolset="pm",
        schema={
            "name": "get_overdue_tasks",
            "description": "获取即将到期或已逾期的任务列表",
            "parameters": {
                "type": "object",
                "properties": {"days": {"type": "integer", "default": 7}}
            }
        },
        handler=lambda args, **kw: get_overdue_tasks(**args, **kw),
        emoji="⏰",
    )

    registry.register(
        name="get_team_workload", toolset="pm",
        schema={
            "name": "get_team_workload",
            "description": "获取团队成员当前负载分布",
            "parameters": {"type": "object", "properties": {}}
        },
        handler=lambda args, **kw: get_team_workload(**args, **kw),
        emoji="👥",
    )

    registry.register(
        name="search_messages", toolset="pm",
        schema={
            "name": "search_messages",
            "description": "搜索近期消息和讨论",
            "parameters": {
                "type": "object",
                "properties": {
                    "hours": {"type": "integer", "default": 24},
                    "keyword": {"type": "string", "default": ""}
                }
            }
        },
        handler=lambda args, **kw: search_messages(**args, **kw),
        emoji="💬",
    )

    registry.register(
        name="create_risk_alert", toolset="pm",
        schema={
            "name": "create_risk_alert",
            "description": "创建风险告警并推送给干系人",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "level": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                    "project_id": {"type": "string", "default": ""},
                    "suggested_action": {"type": "string", "default": ""}
                },
                "required": ["title", "description", "level"]
            }
        },
        handler=lambda args, **kw: create_risk_alert(**args, **kw),
        emoji="🚨",
    )

    registry.register(
        name="get_project_metrics", toolset="pm",
        schema={
            "name": "get_project_metrics",
            "description": "获取项目整体健康指标快照",
            "parameters": {"type": "object", "properties": {}}
        },
        handler=lambda args, **kw: get_project_metrics(**args, **kw),
        emoji="📊",
    )

    registry.register(
        name="update_task_status", toolset="pm",
        schema={
            "name": "update_task_status",
            "description": "更新任务状态（如标记为 completed/blocked）",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["open", "in_progress", "blocked", "completed", "cancelled"]},
                    "note": {"type": "string", "default": ""}
                },
                "required": ["task_id", "status"]
            }
        },
        handler=lambda args, **kw: update_task_status(**args, **kw),
        emoji="✏️",
    )

    logger.info("Registered 8 PM tools to engine registry")
```

### 5.2 Toolset 注册

```python
# 在系统启动时注册 toolset

from pm_copilot_engine.toolsets import TOOLSETS

TOOLSETS["pm"] = {
    "description": "项目管理系统工具集",
    "tools": [
        "list_projects", "get_project_detail", "get_overdue_tasks",
        "get_team_workload", "search_messages", "create_risk_alert",
        "get_project_metrics", "update_task_status",
    ],
    "includes": [],
}
```

### 5.3 工具清单

| 工具名 | 功能 | 权限 | 业务函数 |
|--------|------|------|----------|
| `list_projects` | 列出项目概览 | 只读 | `copilot.tools.list_projects` |
| `get_project_detail` | 获取项目详情（含任务） | 只读 | `copilot.tools.get_project_detail` |
| `get_overdue_tasks` | 获取逾期任务列表 | 只读 | `copilot.tools.get_overdue_tasks` |
| `get_team_workload` | 获取团队负载分布 | 只读 | `copilot.tools.get_team_workload` |
| `search_messages` | 搜索近期消息 | 只读 | `copilot.tools.search_messages` |
| `get_project_metrics` | 获取项目健康指标 | 只读 | `copilot.tools.get_project_metrics` |
| `create_risk_alert` | 创建风险告警 | **写入** | `copilot.tools.create_risk_alert` |
| `update_task_status` | 更新任务状态 | **写入** | `copilot.tools.update_task_status` |

---

## 6. Agent 本体设计（PM Copilot）

### 6.1 PMCopilot 核心

```python
# copilot/scheduler.py

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional

from pm_copilot_engine import AIAgent

logger = logging.getLogger("copilot")


class PMCopilot:
    """
    项目管理常驻智能主理人。
    持有 AIAgent 实例，提供高阶业务方法。
    """

    SYSTEM_PROMPT = """你是项目管理系统的智能主理人 PM Copilot...
    （详见完整 prompt）"""

    def __init__(self, model: Optional[str] = None):
        model = model or os.getenv("PM_MODEL", "anthropic/claude-sonnet-4")
        self.agent = AIAgent(
            model=model,
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
            ephemeral_system_prompt=self.SYSTEM_PROMPT,
            enabled_toolsets=["pm"],
            max_iterations=25,
        )
        self.history = []

    def scan(self) -> str:
        """全量巡检"""
        return self._run("""
            执行项目健康巡检：
            1. get_project_metrics()
            2. list_projects(status="active")
            3. get_overdue_tasks(days=7)
            4. get_team_workload()
            5. 如有风险，create_risk_alert()
            返回中文巡检报告。
        """)

    def daily_report(self) -> str:
        """生成日报"""
        return self._run("生成日报...", keep_history=False)

    def weekly_report(self) -> str:
        """生成周报"""
        return self._run("生成周报...", keep_history=False)

    def ask(self, question: str) -> str:
        """回答项目相关问题"""
        return self._run(question)

    def _run(self, prompt: str, keep_history: bool = True) -> str:
        """底层调用 AIAgent"""
        result = self.agent.run_conversation(
            user_message=prompt,
            conversation_history=self.history if keep_history else None,
        )
        if keep_history:
            self.history.extend(result.get("messages", []))
            if len(self.history) > 40:
                self.history = self.history[-40:]
        return result["final_response"]
```

### 6.2 AIAgent 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `quiet_mode` | `True` | 关闭 CLI spinner 和终端输出 |
| `skip_context_files` | `True` | 不加载 AGENTS.md |
| `skip_memory` | `True` | 禁用引擎自带记忆，自行管理 |
| `enabled_toolsets` | `["pm"]` | 只加载 PM 工具集 |
| `max_iterations` | `25` | 限制工具调用次数，控制成本 |
| `ephemeral_system_prompt` | PM 角色定义 | 角色化提示词 |

---

## 7. 触发机制设计（TriggerHub）

### 7.1 五类触发信号

| 触发类型 | 条件 | 优先级 | 实现 |
|----------|------|--------|------|
| 时间触发 | 固定时刻/周期 | 5 | APScheduler |
| 事件触发 | 业务数据变更 | 4-7 | DB 触发器 / 代码埋点 |
| 请求触发 | 外部显式调用 | 6 | HTTP / MCP |
| 状态触发 | 系统指标异常 | 7-9 | 监控回调 |
| 消息触发 | 关键词命中 | 3-6 | 消息队列消费者 |

### 7.2 触发中心实现

```python
# copilot/trigger_hub.py

import asyncio
import logging
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger("copilot.trigger")


class TriggerType(Enum):
    SCHEDULED = "scheduled"
    EVENT = "event"
    REQUEST = "request"
    STATE = "state"
    MESSAGE = "message"


@dataclass
class TriggerContext:
    trigger_type: TriggerType
    source: str
    payload: dict = field(default_factory=dict)
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)


class TriggerHub:
    """完整触发中心（AI 启用时使用）"""

    def __init__(self, copilot):
        from copilot.scheduler import PMCopilot
        self.copilot: PMCopilot = copilot
        self._queue = asyncio.Queue()
        self._running = False
        self._cooldown = {}

    def fire(self, context: TriggerContext) -> bool:
        key = f"{context.trigger_type.value}:{context.source}"
        last = self._cooldown.get(key)
        if last and (datetime.now() - last).total_seconds() < 60:
            return False
        self._cooldown[key] = datetime.now()

        if context.priority >= 8:
            asyncio.create_task(self._process(context))
        else:
            asyncio.get_event_loop().call_soon(
                lambda: asyncio.create_task(self._queue.put(context))
            )
        return True

    def fire_scheduled(self, job_name: str, payload: dict = None):
        return self.fire(TriggerContext(TriggerType.SCHEDULED, job_name, payload or {}, 5))

    def fire_event(self, event_type: str, entity_id: str, payload: dict = None):
        priority = 7 if event_type in ("task_overdue", "risk_critical") else 4
        return self.fire(TriggerContext(TriggerType.EVENT, f"{event_type}:{entity_id}", payload or {}, priority))

    def fire_request(self, source: str, query: str, user_id: str = None):
        return self.fire(TriggerContext(TriggerType.REQUEST, source, {"query": query, "user_id": user_id}, 6))

    def fire_state(self, metric_name: str, current_value: float, threshold: float):
        priority = 9 if current_value > threshold * 1.5 else 7
        return self.fire(TriggerContext(TriggerType.STATE, metric_name, {"value": current_value, "threshold": threshold}, priority))

    def fire_message(self, message_id: str, content: str, project_id: str = None):
        keywords = ["阻塞", "延期", "风险", "紧急", "bug", "故障"]
        matched = [k for k in keywords if k in content.lower()]
        if not matched:
            return False
        priority = 6 if "紧急" in matched or "故障" in matched else 3
        return self.fire(TriggerContext(TriggerType.MESSAGE, f"message:{message_id}", {"content": content, "keywords": matched, "project_id": project_id}, priority))

    async def start(self):
        self._running = True
        while self._running:
            try:
                ctx = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._process(ctx)
            except asyncio.TimeoutError:
                continue

    async def _process(self, ctx: TriggerContext):
        loop = asyncio.get_event_loop()
        if ctx.trigger_type == TriggerType.SCHEDULED:
            if ctx.source == "daily_scan":
                await loop.run_in_executor(None, self.copilot.scan)
            elif ctx.source == "daily_report":
                result = await loop.run_in_executor(None, self.copilot.daily_report)
                # TODO: 推送报告
        elif ctx.trigger_type == TriggerType.EVENT:
            await loop.run_in_executor(None, self.copilot.agent.chat,
                f"事件触发：{ctx.source}，请分析影响。")
        # ... 其他触发类型处理


class NoOpTriggerHub:
    """空操作触发中心（AI 禁用时使用）"""

    def fire(self, context) -> bool:                         return False
    def fire_scheduled(self, *a, **k) -> bool:               return False
    def fire_event(self, *a, **k) -> bool:                   return False
    def fire_request(self, *a, **k) -> bool:                 return False
    def fire_state(self, *a, **k) -> bool:                   return False
    def fire_message(self, *a, **k) -> bool:                 return False
    async def start(self):                                   pass
```

### 7.3 触发点埋设

```python
# 在常规服务的关键位置埋设触发点

from copilot.trigger_hub import get_trigger_hub

@app.put("/api/tasks/<id>/status")
def update_task_status(id):
    task.update(status=request.json.get("status"))
    if request.json.get("status") == "blocked":
        get_trigger_hub().fire_event("task_blocked", id, {"task_id": id})
    return jsonify(task.to_dict())

@app.post("/api/messages")
def post_message():
    msg = Message.create(request.json)
    get_trigger_hub().fire_message(msg.id, msg.content, msg.project_id)
    return jsonify(msg.to_dict())
```

---

## 8. 系统启动顺序

```python
# main.py — 系统统一入口

import os
import asyncio
import threading
import logging
from dotenv import load_dotenv

load_dotenv()
COPILOT_ENABLED = os.getenv("PM_COPILOT_ENABLED", "false").lower() == "true"

logger = logging.getLogger("system")

# ── 第1步：数据库初始化（两种模式都必须）──
from copilot.database import init_db
init_db()

# ── 第2步：创建 Web 应用（常规服务，零 AI 依赖）──
from copilot.web import create_app
app = create_app(ai_enabled=COPILOT_ENABLED)

if COPILOT_ENABLED:
    # ═══════════════════════════════════════════
    # 完整智能模式
    # ═══════════════════════════════════════════

    # 第3步：注册 PM 工具到引擎
    from copilot.tools import register_all_tools
    register_all_tools()

    # 第4步：注册 toolset
    from pm_copilot_engine.toolsets import TOOLSETS
    TOOLSETS["pm"] = {
        "description": "项目管理工具集",
        "tools": ["list_projects", "get_project_detail", "get_overdue_tasks",
                  "get_team_workload", "search_messages", "create_risk_alert",
                  "get_project_metrics", "update_task_status"],
        "includes": [],
    }

    # 第5步：创建 Copilot 本体
    from copilot.scheduler import PMCopilot, CopilotScheduler
    from copilot.trigger_hub import TriggerHub
    copilot = PMCopilot()
    trigger_hub = TriggerHub(copilot)

    # 第6步：启动调度器
    scheduler = CopilotScheduler(copilot, trigger_hub)
    scheduler.start()

    # 第7步：启动触发中心消费者
    trigger_thread = threading.Thread(
        target=lambda: asyncio.run(trigger_hub.start()),
        daemon=True
    )
    trigger_thread.start()

    # 第8步：注入 Web 应用
    app.state.copilot = copilot
    app.state.trigger_hub = trigger_hub
    app.state.ai_enabled = True

    logger.info("PM Copilot enabled. Running in full intelligence mode.")

else:
    # ═══════════════════════════════════════════
    # 降级模式（常规管理）
    # ═══════════════════════════════════════════

    from copilot.trigger_hub import NoOpTriggerHub
    app.state.trigger_hub = NoOpTriggerHub()
    app.state.ai_enabled = False

    logger.info("PM Copilot disabled. Running in normal management mode.")

# ── 第9步：启动 Web 服务（两种模式共通）──
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8080)
```

---

## 9. 降级模式设计（AI 禁用时的系统行为）

### 9.1 NoOpTriggerHub

所有 `fire_*` 方法返回 `False`，不抛异常。触发点调用静默忽略。

### 9.2 Web 界面自适应

```python
# copilot/web/app.py

def create_app(ai_enabled: bool = False):
    app = FastAPI()
    app.include_router(projects_router)
    app.include_router(tasks_router)
    app.include_router(messages_router)
    if ai_enabled:
        app.include_router(copilot_router)
        app.include_router(mcp_router)
    return app

@app.get("/api/system/config")
def get_system_config(request: Request):
    return {
        "ai_enabled": request.app.state.ai_enabled,
        "features": {
            "copilot_chat": request.app.state.ai_enabled,
            "ai_scan": request.app.state.ai_enabled,
            "risk_alert_auto": request.app.state.ai_enabled,
        }
    }
```

### 9.3 功能清单对比

| 功能 | AI 启用 | AI 禁用 |
|------|--------|--------|
| 项目/任务/团队 CRUD | ✅ | ✅ |
| 消息/讨论 | ✅ | ✅ |
| 风险告警（手动） | ✅ | ✅ |
| Copilot 问答面板 | ✅ | ❌ 隐藏 |
| 自动巡检 | ✅ | ❌ 不启动 |
| 智能风险识别 | ✅ | ❌ 不执行 |
| 自动日报/周报 | ✅ | ❌ 不启动 |
| 消息关键词触发 | ✅ | ❌ 不启动 |

---

## 10. 交互方式

### 10.1 自主运行

```
09:00  ┌─────────┐         09:30  ┌─────────┐
       │ 日报生成 │                │ 定时巡检 │
       └─────────┘                └─────────┘

触发：APScheduler → TriggerHub.fire_scheduled()
      → PMCopilot.scan() → AIAgent → 工具调用 → 业务操作
```

### 10.2 被动响应

```
用户 ──► Web ──► POST /api/copilot/ask
                  → trigger_hub.fire_request()
                  → PMCopilot.ask() → AIAgent → 工具调用
                  → WebSocket 推送回答
```

### 10.3 事件驱动

```
任务标记 blocked ──► DB UPDATE
                        │
                        ▼ SQLAlchemy 事件
                   trigger_hub.fire_event()
                        │
                        ▼
                   PMCopilot.agent.chat("任务X阻塞，分析影响...")
                        │
                        ▼
                   get_project_detail() → create_risk_alert()
                        │
                        ▼ WebSocket 推送
                   项目经理收到告警通知
```

---

## 11. 安全与权限

### 11.1 工具权限

- `enabled_toolsets=["pm"]`：Agent 只能调用 PM 工具
- 如需联网搜索：`enabled_toolsets=["pm", "web"]`
- 如需终端：`enabled_toolsets=["pm", "terminal"]`（谨慎）

### 11.2 写入安全

| 工具 | 写入类型 | 限制 |
|------|---------|------|
| `create_risk_alert` | INSERT | 只能写入 risk_alerts 表 |
| `update_task_status` | UPDATE | 只能修改 status 和 notes |

### 11.3 环境隔离

- 每个 Copilot 实例独立持有 AIAgent
- `max_iterations` 防止无限循环
- 数据库操作通过 ORM Session，支持事务回滚

---

## 12. 部署配置

### 12.1 环境变量

```bash
# AI 开关（核心）
PM_COPILOT_ENABLED=false                        # true=启用, false=禁用

# AI 模型（启用时需要）
ANTHROPIC_API_KEY=sk-ant-...
PM_MODEL=anthropic/claude-sonnet-4

# 数据库
DATABASE_URL=postgresql://user:pass@localhost/pm_db

# 调度
PM_SCAN_INTERVAL_MINUTES=30
PM_DAILY_REPORT_HOUR=9
PM_WEEKLY_REPORT_DAY=fri
PM_WEEKLY_REPORT_HOUR=17

# 触发
PM_COOLDOWN_SECONDS=60
PM_MESSAGE_KEYWORDS=阻塞,延期,风险,紧急,故障

# 通知
WEBHOOK_URL=https://your-company.com/webhook
```

### 12.2 引擎版本依赖

```toml
# your-pm-system/pyproject.toml

[project]
dependencies = [
    # 引擎依赖（PyPI 固定版本）
    "pm-copilot-engine>=0.1.0",

    # 业务依赖
    "fastapi>=0.100",
    "uvicorn[standard]",
    "sqlalchemy>=2.0",
    "apscheduler",
    "python-dotenv",
]
```

---

## 13. 演进路线

### Phase 1：感知（MVP）
- [ ] Fork hermes-agent，重命名为 `pm_copilot_engine`，裁剪后发 PyPI
- [ ] 完成 `copilot/tools.py` 全部工具 + `register_all_tools()`
- [ ] 完成 `copilot/models.py` ORM 模型
- [ ] PMCopilot 支持 `scan()` 和 `daily_report()`
- [ ] TriggerHub 支持时间触发和事件触发
- [ ] Web 界面基础 CRUD + Copilot 问答

### Phase 2：行动
- [ ] `create_risk_alert` 自动推送企业微信/钉钉
- [ ] `update_task_status` 智能推进
- [ ] 消息关键词触发 Copilot 分析
- [ ] 周报自动生成与推送

### Phase 3：多 Copilot 协作
- [ ] DevCopilot：技术债务、代码审查联动
- [ ] OpsCopilot：部署监控、故障响应
- [ ] PMCopilot：统筹协调

### Phase 4：进化
- [ ] Copilot 间对话能力
- [ ] 基于历史数据的预测能力
- [ ] 自主优化巡检策略

---

## 附录：术语表

| 术语 | 定义 |
|------|------|
| **pm-copilot-engine** | 从 Hermes 萃取的 AI 引擎，PyPI 包名，提供 LLM 调度、工具注册、对话循环 |
| **pm_copilot_engine** | Python 包名（下划线），`import pm_copilot_engine` |
| **AIAgent** | 引擎核心类，管理 LLM 对话、工具调用循环 |
| **registry** | 引擎全局工具注册表，业务层通过它注册工具 |
| **TOOLSETS** | 引擎工具集合字典，业务层运行时注入 `"pm"` toolset |
| **PMCopilot** | 项目管理常驻智能主理人，持有 AIAgent |
| **TriggerHub** | 触发决策中心，决定何时唤醒 Copilot |
| **NoOpTriggerHub** | AI 禁用时的空实现，保证触发点不报错 |
| **register_all_tools()** | 业务层函数，将 PM 工具注册到引擎 registry |
