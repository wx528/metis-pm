# Metis PM v2.0 精简重构 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Metis PM 从 v1.4.0 "大而全的 PM 工具"精简为 v2.0 "AI Agent 协作中枢"，用多个 pm-copilot-engine 容器替代 MCP Server + Copilot + A2A。

**Architecture:** 6 个 Docker 容器 — backend(纯 CRUD + SQLite)、frontend(精简 SPA)、agent/mate/tester/registrar(各一个 pm-copilot-engine 容器，自带 MCP 协议，通过 httpx 调 Backend REST API)。

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 async, SQLite, React 19, TypeScript, Ant Design 6, pm-copilot-engine, Docker Compose

---

## 文件结构总览

```
wt-main/
├── agents/                          # [新增] Agent 容器目录
│   ├── Dockerfile
│   ├── agent/{main.py,tools.py,system_prompt.md}
│   ├── mate/{main.py,tools.py,system_prompt.md}
│   ├── tester/{main.py,tools.py,system_prompt.md}
│   └── registrar/{main.py,tools.py,system_prompt.md}
├── backend/
│   ├── main.py                      # [修改] 精简 lifespan
│   ├── pyproject.toml               # [修改] 移除 mcp/copilot 依赖
│   ├── Dockerfile                   # [修改] 移除 uv 依赖
│   └── src/
│       ├── settings.py              # [修改] 移除 A2A/Copilot 配置
│       ├── core/
│       │   ├── database.py          # [保留]
│       │   ├── dependencies.py      # [修改] API Key 认证
│       │   └── notification.py      # [修改] 极简版，无 SSE
│       ├── models/
│       │   ├── __init__.py          # [修改] 只导出 6 个模型
│       │   ├── project.py           # [修改] 精简字段
│       │   ├── issue.py             # [修改] 精简字段
│       │   ├── comment.py           # [修改] 精简字段
│       │   ├── plan.py              # [修改] 精简字段
│       │   ├── plan_item.py         # [保留]
│       │   └── notification.py      # [修改] 极简版
│       ├── schemas/
│       │   ├── __init__.py          # [修改]
│       │   ├── project.py           # [修改]
│       │   ├── issue.py             # [修改]
│       │   ├── comment.py           # [修改]
│       │   ├── plan.py              # [修改]
│       │   ├── plan_item.py         # [修改]
│       │   └── notification.py      # [修改]
│       └── routes/
│           ├── __init__.py          # [修改] 只注册 6 个路由
│           ├── auth.py              # [修改] API Key 认证
│           ├── projects.py          # [修改] 移除 Milestone/Server 引用
│           ├── issues.py            # [修改] 移除 milestone/defer/trigger/workflow 逻辑
│           ├── plans.py             # [修改] 移除 milestone/workflow 逻辑
│           ├── comments.py          # [修改] 精简
│           └── notifications.py     # [修改] 移除 SSE，极简 REST
├── frontend/src/
│   ├── App.tsx                      # [修改] 精简路由
│   ├── api/
│   │   ├── client.ts               # [修改] API Key 认证
│   │   ├── index.ts                # [修改] 只导出 6 个模块
│   │   ├── issues.ts               # [修改] 精简类型
│   │   ├── plans.ts                # [修改] 精简类型
│   │   ├── projects.ts             # [修改]
│   │   ├── notifications.ts        # [修改]
│   │   └── auth.ts                 # [修改] API Key 登录
│   ├── pages/
│   │   ├── Dashboard.tsx           # [修改] 极简版
│   │   ├── Issues.tsx              # [修改] 移除 milestone 筛选
│   │   ├── IssueDetail.tsx         # [修改] 移除 milestone/defer
│   │   ├── Plans.tsx               # [修改] 精简
│   │   └── PlanDetail.tsx          # [修改] 精简
│   ├── components/
│   │   ├── Layout.tsx              # [修改] 精简菜单
│   │   ├── IssueCard.tsx           # [修改] 移除 source icons
│   │   └── PlanItem.tsx            # [保留]
│   ├── hooks/
│   │   ├── useAuth.tsx             # [修改] API Key 认证
│   │   └── useProject.tsx          # [修改]
│   └── types/
│       └── index.ts                # [新增] 集中类型定义
├── docker-compose.yml              # [修改] 6 个服务
├── .env.example                    # [修改] 精简配置
├── Makefile                        # [修改] 精简命令
└── CHANGELOG.md                    # [修改]

---

## Phase 1: Backend 模型精简

### Task 1.1: 精简 Project 模型

**Files:**
- Modify: `backend/src/models/project.py`

- [ ] **Step 1: 重写 project.py，移除不需要的字段和关系**

```python
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship

from src.core.database import Base, EnumColumn


class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(EnumColumn(ProjectStatus), default=ProjectStatus.ACTIVE)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    issues = relationship("Issue", back_populates="project", foreign_keys="Issue.project_id")
    plans = relationship("Plan", back_populates="project", foreign_keys="Plan.project_id")
    notifications = relationship("Notification", foreign_keys="Notification.project_id")
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/models/project.py
git commit -m "refactor: simplify Project model - remove repo_url, owner, default_milestone_id, server/milestone relationships"
```

---

### Task 1.2: 精简 Issue 模型

**Files:**
- Modify: `backend/src/models/issue.py`

- [ ] **Step 1: 重写 issue.py**

```python
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base, EnumColumn


class IssueType(str, enum.Enum):
    BUG = "bug"
    FEATURE = "feature"
    TASK = "task"


class IssueStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IssuePriority(str, enum.Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    issue_type = Column(EnumColumn(IssueType), default=IssueType.TASK, nullable=False)
    status = Column(EnumColumn(IssueStatus), default=IssueStatus.OPEN, nullable=False)
    priority = Column(EnumColumn(IssuePriority), default=IssuePriority.P2, nullable=False)
    assignee_role = Column(String(50), nullable=True)
    source_role = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="issues", foreign_keys=[project_id])
    comments = relationship("Comment", back_populates="issue", cascade="all, delete-orphan")
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/models/issue.py
git commit -m "refactor: simplify Issue model - remove milestone, source enum, labels, parent, deferred fields"
```

---

### Task 1.3: 精简 Comment 模型

**Files:**
- Modify: `backend/src/models/comment.py`

- [ ] **Step 1: 重写 comment.py**

```python
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    author_role = Column(String(50), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    issue = relationship("Issue", back_populates="comments")
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/models/comment.py
git commit -m "refactor: simplify Comment model - remove parent_id, comment_type, read_by, read_at"
```

---

### Task 1.4: 精简 Plan 模型

**Files:**
- Modify: `backend/src/models/plan.py`

- [ ] **Step 1: 重写 plan.py**

```python
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base, EnumColumn


class PlanStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(EnumColumn(PlanStatus), default=PlanStatus.PENDING)
    proposed_by = Column(String(50), nullable=True)
    approved_by = Column(String(50), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    reject_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="plans", foreign_keys=[project_id])
    plan_items = relationship("PlanItem", back_populates="plan", cascade="all, delete-orphan", order_by="PlanItem.sort_order")
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/models/plan.py
git commit -m "refactor: simplify Plan model - remove PlanSource enum, proposed_by_name, current_milestone_id"
```

---

### Task 1.5: 精简 Notification 模型

**Files:**
- Modify: `backend/src/models/notification.py`

- [ ] **Step 1: 重写 notification.py**

```python
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    target_role = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", foreign_keys=[project_id])
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/models/notification.py
git commit -m "refactor: simplify Notification model - target_role, message, is_read only"
```

---

### Task 1.6: 更新 models/__init__.py

**Files:**
- Modify: `backend/src/models/__init__.py`

- [ ] **Step 1: 重写 __init__.py，只导出 6 个模型**

```python
from src.core.database import Base
from src.models.project import Project, ProjectStatus
from src.models.issue import Issue, IssueType, IssueStatus, IssuePriority
from src.models.comment import Comment
from src.models.plan import Plan, PlanStatus
from src.models.plan_item import PlanItem, PlanItemStatus
from src.models.notification import Notification

__all__ = [
    "Base",
    "Project", "ProjectStatus",
    "Issue", "IssueType", "IssueStatus", "IssuePriority",
    "Comment",
    "Plan", "PlanStatus",
    "PlanItem", "PlanItemStatus",
    "Notification",
]
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/models/__init__.py
git commit -m "refactor: update models __init__ to export only 6 models"
```

---

## Phase 2: Backend Schema 精简

### Task 2.1: 精简 Project Schema

**Files:**
- Modify: `backend/src/schemas/project.py`

- [ ] **Step 1: 重写 project.py**

```python
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ProjectRead(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectReadWithStats(ProjectRead):
    issue_count: int = 0
    open_issue_count: int = 0
    plan_count: int = 0
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/schemas/project.py
git commit -m "refactor: simplify Project schemas"
```

---

### Task 2.2: 精简 Issue Schema

**Files:**
- Modify: `backend/src/schemas/issue.py`

- [ ] **Step 1: 重写 issue.py**

```python
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class IssueCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    issue_type: str = Field(default="task")
    priority: str = Field(default="P2")
    assignee_role: Optional[str] = None
    source_role: Optional[str] = None
    project_id: Optional[int] = None


class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    issue_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_role: Optional[str] = None


class IssueRead(BaseModel):
    id: int
    project_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    issue_type: str
    status: str
    priority: str
    assignee_role: Optional[str] = None
    source_role: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IssueReadWithComments(IssueRead):
    comments: List["CommentRead"] = []


class IssueListResponse(BaseModel):
    total: int
    items: List[IssueRead]
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/schemas/issue.py
git commit -m "refactor: simplify Issue schemas"
```

---

### Task 2.3: 精简 Comment Schema

**Files:**
- Modify: `backend/src/schemas/comment.py`

- [ ] **Step 1: 重写 comment.py**

```python
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    author_role: Optional[str] = None


class CommentRead(BaseModel):
    id: int
    issue_id: int
    author_role: Optional[str] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/schemas/comment.py
git commit -m "refactor: simplify Comment schemas"
```

---

### Task 2.4: 精简 Plan Schema

**Files:**
- Modify: `backend/src/schemas/plan.py`

- [ ] **Step 1: 重写 plan.py**

```python
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class PlanCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    proposed_by: Optional[str] = None
    project_id: Optional[int] = None


class PlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class PlanRead(BaseModel):
    id: int
    project_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: str
    proposed_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlanReadWithItems(PlanRead):
    plan_items: List["PlanItemRead"] = []


class PlanReadWithStats(PlanRead):
    item_count: int = 0
    item_done_count: int = 0


class PlanItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    sort_order: int = 0


class PlanItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None
    completed_by: Optional[str] = None


class PlanItemRead(BaseModel):
    id: int
    plan_id: int
    title: str
    description: Optional[str] = None
    status: str
    sort_order: int
    completed_by: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/schemas/plan.py
git commit -m "refactor: simplify Plan schemas"
```

---

### Task 2.5: 精简 Notification Schema

**Files:**
- Modify: `backend/src/schemas/notification.py`

- [ ] **Step 1: 重写 notification.py**

```python
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: int
    target_role: str
    message: str
    is_read: bool
    project_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    total: int
    items: List[NotificationRead]


class UnreadCountResponse(BaseModel):
    count: int
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/schemas/notification.py
git commit -m "refactor: simplify Notification schemas"
```

---

### Task 2.6: 更新 schemas/__init__.py

**Files:**
- Modify: `backend/src/schemas/__init__.py`

- [ ] **Step 1: 重写 __init__.py**

```python
from src.schemas.project import ProjectCreate, ProjectUpdate, ProjectRead, ProjectReadWithStats
from src.schemas.issue import IssueCreate, IssueUpdate, IssueRead, IssueReadWithComments, IssueListResponse
from src.schemas.comment import CommentCreate, CommentRead
from src.schemas.plan import (
    PlanCreate, PlanUpdate, PlanRead, PlanReadWithItems, PlanReadWithStats,
    PlanItemCreate, PlanItemUpdate, PlanItemRead,
)
from src.schemas.notification import NotificationRead, NotificationListResponse, UnreadCountResponse
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/schemas/__init__.py
git commit -m "refactor: update schemas __init__"
```

---

## Phase 3: Backend 路由精简

### Task 3.1: 重写 auth.py — API Key 认证

**Files:**
- Modify: `backend/src/routes/auth.py`

- [ ] **Step 1: 重写 auth.py**

```python
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.settings import settings

router = APIRouter()
security = HTTPBearer(auto_error=False)


async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    api_key = request.headers.get("X-API-Key")
    if api_key and api_key == settings.API_KEY:
        return {"sub": "admin", "role": "admin"}
    if credentials:
        token = credentials.credentials
        identity = settings.resolve_identity(token)
        if identity:
            sub, role = identity
            return {"sub": sub, "role": role}
    raise HTTPException(status_code=401, detail="Invalid credentials")


def require_role(*allowed_roles: str):
    def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed_roles:
            roles_str = "/".join(allowed_roles)
            raise HTTPException(status_code=403, detail=f"{roles_str} role required")
        return user
    return _checker


@router.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/routes/auth.py
git commit -m "refactor: simplify auth to API Key + agent password dual auth"
```

---

### Task 3.2: 重写 projects.py

**Files:**
- Modify: `backend/src/routes/projects.py`

- [ ] **Step 1: 重写 projects.py，移除 Milestone/Server 引用**

```python
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.core.dependencies import get_db
from src.models.project import Project, ProjectStatus
from src.models.issue import Issue, IssueStatus
from src.models.plan import Plan
from src.schemas.project import ProjectCreate, ProjectUpdate, ProjectRead, ProjectReadWithStats
from src.routes.auth import get_current_user, require_role

router = APIRouter(dependencies=[Depends(get_current_user)])


async def _get_project_by_slug(db: AsyncSession, slug: str) -> Project:
    result = await db.execute(select(Project).where(Project.slug == slug))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{slug}' not found")
    return project


@router.get("", response_model=list[ProjectReadWithStats])
async def list_projects(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Project)
    if status:
        query = query.where(Project.status == status)
    query = query.order_by(Project.created_at.desc())
    result = await db.execute(query)
    projects = result.scalars().all()

    response = []
    for p in projects:
        issue_count = (await db.execute(
            select(func.count(Issue.id)).where(Issue.project_id == p.id)
        )).scalar() or 0
        open_issue_count = (await db.execute(
            select(func.count(Issue.id)).where(
                Issue.project_id == p.id,
                Issue.status.in_([IssueStatus.OPEN, IssueStatus.IN_PROGRESS])
            )
        )).scalar() or 0
        plan_count = (await db.execute(
            select(func.count(Plan.id)).where(Plan.project_id == p.id)
        )).scalar() or 0
        response.append(ProjectReadWithStats(
            id=p.id, name=p.name, slug=p.slug, description=p.description,
            status=p.status, created_at=p.created_at, updated_at=p.updated_at,
            issue_count=issue_count, open_issue_count=open_issue_count, plan_count=plan_count,
        ))
    return response


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "agent"))):
    existing = await db.execute(select(Project).where(Project.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Project slug '{data.slug}' already exists")
    project = Project(**data.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{slug}", response_model=ProjectReadWithStats)
async def get_project(slug: str, db: AsyncSession = Depends(get_db)):
    project = await _get_project_by_slug(db, slug)
    issue_count = (await db.execute(select(func.count(Issue.id)).where(Issue.project_id == project.id))).scalar() or 0
    open_issue_count = (await db.execute(select(func.count(Issue.id)).where(Issue.project_id == project.id, Issue.status.in_([IssueStatus.OPEN, IssueStatus.IN_PROGRESS])))).scalar() or 0
    plan_count = (await db.execute(select(func.count(Plan.id)).where(Plan.project_id == project.id))).scalar() or 0
    return ProjectReadWithStats(
        id=project.id, name=project.name, slug=project.slug, description=project.description,
        status=project.status, created_at=project.created_at, updated_at=project.updated_at,
        issue_count=issue_count, open_issue_count=open_issue_count, plan_count=plan_count,
    )


@router.put("/{slug}", response_model=ProjectRead)
async def update_project(slug: str, data: ProjectUpdate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "agent"))):
    project = await _get_project_by_slug(db, slug)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{slug}", status_code=204)
async def delete_project(slug: str, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin"))):
    project = await _get_project_by_slug(db, slug)
    issue_count = (await db.execute(select(func.count(Issue.id)).where(Issue.project_id == project.id))).scalar() or 0
    plan_count = (await db.execute(select(func.count(Plan.id)).where(Plan.project_id == project.id))).scalar() or 0
    if issue_count or plan_count:
        raise HTTPException(status_code=409, detail="Cannot delete project with existing issues or plans")
    await db.delete(project)
    await db.commit()
    return None
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/routes/projects.py
git commit -m "refactor: simplify projects route - remove activity log, milestone/server refs"
```

---

### Task 3.3: 重写 issues.py

**Files:**
- Modify: `backend/src/routes/issues.py`

- [ ] **Step 1: 重写 issues.py，移除 milestone/defer/trigger/workflow/metrics**

```python
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc
from sqlalchemy.orm import selectinload

from src.core.dependencies import get_db
from src.core.notification import create_notification
from src.models.issue import Issue, IssueType, IssueStatus, IssuePriority
from src.models.comment import Comment
from src.schemas.issue import IssueCreate, IssueUpdate, IssueRead, IssueReadWithComments, IssueListResponse
from src.schemas.comment import CommentCreate, CommentRead
from src.routes.auth import get_current_user, require_role

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=IssueListResponse)
async def list_issues(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    project_id: Optional[int] = Query(None),
    issue_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assignee_role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at_desc"),
):
    query = select(Issue)
    if project_id:
        query = query.where(Issue.project_id == project_id)
    if issue_type:
        query = query.where(Issue.issue_type == issue_type)
    if status:
        query = query.where(Issue.status == status)
    if priority:
        query = query.where(Issue.priority == priority)
    if assignee_role:
        query = query.where(Issue.assignee_role == assignee_role)
    if search:
        query = query.where(Issue.title.contains(search, autoescape=True))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    sort_map = {
        "created_at_desc": desc(Issue.created_at),
        "created_at_asc": asc(Issue.created_at),
        "updated_at_desc": desc(Issue.updated_at),
        "priority_asc": asc(Issue.priority),
        "priority_desc": desc(Issue.priority),
    }
    order_clause = sort_map.get(sort_by, desc(Issue.created_at))
    query = query.order_by(order_clause).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()
    return {"total": total, "items": items}


@router.post("", response_model=IssueRead, status_code=201)
async def create_issue(data: IssueCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "agent", "tester"))):
    issue = Issue(**data.model_dump())
    db.add(issue)
    await db.commit()
    await db.refresh(issue)

    if issue.priority in (IssuePriority.P0, IssuePriority.P1):
        await create_notification(
            db, target_role="admin",
            message=f"[{issue.priority}] {issue.title}",
            project_id=issue.project_id,
        )
    return issue


@router.get("/{issue_id}", response_model=IssueReadWithComments)
async def get_issue(issue_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Issue).where(Issue.id == issue_id).options(selectinload(Issue.comments))
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.put("/{issue_id}", response_model=IssueRead)
async def update_issue(issue_id: int, data: IssueUpdate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(issue, key, value)

    await db.commit()
    await db.refresh(issue)

    if update_data.get("status") == IssueStatus.CLOSED:
        await create_notification(
            db, target_role="admin",
            message=f"Issue #{issue.id} closed: {issue.title}",
            project_id=issue.project_id,
        )
    return issue


@router.delete("/{issue_id}", status_code=204)
async def delete_issue(issue_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin"))):
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    await db.delete(issue)
    await db.commit()
    return None


@router.get("/{issue_id}/comments", response_model=List[CommentRead])
async def list_comments(issue_id: int, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Comment).where(Comment.issue_id == issue_id).order_by(asc(Comment.created_at)).offset(offset).limit(limit)
    )
    return result.scalars().all()


@router.post("/{issue_id}/comments", response_model=CommentRead, status_code=201)
async def add_comment(issue_id: int, data: CommentCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    comment = Comment(issue_id=issue_id, **data.model_dump())
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/routes/issues.py
git commit -m "refactor: simplify issues route - remove milestone/defer/trigger/workflow/metrics"
```

---

### Task 3.4: 重写 plans.py

**Files:**
- Modify: `backend/src/routes/plans.py`

- [ ] **Step 1: 重写 plans.py，移除 milestone/workflow/activity 逻辑**

```python
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, case
from sqlalchemy.orm import selectinload

from src.core.dependencies import get_db
from src.core.notification import create_notification
from src.models.plan import Plan, PlanStatus
from src.models.plan_item import PlanItem, PlanItemStatus
from src.schemas.plan import (
    PlanCreate, PlanUpdate, PlanRead, PlanReadWithItems, PlanReadWithStats,
    PlanItemCreate, PlanItemUpdate, PlanItemRead,
)
from src.routes.auth import get_current_user, require_role

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=List[PlanReadWithStats])
async def list_plans(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
):
    query = select(Plan).order_by(desc(Plan.created_at))
    if status:
        query = query.where(Plan.status == status)
    if project_id:
        query = query.where(Plan.project_id == project_id)
    result = await db.execute(query)
    plans = result.scalars().all()

    out = []
    for p in plans:
        stats = await db.execute(
            select(
                func.count(PlanItem.id).label("total"),
                func.sum(case((PlanItem.status == PlanItemStatus.DONE, 1), else_=0)).label("done"),
            ).where(PlanItem.plan_id == p.id)
        )
        row = stats.one()
        out.append(PlanReadWithStats(
            id=p.id, project_id=p.project_id, title=p.title, description=p.description,
            status=p.status, proposed_by=p.proposed_by, approved_by=p.approved_by,
            approved_at=p.approved_at, reject_reason=p.reject_reason,
            created_at=p.created_at, updated_at=p.updated_at,
            item_count=row.total or 0, item_done_count=row.done or 0,
        ))
    return out


@router.post("", response_model=PlanRead, status_code=201)
async def create_plan(data: PlanCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "agent"))):
    plan = Plan(**data.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    if plan.status == PlanStatus.PENDING:
        await create_notification(
            db, target_role="mate",
            message=f"Plan #{plan.id} waiting approval: {plan.title}",
            project_id=plan.project_id,
        )
    return plan


@router.get("/{plan_id}", response_model=PlanReadWithItems)
async def get_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id).options(selectinload(Plan.plan_items))
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.put("/{plan_id}", response_model=PlanRead)
async def update_plan(plan_id: int, data: PlanUpdate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "agent"))):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(plan, key, value)

    await db.commit()
    await db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(plan_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin"))):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    await db.delete(plan)
    await db.commit()
    return None


@router.post("/{plan_id}/approve", response_model=PlanRead)
async def approve_plan(plan_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "mate"))):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != PlanStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending plans can be approved")

    plan.status = PlanStatus.APPROVED
    plan.approved_by = user["sub"]
    plan.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(plan)

    await create_notification(
        db, target_role=plan.proposed_by or "agent",
        message=f"Plan #{plan.id} approved: {plan.title}",
        project_id=plan.project_id,
    )
    return plan


@router.post("/{plan_id}/reject", response_model=PlanRead)
async def reject_plan(plan_id: int, reason: Optional[str] = Body(None, embed=True), db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "mate"))):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != PlanStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending plans can be rejected")

    plan.status = PlanStatus.REJECTED
    plan.reject_reason = reason
    await db.commit()
    await db.refresh(plan)

    await create_notification(
        db, target_role=plan.proposed_by or "agent",
        message=f"Plan #{plan.id} rejected: {plan.title} - {reason or 'no reason'}",
        project_id=plan.project_id,
    )
    return plan


@router.get("/{plan_id}/items", response_model=List[PlanItemRead])
async def list_plan_items(plan_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PlanItem).where(PlanItem.plan_id == plan_id).order_by(PlanItem.sort_order)
    )
    return result.scalars().all()


@router.post("/{plan_id}/items", response_model=PlanItemRead, status_code=201)
async def create_plan_item(plan_id: int, data: PlanItemCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "agent"))):
    plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    item = PlanItem(plan_id=plan_id, **data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.put("/{plan_id}/items/{item_id}", response_model=PlanItemRead)
async def update_plan_item(plan_id: int, item_id: int, data: PlanItemUpdate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin", "agent"))):
    result = await db.execute(
        select(PlanItem).where(PlanItem.id == item_id, PlanItem.plan_id == plan_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="PlanItem not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{plan_id}/items/{item_id}", status_code=204)
async def delete_plan_item(plan_id: int, item_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(require_role("admin"))):
    result = await db.execute(
        select(PlanItem).where(PlanItem.id == item_id, PlanItem.plan_id == plan_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="PlanItem not found")
    await db.delete(item)
    await db.commit()
    return None
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/routes/plans.py
git commit -m "refactor: simplify plans route - remove milestone/workflow/activity logic"
```

---

### Task 3.5: 重写 comments.py

**Files:**
- Modify: `backend/src/routes/comments.py`

- [ ] **Step 1: 重写 comments.py**

```python
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.core.dependencies import get_db
from src.routes.auth import get_current_user
from src.models.comment import Comment
from src.schemas.comment import CommentRead

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[CommentRead])
async def list_comments(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Comment).order_by(desc(Comment.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/routes/comments.py
git commit -m "refactor: simplify comments route"
```

---

### Task 3.6: 重写 notifications.py

**Files:**
- Modify: `backend/src/routes/notifications.py`

- [ ] **Step 1: 重写 notifications.py，移除 SSE**

```python
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update, delete

from src.core.dependencies import get_db
from src.models.notification import Notification
from src.schemas.notification import NotificationRead, NotificationListResponse, UnreadCountResponse
from src.routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    project_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    role = user.get("role", "")
    query = select(Notification).where(
        Notification.target_role.in_([role, "all"])
    )
    if unread_only:
        query = query.where(Notification.is_read == False)
    if project_id is not None:
        query = query.where(Notification.project_id == project_id)
    query = query.order_by(desc(Notification.created_at))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    result = await db.execute(query.offset(skip).limit(limit))
    items = result.scalars().all()
    return {"total": total, "items": items}


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    role = user.get("role", "")
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.target_role.in_([role, "all"]),
            Notification.is_read == False,
        )
    )
    return {"count": result.scalar() or 0}


@router.put("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(notification_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification


@router.put("/read-all", status_code=204)
async def mark_all_read(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    role = user.get("role", "")
    await db.execute(
        update(Notification)
        .where(Notification.target_role.in_([role, "all"]), Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return None
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/routes/notifications.py
git commit -m "refactor: simplify notifications route - remove SSE, use role-based filtering"
```

---

### Task 3.7: 重写 routes/__init__.py

**Files:**
- Modify: `backend/src/routes/__init__.py`

- [ ] **Step 1: 重写 __init__.py，只注册 6 个路由**

```python
from fastapi import APIRouter

from src.routes import auth, projects, issues, plans, comments, notifications

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(projects.router, prefix="/projects", tags=["项目管理"])
api_router.include_router(issues.router, prefix="/issues", tags=["问题管理"])
api_router.include_router(plans.router, prefix="/plans", tags=["计划管理"])
api_router.include_router(comments.router, prefix="/issue-comments", tags=["评论管理"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["通知"])
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/routes/__init__.py
git commit -m "refactor: routes __init__ - only 6 route modules"
```

---

## Phase 4: Backend 核心基础设施精简

### Task 4.1: 重写 core/notification.py

**Files:**
- Modify: `backend/src/core/notification.py`

- [ ] **Step 1: 重写 notification.py 为极简版**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.notification import Notification


async def create_notification(
    db: AsyncSession,
    target_role: str,
    message: str,
    project_id: int | None = None,
):
    notification = Notification(
        target_role=target_role,
        message=message,
        project_id=project_id,
    )
    db.add(notification)
    await db.commit()
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/core/notification.py
git commit -m "refactor: simplify notification.py - remove SSE, just DB write"
```

---

### Task 4.2: 重写 core/dependencies.py

**Files:**
- Modify: `backend/src/core/dependencies.py`

- [ ] **Step 1: 重写 dependencies.py**

```python
from src.core.database import AsyncSessionLocal


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/core/dependencies.py
git commit -m "refactor: simplify dependencies.py"
```

---

### Task 4.3: 更新 settings.py

**Files:**
- Modify: `backend/src/settings.py`

- [ ] **Step 1: 移除 A2A/Copilot 相关配置**

Read the current settings.py first, then remove:
- `PM_COPILOT_ENABLED`, `PM_MODEL`, `PM_API_BASE_URL`, `PM_API_KEY` 
- `A2A_ENABLED`, `A2A_HOST`, `A2A_PORT`, `A2A_AGENT_CARD_URL`
- `ENCRYPTION_KEY`
- `api_token_map`

Keep only: `SECRET_KEY`, `ADMIN_PASSWORD_HASH`, `AGENT_PASSWORDS_JSON`, `API_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, `DEBUG`, `resolve_identity()`

Add new `API_KEY` setting:
```python
API_KEY: str = Field(default="metis-pm-default-key-change-me", alias="API_KEY")
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/settings.py
git commit -m "refactor: simplify settings - remove A2A/Copilot/Encryption config, add API_KEY"
```

---

### Task 4.4: 精简 main.py

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: 重写 main.py**

```python
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.database import engine, Base
from src.routes import api_router
from src.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Metis PM",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Commit**

```bash
git add backend/main.py
git commit -m "refactor: simplify main.py - remove migrations, copilot, a2a, mcp, metrics"
```

---

### Task 4.5: 更新 pyproject.toml

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: 移除不需要的依赖**

Remove from dependencies:
- `mcp>=1.12`
- `prometheus-client>=0.20`
- `prometheus-fastapi-instrumentator>=7.0`
- `cryptography>=42.0`
- `requests>=2.32`

Remove optional dependencies:
- `copilot` group (pm-copilot-engine)
- `postgres` group

Remove scripts:
- `metis-pm-mcp`

- [ ] **Step 2: Commit**

```bash
git add backend/pyproject.toml
git commit -m "refactor: simplify pyproject.toml - remove mcp/copilot/prometheus deps"
```

---

### Task 4.6: 删除不需要的文件

**Files:**
- Delete: `backend/copilot/` (entire directory)
- Delete: `backend/src/a2a/` (entire directory)
- Delete: `backend/mcp_server_unified.py`
- Delete: `backend/mcp_tools/` (entire directory)
- Delete: `backend/mcp_common.py`
- Delete: `backend/mcp_server.py`
- Delete: `backend/mcp_server_mate.py`
- Delete: `backend/mcp_server_tester.py`
- Delete: `backend/src/core/crypto.py`
- Delete: `backend/src/core/message_queue.py`
- Delete: `backend/src/core/workflow_engine.py`
- Delete: `backend/src/core/workflow_timeout.py`
- Delete: `backend/src/core/trigger_hub.py`
- Delete: `backend/src/core/metrics.py`
- Delete: `backend/src/core/rate_limit.py`
- Delete: `backend/src/core/debounce.py`
- Delete: `backend/src/core/webhook_handler.py`
- Delete: `backend/src/core/activity.py`
- Delete: `backend/src/models/milestone.py`
- Delete: `backend/src/models/server.py`
- Delete: `backend/src/models/workflow.py`
- Delete: `backend/src/models/agent_memory.py`
- Delete: `backend/src/models/project_registration.py`
- Delete: `backend/src/models/feedback.py`
- Delete: `backend/src/models/git_integration.py`
- Delete: `backend/src/models/risk_alert.py`
- Delete: `backend/src/models/activity_log.py`
- Delete: `backend/src/schemas/milestone.py`
- Delete: `backend/src/schemas/server.py`
- Delete: `backend/src/schemas/workflow.py`
- Delete: `backend/src/schemas/agent_memory.py`
- Delete: `backend/src/schemas/project_registration.py`
- Delete: `backend/src/schemas/feedback.py`
- Delete: `backend/src/schemas/git_integration.py`
- Delete: `backend/src/schemas/risk_alert.py`
- Delete: `backend/src/schemas/activity_log.py`
- Delete: `backend/src/routes/milestones.py`
- Delete: `backend/src/routes/servers.py`
- Delete: `backend/src/routes/workflows.py`
- Delete: `backend/src/routes/agent_memory.py`
- Delete: `backend/src/routes/project_registrations.py`
- Delete: `backend/src/routes/feedback.py`
- Delete: `backend/src/routes/risk_alerts.py`
- Delete: `backend/src/routes/activity_logs.py`
- Delete: `backend/src/routes/copilot.py`
- Delete: `backend/src/routes/dashboard.py`
- Delete: `backend/src/routes/graph.py`
- Delete: `backend/src/routes/git_webhook.py`
- Delete: `backend/src/routes/external_api.py`
- Delete: `backend/src/routes/stats.py`
- Delete: `backend/src/routes/agent_status.py`
- Delete: `backend/src/routes/monitoring.py`

- [ ] **Step 1: Delete all files**

```bash
Remove-Item -Recurse -Force backend/copilot
Remove-Item -Recurse -Force backend/src/a2a
Remove-Item -Recurse -Force backend/mcp_tools
Remove-Item -Force backend/mcp_server_unified.py, backend/mcp_common.py, backend/mcp_server.py, backend/mcp_server_mate.py, backend/mcp_server_tester.py
Remove-Item -Force backend/src/core/crypto.py, backend/src/core/message_queue.py, backend/src/core/workflow_engine.py, backend/src/core/workflow_timeout.py, backend/src/core/trigger_hub.py, backend/src/core/metrics.py, backend/src/core/rate_limit.py, backend/src/core/debounce.py, backend/src/core/webhook_handler.py, backend/src/core/activity.py
Remove-Item -Force backend/src/models/milestone.py, backend/src/models/server.py, backend/src/models/workflow.py, backend/src/models/agent_memory.py, backend/src/models/project_registration.py, backend/src/models/feedback.py, backend/src/models/git_integration.py, backend/src/models/risk_alert.py, backend/src/models/activity_log.py
Remove-Item -Force backend/src/schemas/milestone.py, backend/src/schemas/server.py, backend/src/schemas/workflow.py, backend/src/schemas/agent_memory.py, backend/src/schemas/project_registration.py, backend/src/schemas/feedback.py, backend/src/schemas/git_integration.py, backend/src/schemas/risk_alert.py, backend/src/schemas/activity_log.py
Remove-Item -Force backend/src/routes/milestones.py, backend/src/routes/servers.py, backend/src/routes/workflows.py, backend/src/routes/agent_memory.py, backend/src/routes/project_registrations.py, backend/src/routes/feedback.py, backend/src/routes/risk_alerts.py, backend/src/routes/activity_logs.py, backend/src/routes/copilot.py, backend/src/routes/dashboard.py, backend/src/routes/graph.py, backend/src/routes/git_webhook.py, backend/src/routes/external_api.py, backend/src/routes/stats.py, backend/src/routes/agent_status.py, backend/src/routes/monitoring.py
```

- [ ] **Step 2: Commit**

```bash
git add -A backend/
git commit -m "refactor: delete unused models, schemas, routes, core files, mcp, copilot, a2a"
```

---

### Task 4.7: 更新 Dockerfile

**Files:**
- Modify: `backend/Dockerfile`

- [ ] **Step 1: 重写 Dockerfile，移除 uv**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi uvicorn[standard] sqlalchemy[asyncio] aiosqlite pydantic pydantic-settings python-multipart python-dotenv pyjwt[crypto] httpx bcrypt

COPY . .

RUN groupadd -r pm && useradd -r -g pm -d /data -s /sbin/nologin pm
RUN mkdir -p /data && chown -R pm:pm /data

ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite+aiosqlite:////data/metis_pm.db

EXPOSE 8000

USER pm

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Commit**

```bash
git add backend/Dockerfile
git commit -m "refactor: simplify Dockerfile - remove uv, use pip directly"
```

---

## Phase 5: Agent 容器

### Task 5.1: 创建共享 Dockerfile

**Files:**
- Create: `agents/Dockerfile`

- [ ] **Step 1: 创建 agents/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pm-copilot-engine httpx

COPY main.py tools.py system_prompt.md ./

CMD ["python", "main.py"]
```

- [ ] **Step 2: Commit**

```bash
git add agents/Dockerfile
git commit -m "feat: add shared Agent Dockerfile"
```

---

### Task 5.2: 创建 Agent 容器

**Files:**
- Create: `agents/agent/main.py`
- Create: `agents/agent/tools.py`
- Create: `agents/agent/system_prompt.md`

- [ ] **Step 1: 创建 agents/agent/main.py**

```python
import os
from pm_copilot_engine import AIAgent, registry
from tools import register_tools

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/api/v1")
API_KEY = os.getenv("API_KEY", "metis-pm-default-key-change-me")
ROLE = "agent"

register_tools()

agent = AIAgent(
    model=os.getenv("PM_MODEL", "gpt-4o"),
    base_url=os.getenv("PM_API_BASE_URL"),
    api_key=os.getenv("PM_API_KEY"),
    system_prompt=open("system_prompt.md").read(),
    enabled_toolsets=["agent"],
)

if __name__ == "__main__":
    agent.run()
```

- [ ] **Step 2: 创建 agents/agent/tools.py**

```python
import os
import httpx
from pm_copilot_engine import registry

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/api/v1")
API_KEY = os.getenv("API_KEY", "metis-pm-default-key-change-me")
ROLE = "agent"

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


async def _api(method: str, path: str, **kwargs) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, f"{BACKEND_URL}{path}", headers=HEADERS, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}


@registry.tool(toolset="agent")
async def list_my_issues(project_id: int | None = None, status: str | None = None) -> str:
    """列出分配给我的 Issue。

    Args:
        project_id: 项目 ID（可选）
        status: 状态筛选 open/in_progress/resolved/closed（可选）
    """
    params = {"assignee_role": ROLE}
    if project_id:
        params["project_id"] = project_id
    if status:
        params["status"] = status
    result = await _api("GET", "/issues", params=params)
    items = result.get("items", [])
    if not items:
        return "没有分配给你的 Issue。"
    lines = [f"共 {result['total']} 个 Issue："]
    for i in items:
        lines.append(f"  #{i['id']} [{i['priority']}] {i['title']} ({i['status']})")
    return "\n".join(lines)


@registry.tool(toolset="agent")
async def get_issue(issue_id: int) -> str:
    """查看 Issue 详情。

    Args:
        issue_id: Issue ID
    """
    result = await _api("GET", f"/issues/{issue_id}")
    comments = result.get("comments", [])
    lines = [
        f"#{result['id']} {result['title']}",
        f"状态: {result['status']} | 优先级: {result['priority']} | 类型: {result['issue_type']}",
        f"描述: {result.get('description', '无')}",
    ]
    if comments:
        lines.append(f"\n评论 ({len(comments)}):")
        for c in comments:
            lines.append(f"  [{c['author_role']}] {c['content']}")
    return "\n".join(lines)


@registry.tool(toolset="agent")
async def update_issue_status(issue_id: int, status: str) -> str:
    """更新 Issue 状态。

    Args:
        issue_id: Issue ID
        status: 新状态 open/in_progress/resolved/closed
    """
    result = await _api("PUT", f"/issues/{issue_id}", json={"status": status})
    return f"Issue #{issue_id} 状态已更新为 {status}"


@registry.tool(toolset="agent")
async def add_comment(issue_id: int, content: str) -> str:
    """在 Issue 上添加评论。

    Args:
        issue_id: Issue ID
        content: 评论内容
    """
    await _api("POST", f"/issues/{issue_id}/comments", json={"content": content, "author_role": ROLE})
    return f"已在 Issue #{issue_id} 添加评论"


@registry.tool(toolset="agent")
async def propose_plan(project_id: int, title: str, description: str = "") -> str:
    """提出执行计划。

    Args:
        project_id: 项目 ID
        title: 计划标题
        description: 计划描述
    """
    result = await _api("POST", "/plans", json={
        "title": title, "description": description,
        "project_id": project_id, "proposed_by": ROLE,
    })
    return f"已创建 Plan #{result['id']}: {result['title']}"


@registry.tool(toolset="agent")
async def update_plan_progress(plan_id: int, item_title: str, status: str) -> str:
    """更新计划进度。

    Args:
        plan_id: Plan ID
        item_title: 进度项标题
        status: 状态 todo/in_progress/done
    """
    await _api("POST", f"/plans/{plan_id}/items", json={
        "title": item_title, "status": status,
    })
    return f"Plan #{plan_id} 进度已更新: {item_title} -> {status}"


@registry.tool(toolset="agent")
async def list_plans(project_id: int | None = None) -> str:
    """查看项目计划列表。

    Args:
        project_id: 项目 ID（可选）
    """
    params = {}
    if project_id:
        params["project_id"] = project_id
    result = await _api("GET", "/plans", params=params)
    if not result:
        return "暂无计划。"
    lines = ["计划列表："]
    for p in result:
        lines.append(f"  #{p['id']} [{p['status']}] {p['title']} ({p.get('item_done_count', 0)}/{p.get('item_count', 0)})")
    return "\n".join(lines)


@registry.tool(toolset="agent")
async def notify_role(target_role: str, message: str, project_id: int | None = None) -> str:
    """通知其他角色。

    Args:
        target_role: 目标角色 agent/mate/tester/admin
        message: 通知内容
        project_id: 项目 ID（可选）
    """
    await _api("POST", "/notifications", json={
        "target_role": target_role, "message": message, "project_id": project_id,
    })
    return f"已通知 {target_role}: {message}"


def register_tools():
    pass
```

- [ ] **Step 3: 创建 agents/agent/system_prompt.md**

```markdown
# Agent Role

You are the **Developer Agent** in the Metis PM system. Your role is to execute tasks assigned to you.

## Responsibilities
- Work on Issues assigned to you (assignee_role="agent")
- Update Issue status as you make progress
- Add comments to Issues with your findings
- Propose execution plans for complex tasks
- Update plan progress as you complete items
- Notify other roles (mate, tester) when you need review or testing

## Workflow
1. Check `list_my_issues` to see what's assigned to you
2. Pick the highest priority Issue and start working
3. Update status to `in_progress` when you begin
4. Add comments with your progress and decisions
5. When done, update status to `resolved` and notify the tester
6. For complex tasks, use `propose_plan` first and wait for approval

## Rules
- Always update Issue status before and after working
- Add meaningful comments explaining your decisions
- If blocked, notify mate with details
- Respect priority order: P0 > P1 > P2 > P3
```

- [ ] **Step 4: Commit**

```bash
git add agents/agent/
git commit -m "feat: add Agent container with 8 tools"
```

---

### Task 5.3: 创建 Mate 容器

**Files:**
- Create: `agents/mate/main.py`
- Create: `agents/mate/tools.py`
- Create: `agents/mate/system_prompt.md`

- [ ] **Step 1: 创建 agents/mate/main.py**

```python
import os
from pm_copilot_engine import AIAgent, registry
from tools import register_tools

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/api/v1")
API_KEY = os.getenv("API_KEY", "metis-pm-default-key-change-me")
ROLE = "mate"

register_tools()

agent = AIAgent(
    model=os.getenv("PM_MODEL", "gpt-4o"),
    base_url=os.getenv("PM_API_BASE_URL"),
    api_key=os.getenv("PM_API_KEY"),
    system_prompt=open("system_prompt.md").read(),
    enabled_toolsets=["mate"],
)

if __name__ == "__main__":
    agent.run()
```

- [ ] **Step 2: 创建 agents/mate/tools.py**

```python
import os
import httpx
from pm_copilot_engine import registry

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/api/v1")
API_KEY = os.getenv("API_KEY", "metis-pm-default-key-change-me")
ROLE = "mate"

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


async def _api(method: str, path: str, **kwargs) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, f"{BACKEND_URL}{path}", headers=HEADERS, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}


@registry.tool(toolset="mate")
async def list_pending_plans(project_id: int | None = None) -> str:
    """查看待审批的计划。

    Args:
        project_id: 项目 ID（可选）
    """
    params = {"status": "pending"}
    if project_id:
        params["project_id"] = project_id
    result = await _api("GET", "/plans", params=params)
    if not result:
        return "没有待审批的计划。"
    lines = [f"待审批计划 ({len(result)}):"]
    for p in result:
        lines.append(f"  #{p['id']} {p['title']} (by {p.get('proposed_by', 'unknown')})")
    return "\n".join(lines)


@registry.tool(toolset="mate")
async def approve_plan(plan_id: int) -> str:
    """批准计划。

    Args:
        plan_id: Plan ID
    """
    result = await _api("POST", f"/plans/{plan_id}/approve")
    return f"Plan #{plan_id} 已批准"


@registry.tool(toolset="mate")
async def reject_plan(plan_id: int, reason: str = "") -> str:
    """驳回计划。

    Args:
        plan_id: Plan ID
        reason: 驳回原因
    """
    await _api("POST", f"/plans/{plan_id}/reject", json={"reason": reason})
    return f"Plan #{plan_id} 已驳回: {reason}"


@registry.tool(toolset="mate")
async def assign_issue(issue_id: int, role: str = "agent") -> str:
    """分配 Issue 给指定角色。

    Args:
        issue_id: Issue ID
        role: 目标角色 agent/tester（默认 agent）
    """
    await _api("PUT", f"/issues/{issue_id}", json={"assignee_role": role})
    return f"Issue #{issue_id} 已分配给 {role}"


@registry.tool(toolset="mate")
async def get_project_overview(project_id: int) -> str:
    """查看项目全局状态。

    Args:
        project_id: 项目 ID
    """
    result = await _api("GET", f"/projects/{project_id}")
    return (
        f"项目: {result['name']}\n"
        f"Issue 总数: {result.get('issue_count', 0)} | "
        f"进行中: {result.get('open_issue_count', 0)} | "
        f"Plan 数: {result.get('plan_count', 0)}"
    )


def register_tools():
    pass
```

- [ ] **Step 3: 创建 agents/mate/system_prompt.md**

```markdown
# First Mate Role

You are the **First Mate** in the Metis PM system. Your role is to review and coordinate.

## Responsibilities
- Review and approve/reject plans proposed by the Agent
- Assign Issues to the appropriate role
- Monitor project health and progress
- Coordinate between Agent and Tester

## Workflow
1. Check `list_pending_plans` regularly for new plans to review
2. Review each plan: is it clear? feasible? well-scoped?
3. Approve good plans, reject unclear ones with specific feedback
4. Assign unassigned Issues to the Agent
5. Monitor project overview for bottlenecks

## Rules
- Always provide a reason when rejecting a plan
- Don't approve plans that are too vague or too large
- Assign P0/P1 Issues immediately
```

- [ ] **Step 4: Commit**

```bash
git add agents/mate/
git commit -m "feat: add Mate container with 5 tools"
```

---

### Task 5.4: 创建 Tester 容器

**Files:**
- Create: `agents/tester/main.py`
- Create: `agents/tester/tools.py`
- Create: `agents/tester/system_prompt.md`

- [ ] **Step 1: 创建 agents/tester/main.py**

```python
import os
from pm_copilot_engine import AIAgent, registry
from tools import register_tools

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/api/v1")
API_KEY = os.getenv("API_KEY", "metis-pm-default-key-change-me")
ROLE = "tester"

register_tools()

agent = AIAgent(
    model=os.getenv("PM_MODEL", "gpt-4o"),
    base_url=os.getenv("PM_API_BASE_URL"),
    api_key=os.getenv("PM_API_KEY"),
    system_prompt=open("system_prompt.md").read(),
    enabled_toolsets=["tester"],
)

if __name__ == "__main__":
    agent.run()
```

- [ ] **Step 2: 创建 agents/tester/tools.py**

```python
import os
import httpx
from pm_copilot_engine import registry

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/api/v1")
API_KEY = os.getenv("API_KEY", "metis-pm-default-key-change-me")
ROLE = "tester"

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


async def _api(method: str, path: str, **kwargs) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, f"{BACKEND_URL}{path}", headers=HEADERS, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}


@registry.tool(toolset="tester")
async def report_bug(project_id: int, title: str, description: str = "", priority: str = "P2") -> str:
    """报告 Bug。

    Args:
        project_id: 项目 ID
        title: Bug 标题
        description: Bug 描述
        priority: 优先级 P0/P1/P2/P3
    """
    result = await _api("POST", "/issues", json={
        "title": title, "description": description,
        "project_id": project_id, "priority": priority,
        "issue_type": "bug", "source_role": ROLE,
    })
    return f"已报告 Bug #{result['id']}: {result['title']}"


@registry.tool(toolset="tester")
async def request_feature(project_id: int, title: str, description: str = "") -> str:
    """请求新功能。

    Args:
        project_id: 项目 ID
        title: 功能标题
        description: 功能描述
    """
    result = await _api("POST", "/issues", json={
        "title": title, "description": description,
        "project_id": project_id, "issue_type": "feature",
        "source_role": ROLE,
    })
    return f"已创建功能请求 #{result['id']}: {result['title']}"


@registry.tool(toolset="tester")
async def verify_issue(issue_id: int, passed: bool, comment: str = "") -> str:
    """验证 Issue 修复。

    Args:
        issue_id: Issue ID
        passed: 验证是否通过
        comment: 验证备注
    """
    if passed:
        await _api("PUT", f"/issues/{issue_id}", json={"status": "closed"})
        await _api("POST", f"/issues/{issue_id}/comments", json={
            "content": f"验证通过。{comment}", "author_role": ROLE,
        })
        return f"Issue #{issue_id} 验证通过，已关闭"
    else:
        await _api("PUT", f"/issues/{issue_id}", json={"status": "in_progress"})
        await _api("POST", f"/issues/{issue_id}/comments", json={
            "content": f"验证未通过。{comment}", "author_role": ROLE,
        })
        return f"Issue #{issue_id} 验证未通过，已退回"


@registry.tool(toolset="tester")
async def list_my_issues(project_id: int | None = None) -> str:
    """查看我创建的 Issue。

    Args:
        project_id: 项目 ID（可选）
    """
    params = {"source_role": ROLE}
    if project_id:
        params["project_id"] = project_id
    result = await _api("GET", "/issues", params=params)
    items = result.get("items", [])
    if not items:
        return "你还没有创建过 Issue。"
    lines = [f"你创建的 Issue ({result['total']}):"]
    for i in items:
        lines.append(f"  #{i['id']} [{i['priority']}] {i['title']} ({i['status']})")
    return "\n".join(lines)


def register_tools():
    pass
```

- [ ] **Step 3: 创建 agents/tester/system_prompt.md**

```markdown
# Tester Role

You are the **Tester** in the Metis PM system. Your role is quality assurance.

## Responsibilities
- Report bugs found during testing
- Request new features based on user needs
- Verify fixes when Agent marks issues as resolved
- Track issues you created

## Workflow
1. When you find a bug, use `report_bug` with clear description
2. When you think of a feature, use `request_feature`
3. When an Issue is marked `resolved`, use `verify_issue` to test it
4. If the fix works, verify and close. If not, reject back to `in_progress`

## Rules
- Always include clear steps to reproduce in bug reports
- Be specific about what passed/failed in verification
- Use appropriate priority: P0 for blockers, P1 for critical, P2 for normal
```

- [ ] **Step 4: Commit**

```bash
git add agents/tester/
git commit -m "feat: add Tester container with 4 tools"
```

---

### Task 5.5: 创建 Registrar 容器

**Files:**
- Create: `agents/registrar/main.py`
- Create: `agents/registrar/tools.py`
- Create: `agents/registrar/system_prompt.md`

- [ ] **Step 1: 创建 agents/registrar/main.py**

```python
import os
from pm_copilot_engine import AIAgent, registry
from tools import register_tools

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/api/v1")
API_KEY = os.getenv("API_KEY", "metis-pm-default-key-change-me")
ROLE = "registrar"

register_tools()

agent = AIAgent(
    model=os.getenv("PM_MODEL", "gpt-4o"),
    base_url=os.getenv("PM_API_BASE_URL"),
    api_key=os.getenv("PM_API_KEY"),
    system_prompt=open("system_prompt.md").read(),
    enabled_toolsets=["registrar"],
)

if __name__ == "__main__":
    agent.run()
```

- [ ] **Step 2: 创建 agents/registrar/tools.py**

```python
import os
import httpx
from pm_copilot_engine import registry

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/api/v1")
API_KEY = os.getenv("API_KEY", "metis-pm-default-key-change-me")
ROLE = "registrar"

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


async def _api(method: str, path: str, **kwargs) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, f"{BACKEND_URL}{path}", headers=HEADERS, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}


@registry.tool(toolset="registrar")
async def create_project(name: str, slug: str, description: str = "") -> str:
    """创建新项目。

    Args:
        name: 项目名称
        slug: URL 标识（英文，如 my-project）
        description: 项目描述
    """
    result = await _api("POST", "/projects", json={
        "name": name, "slug": slug, "description": description,
    })
    return f"已创建项目: {result['name']} (slug: {result['slug']}, id: {result['id']})"


@registry.tool(toolset="registrar")
async def initialize_issues(project_id: int, titles: list[str]) -> str:
    """批量创建初始 Issue。

    Args:
        project_id: 项目 ID
        titles: Issue 标题列表
    """
    created = []
    for title in titles:
        result = await _api("POST", "/issues", json={
            "title": title, "project_id": project_id, "source_role": ROLE,
        })
        created.append(f"  #{result['id']} {result['title']}")
    return f"已创建 {len(created)} 个 Issue:\n" + "\n".join(created)


@registry.tool(toolset="registrar")
async def get_project_context(project_id: int) -> str:
    """获取项目上下文（项目信息 + Issue 统计）。

    Args:
        project_id: 项目 ID
    """
    project = await _api("GET", f"/projects/{project_id}")
    issues = await _api("GET", "/issues", params={"project_id": project_id, "limit": 5})
    lines = [
        f"项目: {project['name']}",
        f"Issue 总数: {project.get('issue_count', 0)} | 进行中: {project.get('open_issue_count', 0)}",
        f"Plan 数: {project.get('plan_count', 0)}",
    ]
    items = issues.get("items", [])
    if items:
        lines.append("\n最近 Issue:")
        for i in items:
            lines.append(f"  #{i['id']} [{i['priority']}] {i['title']} ({i['status']})")
    return "\n".join(lines)


def register_tools():
    pass
```

- [ ] **Step 3: 创建 agents/registrar/system_prompt.md**

```markdown
# Registrar Role

You are the **Registrar** in the Metis PM system. Your role is project initialization.

## Responsibilities
- Create new projects when starting work
- Initialize projects with initial Issues from requirements
- Provide project context to other agents

## Workflow
1. When starting a new project, use `create_project` to set it up
2. Break down requirements into initial Issues with `initialize_issues`
3. Provide project context when other agents ask

## Rules
- Use descriptive, URL-friendly slugs (lowercase, hyphens)
- Break large requirements into small, actionable Issues
- Each Issue should be completable in one session
```

- [ ] **Step 4: Commit**

```bash
git add agents/registrar/
git commit -m "feat: add Registrar container with 3 tools"
```
---
## Phase 6: 前端精简

### Task 6.1: 更新 API client 为 API Key 认证

**Files:** Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 重写 client.ts**

```ts
import axios from "axios";
const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";
const API_KEY = import.meta.env.VITE_API_KEY || "metis-pm-default-key-change-me";
export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
});
```

- [ ] **Step 2: Commit**
```bash
git add frontend/src/api/client.ts
git commit -m "refactor: simplify API client to use X-API-Key"
```

---

### Task 6.2: 更新 API 类型定义

**Files:** Modify: `frontend/src/api/issues.ts`, `plans.ts`, `projects.ts`, `notifications.ts`, `auth.ts`, `index.ts`

- [ ] **Step 1: 重写 issues.ts** — 用 `assignee_role`/`source_role` 替代 `assignee`/`source`，移除 `milestone_id`, `labels`, `parent_id`, `closed_at`, `deferred_*` 字段。

```ts
import { api } from "./client";

export interface Issue {
  id: number; project_id?: number; title: string; description?: string;
  issue_type: string; status: string; priority: string;
  assignee_role?: string; source_role?: string;
  created_at: string; updated_at: string;
}
export interface IssueListResponse { total: number; items: Issue[]; }
export interface IssueCreate {
  title: string; description?: string; issue_type?: string;
  priority?: string; assignee_role?: string; source_role?: string; project_id?: number;
}
export interface IssueUpdate {
  title?: string; description?: string; issue_type?: string;
  status?: string; priority?: string; assignee_role?: string;
}
export interface Comment { id: number; issue_id: number; author_role?: string; content: string; created_at: string; }
export interface IssueWithComments extends Issue { comments: Comment[]; }
export interface CommentCreate { content: string; author_role?: string; }
export const issuesApi = {
  list: (params?: Record<string, any>) => api.get<IssueListResponse>("/issues", { params }),
  get: (id: number) => api.get<IssueWithComments>(`/issues/${id}`),
  create: (data: IssueCreate) => api.post<Issue>("/issues", data),
  update: (id: number, data: IssueUpdate) => api.put<Issue>(`/issues/${id}`, data),
  remove: (id: number) => api.delete(`/issues/${id}`),
  addComment: (issueId: number, data: CommentCreate) => api.post<Comment>(`/issues/${issueId}/comments`, data),
};
```

- [ ] **Step 2: 重写 plans.ts** — 移除 `current_milestone_id`, `proposed_by_name`。

```ts
import { api } from "./client";

export interface PlanItem {
  id: number; plan_id: number; title: string; description?: string;
  status: string; sort_order: number; completed_by?: string;
  completed_at?: string; created_at: string; updated_at: string;
}
export interface Plan {
  id: number; project_id?: number; title: string; description?: string;
  status: string; proposed_by?: string; approved_by?: string;
  approved_at?: string; reject_reason?: string;
  created_at: string; updated_at: string;
  plan_items?: PlanItem[]; item_count?: number; item_done_count?: number;
}
export const plansApi = {
  list: (params?: Record<string, any>) => api.get<Plan[]>("/plans", { params }),
  get: (id: number) => api.get<Plan>(`/plans/${id}`),
  create: (data: Partial<Plan>) => api.post<Plan>("/plans", data),
  update: (id: number, data: Partial<Plan>) => api.put<Plan>(`/plans/${id}`, data),
  remove: (id: number) => api.delete(`/plans/${id}`),
  approve: (id: number) => api.post<Plan>(`/plans/${id}/approve`),
  reject: (id: number, reason?: string) => api.post<Plan>(`/plans/${id}/reject`, { reason }),
  listItems: (planId: number) => api.get<PlanItem[]>(`/plans/${planId}/items`),
  createItem: (planId: number, data: Partial<PlanItem>) => api.post<PlanItem>(`/plans/${planId}/items`, data),
  updateItem: (planId: number, itemId: number, data: Partial<PlanItem>) => api.put<PlanItem>(`/plans/${planId}/items/${itemId}`, data),
  removeItem: (planId: number, itemId: number) => api.delete(`/plans/${planId}/items/${itemId}`),
};
```

- [ ] **Step 3: 重写 projects.ts** — 移除 `repo_url`, `owner`, `default_milestone_id`。

```ts
import { api } from "./client";

export interface Project { id: number; name: string; slug: string; description?: string; status: string; created_at: string; updated_at: string; }
export interface ProjectWithStats extends Project { issue_count: number; open_issue_count: number; plan_count: number; }
export interface ProjectCreate { name: string; slug: string; description?: string; }
export interface ProjectUpdate { name?: string; slug?: string; description?: string; status?: string; }
export const projectsApi = {
  list: (params?: Record<string, any>) => api.get<ProjectWithStats[]>("/projects", { params }),
  get: (slug: string) => api.get<ProjectWithStats>(`/projects/${slug}`),
  create: (data: ProjectCreate) => api.post<Project>("/projects", data),
  update: (slug: string, data: ProjectUpdate) => api.put<Project>(`/projects/${slug}`, data),
  remove: (slug: string) => api.delete(`/projects/${slug}`),
};
```

- [ ] **Step 4: 重写 notifications.ts** — 用 `target_role`/`message`/`is_read` 替代旧字段。

```ts
import { api } from "./client";

export interface Notification { id: number; target_role: string; message: string; is_read: boolean; project_id?: number; created_at: string; }
export interface NotificationListResponse { total: number; items: Notification[]; }
export const notificationsApi = {
  list: (params?: Record<string, any>) => api.get<NotificationListResponse>("/notifications", { params }),
  unreadCount: () => api.get<{ count: number }>("/notifications/unread-count"),
  markRead: (id: number) => api.put<Notification>(`/notifications/${id}/read`),
  markAllRead: () => api.put("/notifications/read-all"),
};
```

- [ ] **Step 5: 重写 auth.ts** — 只保留 health。

```ts
import { api } from "./client";
export const authApi = { health: () => api.get("/auth/health") };
```

- [ ] **Step 6: 重写 index.ts** — 只导出 5 个模块。

```ts
export * from "./issues";
export * from "./plans";
export * from "./projects";
export * from "./notifications";
export * from "./auth";
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/
git commit -m "refactor: simplify frontend API layer - API Key auth, remove unused modules"
```

---

### Task 6.3: 删除不需要的前端文件

**Files to delete:**
- `frontend/src/pages/`: Board.tsx, Milestones.tsx, Servers.tsx, Workflows.tsx, Projects.tsx, ProjectRegistrations.tsx, Feedbacks.tsx, RiskAlerts.tsx, Graph.tsx, GitIntegration.tsx, DeadLetterQueue.tsx, Notifications.tsx, Login.tsx
- `frontend/src/components/`: ActivityTimeline.tsx, AgentActivityPanel.tsx, BoardColumn.tsx, BurndownChart.tsx, CopilotChat.tsx, ProjectHealth.tsx, GraphView/ (dir)
- `frontend/src/api/`: milestones.ts, servers.ts, activity_logs.ts, dashboard.ts, projectRegistrations.ts, agentStatus.ts, graph.ts, riskAlerts.ts, monitoring.ts, feedback.ts
- `frontend/src/queries/` (entire directory)
- `frontend/src/hooks/`: useAuth.tsx, useNotifications.tsx, useTheme.tsx, useProject.tsx

- [ ] **Step 1: Delete files** (see plan for full PowerShell commands)
- [ ] **Step 2: Commit**

---

### Task 6.4: 重写 App.tsx

**Files:** Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 重写 App.tsx** — 移除 AuthProvider, ProjectProvider, NotificationProvider, ThemeProvider, Login, PrivateRoute。

```tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Issues from "./pages/Issues";
import IssueDetail from "./pages/IssueDetail";
import Plans from "./pages/Plans";
import PlanDetail from "./pages/PlanDetail";

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/projects/default/dashboard" replace />} />
            <Route path="issues/:id" element={<IssueDetail />} />
            <Route path="plans/:id" element={<PlanDetail />} />
            <Route path="projects/:projectSlug/dashboard" element={<Dashboard />} />
            <Route path="projects/:projectSlug/issues" element={<Issues />} />
            <Route path="projects/:projectSlug/issues/:id" element={<IssueDetail />} />
            <Route path="projects/:projectSlug/plans" element={<Plans />} />
            <Route path="projects/:projectSlug/plans/:id" element={<PlanDetail />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "refactor: simplify App.tsx - 5 pages, no auth wrapper"
```

---

### Task 6.5: 重写 main.tsx

**Files:** Modify: `frontend/src/main.tsx`

- [ ] **Step 1: 重写 main.tsx** — 移除 QueryClientProvider, ReactQueryDevtools。
- [ ] **Step 2: Commit**

---

### Task 6.6: 精简 Layout.tsx

**Files:** Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: 重写 Layout.tsx** — 3 个菜单项，不依赖 useProject hook。

```tsx
import { useState } from "react";
import { Outlet, useNavigate, useParams } from "react-router-dom";
import { Layout as AntLayout, Menu, Button, Drawer } from "antd";
import { DashboardOutlined, BugOutlined, ScheduleOutlined, MenuOutlined } from "@ant-design/icons";

const { Sider, Content, Header } = AntLayout;

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const { projectSlug } = useParams<{ projectSlug: string }>();
  const slug = projectSlug || "default";

  const menuItems = [
    { key: "dashboard", icon: <DashboardOutlined />, label: "概览" },
    { key: "issues", icon: <BugOutlined />, label: "Issues" },
    { key: "plans", icon: <ScheduleOutlined />, label: "计划" },
  ];

  const handleMenuClick = (key: string) => {
    navigate(`/projects/${slug}/${key}`);
    setMobileOpen(false);
  };

  const sidebar = (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: 16, fontWeight: 700, fontSize: 16, textAlign: "center", borderBottom: "1px solid #f0f0f0" }}>
        Metis PM
      </div>
      <Menu
        mode="inline"
        selectedKeys={[window.location.pathname.split("/").pop() || "dashboard"]}
        items={menuItems}
        onClick={({ key }) => handleMenuClick(key)}
        style={{ flex: 1, borderRight: 0 }}
      />
    </div>
  );

  return (
    <AntLayout style={{ minHeight: "100vh" }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} breakpoint="lg">
        {sidebar}
      </Sider>
      <Drawer open={mobileOpen} onClose={() => setMobileOpen(false)} placement="left" width={250} styles={{ body: { padding: 0 } }}>
        {sidebar}
      </Drawer>
      <AntLayout>
        <Header style={{ background: "#fff", padding: "0 16px", display: "flex", alignItems: "center", gap: 12 }}>
          <Button type="text" icon={<MenuOutlined />} onClick={() => setMobileOpen(true)} className="mobile-menu-btn" />
          <span style={{ fontWeight: 600 }}>Metis PM</span>
        </Header>
        <Content style={{ margin: 16 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Layout.tsx
git commit -m "refactor: simplify Layout - 3 menu items, no auth, no project switcher"
```

---

### Task 6.7: 精简页面组件

**Files:** Modify: `frontend/src/pages/Dashboard.tsx`, `Issues.tsx`, `IssueDetail.tsx`, `Plans.tsx`, `PlanDetail.tsx`

- [ ] **Step 1: 精简 Dashboard.tsx** — 只保留项目统计卡片（Issue 总数/进行中/Plan 数）+ 最近 Issue 列表。
- [ ] **Step 2: 精简 Issues.tsx** — 移除 milestone 筛选、source 图标、defer 按钮。用 assignee_role 替代 assignee。
- [ ] **Step 3: 精简 IssueDetail.tsx** — 移除 milestone/defer/ActivityTimeline 相关内容。
- [ ] **Step 4: 精简 Plans.tsx** — 移除 milestone 引用。
- [ ] **Step 5: 精简 PlanDetail.tsx** — 移除 milestone 引用。
- [ ] **Step 6: Commit**

---

### Task 6.8: 精简 IssueCard.tsx

**Files:** Modify: `frontend/src/components/IssueCard.tsx`

- [ ] **Step 1: 重写 IssueCard.tsx** — 移除 SOURCE_ICONS、@dnd-kit 拖拽逻辑，保留优先级/类型/assignee_role 标签。
- [ ] **Step 2: Commit**

---

## Phase 7: Docker Compose 和配置

### Task 7.1: 重写 docker-compose.yml

**Files:** Modify: `docker-compose.yml`

- [ ] **Step 1: 重写 docker-compose.yml** — 6 个服务，移除 mcp。

```yaml
services:
  backend:
    build: ./backend
    container_name: pm-backend
    ports: ["${BACKEND_PORT:-8000}:8000"]
    volumes: [sqlite_data:/data]
    environment:
      - DATABASE_URL=sqlite+aiosqlite:////data/metis_pm.db
      - API_KEY=${API_KEY:-metis-pm-default-key-change-me}
      - SECRET_KEY=${SECRET_KEY:-not-used-in-v2}
      - ADMIN_PASSWORD_HASH=${ADMIN_PASSWORD_HASH:-}
      - AGENT_PASSWORDS_JSON=${AGENT_PASSWORDS_JSON:-{}}
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:8080}
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s; timeout: 5s; retries: 3; start_period: 15s
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: pm-frontend
    ports: ["${FRONTEND_PORT:-8080}:80"]
    depends_on: [backend]
    restart: unless-stopped

  agent:
    build:
      context: ./agents
      dockerfile: Dockerfile
      args: { ROLE_DIR: agent }
    container_name: pm-agent
    ports: ["9001:9001"]
    environment:
      - BACKEND_URL=http://backend:8000/api/v1
      - API_KEY=${API_KEY:-metis-pm-default-key-change-me}
      - PM_MODEL=${PM_MODEL:-gpt-4o}
      - PM_API_BASE_URL=${PM_API_BASE_URL}
      - PM_API_KEY=${PM_API_KEY}
      - ROLE=agent
      - MCP_PORT=9001
    depends_on: [backend]
    restart: unless-stopped

  mate:
    build:
      context: ./agents
      dockerfile: Dockerfile
      args: { ROLE_DIR: mate }
    container_name: pm-mate
    ports: ["9002:9002"]
    environment:
      - BACKEND_URL=http://backend:8000/api/v1
      - API_KEY=${API_KEY:-metis-pm-default-key-change-me}
      - PM_MODEL=${PM_MODEL:-gpt-4o}
      - PM_API_BASE_URL=${PM_API_BASE_URL}
      - PM_API_KEY=${PM_API_KEY}
      - ROLE=mate
      - MCP_PORT=9002
    depends_on: [backend]
    restart: unless-stopped

  tester:
    build:
      context: ./agents
      dockerfile: Dockerfile
      args: { ROLE_DIR: tester }
    container_name: pm-tester
    ports: ["9003:9003"]
    environment:
      - BACKEND_URL=http://backend:8000/api/v1
      - API_KEY=${API_KEY:-metis-pm-default-key-change-me}
      - PM_MODEL=${PM_MODEL:-gpt-4o}
      - PM_API_BASE_URL=${PM_API_BASE_URL}
      - PM_API_KEY=${PM_API_KEY}
      - ROLE=tester
      - MCP_PORT=9003
    depends_on: [backend]
    restart: unless-stopped

  registrar:
    build:
      context: ./agents
      dockerfile: Dockerfile
      args: { ROLE_DIR: registrar }
    container_name: pm-registrar
    ports: ["9004:9004"]
    environment:
      - BACKEND_URL=http://backend:8000/api/v1
      - API_KEY=${API_KEY:-metis-pm-default-key-change-me}
      - PM_MODEL=${PM_MODEL:-gpt-4o}
      - PM_API_BASE_URL=${PM_API_BASE_URL}
      - PM_API_KEY=${PM_API_KEY}
      - ROLE=registrar
      - MCP_PORT=9004
    depends_on: [backend]
    restart: unless-stopped

volumes:
  sqlite_data:
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "refactor: docker-compose - 6 services, remove mcp"
```

---

### Task 7.2: 更新 .env.example

**Files:** Modify: `.env.example`

- [ ] **Step 1: 重写 .env.example**

```env
# Metis PM v2.0 - Environment Configuration

# API Key for frontend and agent containers
API_KEY=metis-pm-default-key-change-me

# LLM configuration for agent containers
PM_MODEL=gpt-4o
PM_API_BASE_URL=https://api.openai.com/v1
PM_API_KEY=sk-...

# Agent passwords (JSON, for agent container auth)
# Format: {"agent-name": {"password_hash": "...", "role": "agent"}, ...}
AGENT_PASSWORDS_JSON={}

# Optional
# BACKEND_PORT=8000
# FRONTEND_PORT=8080
# CORS_ORIGINS=http://localhost:8080
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "refactor: simplify .env.example for v2.0"
```

---

### Task 7.3: 更新 Makefile

**Files:** Modify: `Makefile`

- [ ] **Step 1: 精简 Makefile** — 移除 mcp 相关命令，保留 build/up/down/logs。
- [ ] **Step 2: Commit**

---

### Task 7.4: 更新 CHANGELOG.md 和 README.md

**Files:** Modify: `CHANGELOG.md`, `README.md`, `README_zh.md`

- [ ] **Step 1: 更新 CHANGELOG.md** — 添加 v2.0 条目。
- [ ] **Step 2: 更新 README** — 反映新架构。
- [ ] **Step 3: Commit**

---

## Phase 8: 验证

### Task 8.1: 后端启动验证

- [ ] **Step 1: 安装依赖并启动后端**
```bash
cd backend && pip install fastapi uvicorn[standard] sqlalchemy[asyncio] aiosqlite pydantic pydantic-settings python-multipart python-dotenv pyjwt[crypto] httpx bcrypt
uvicorn main:app --host 0.0.0.0 --port 8000
```
Expected: 服务启动，`/health` 返回 200，`/api/v1/projects` 返回空列表。

- [ ] **Step 2: 测试 API Key 认证**
```bash
curl -H "X-API-Key: metis-pm-default-key-change-me" http://localhost:8000/api/v1/projects
```
Expected: 200 OK

---

### Task 8.2: Docker Compose 启动验证

- [ ] **Step 1: 构建并启动**
```bash
docker compose build
docker compose up -d
```
Expected: 6 个容器全部 running

- [ ] **Step 2: 验证各服务**
```bash
curl http://localhost:8000/health
curl http://localhost:8080
```
Expected: backend 返回 `{"status":"ok"}`，frontend 返回 HTML。

---

### Task 8.3: 端到端测试

- [ ] **Step 1: 创建项目**
```bash
curl -X POST http://localhost:8000/api/v1/projects -H "X-API-Key: metis-pm-default-key-change-me" -H "Content-Type: application/json" -d '{"name":"Test","slug":"test"}'
```
Expected: 返回创建的项目 JSON

- [ ] **Step 2: 创建 Issue**
```bash
curl -X POST http://localhost:8000/api/v1/issues -H "X-API-Key: metis-pm-default-key-change-me" -H "Content-Type: application/json" -d '{"title":"Test Issue","project_id":1}'
```
Expected: 返回创建的 Issue JSON

- [ ] **Step 3: 创建 Plan**
```bash
curl -X POST http://localhost:8000/api/v1/plans -H "X-API-Key: metis-pm-default-key-change-me" -H "Content-Type: application/json" -d '{"title":"Test Plan","project_id":1}'
```
Expected: 返回创建的 Plan JSON

- [ ] **Step 4: Commit**
