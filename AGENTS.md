# AGENTS.md — 项目编码规范

> 本文档面向 AI Agent 和开发者，定义 Metis PM 的前后端编码规范。
> 最后更新：2026-05-28

---

## 一、后端（Python / FastAPI）

### 1. 项目结构

```
backend/
├── main.py                  # FastAPI 入口 + 数据库迁移
├── mcp_server.py            # MCP Server（AI Agent 工具入口）
├── mcp_server_mate.py       # First Mate MCP Server（多 Agent 架构）
├── mcp_server_tester.py     # Tester MCP Server（内部测试角色）
├── mcp_common.py            # MCP 共享工具与基类
├── requirements.txt
├── src/
│   ├── settings.py          # 全局配置（Pydantic BaseSettings）
│   ├── core/                # 跨路由共享的基础设施
│   │   ├── database.py      # SQLAlchemy 异步引擎 + Base + EnumColumn
│   │   ├── dependencies.py  # 依赖注入（get_db）
│   │   ├── crypto.py        # 加密工具
│   │   ├── activity.py      # 活动日志
│   │   ├── notification.py  # 通知 + SSE
│   │   └── workflow_engine.py
│   ├── models/              # SQLAlchemy ORM（每个实体一个文件）
│   ├── schemas/             # Pydantic 请求/响应模型
│   └── routes/              # FastAPI 路由
└── tests/
```

**原则：三层分离，严格解耦**

- `models/` → 数据层（ORM 定义，不包含业务逻辑）
- `schemas/` → 验证/序列化层（Pydantic，不做数据库操作）
- `routes/` → API 层（组合 models + schemas，包含业务逻辑）
- `core/` → 跨路由共享的基础设施

### 2. 命名规范

| 类别 | 规范 | 示例 |
|------|------|------|
| 文件名 | 小写下划线 | `issue.py`, `workflow_engine.py` |
| 类名 | PascalCase | `IssueRead`, `WorkflowEngine` |
| 函数/方法 | 小写下划线 | `list_issues()`, `handle_push_event()` |
| 变量 | 小写下划线 | `issue_count`, `created_at` |
| 常量 | 大写下划线 | `MAX_RETRIES`, `DEFAULT_PAGE_SIZE` |
| 枚举值 | 小写下划线 | `in_progress`, `not_started` |
| 表名 | 复数小写 | `issues`, `workflows` |
| URL 路径 | 小写连字符 | `/api/v1/issue-comments` |

### 3. 模型定义（models/）

```python
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base, EnumColumn

# 枚举：继承 str + enum.Enum
class IssueStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"

# ORM 模型
class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    status = Column(EnumColumn(IssueStatus), default=IssueStatus.OPEN)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    # 关系：字符串引用类名
    project = relationship("Project", back_populates="issues")
    comments = relationship("IssueComment", back_populates="issue",
                           cascade="all, delete-orphan")
```

**要点：**
- 枚举列统一用 `EnumColumn(EnumClass)`，不用 SQLAlchemy 原生 `Enum`
- 时间字段统一 UTC：`datetime.now(timezone.utc)`，不用 `datetime.utcnow()`
- `relationship` 用字符串引用，不用直接引用类

### 4. Schema 定义（schemas/）

每个实体三个 Schema：`EntityCreate` / `EntityUpdate` / `EntityRead`

```python
from typing import Optional, List
from pydantic import BaseModel, Field

class IssueCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    priority: str = Field(default="P2")
    issue_type: str = Field(default="task")

class IssueUpdate(BaseModel):
    """所有字段 Optional，支持部分更新"""
    title: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None

class IssueRead(BaseModel):
    id: int
    title: str
    status: str          # Read 中用 str，不用枚举类
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class IssueReadWithComments(IssueRead):
    """扩展 Read：继承基础 + 关联数据"""
    comments: List[IssueCommentRead] = []

class IssueListResponse(BaseModel):
    total: int
    items: List[IssueRead]
```

**要点：**
- `Create`：必填字段用 `Field(...)`，可选 `Optional[Type] = None`
- `Update`：所有字段 `Optional`，部分更新语义
- `Read`：`from_attributes = True`，枚举用 `str` 类型
- 列表响应统一用 `EntityListResponse` 包含 `total` + `items`

### 5. 路由定义（routes/）

```python
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.dependencies import get_db, get_current_user
from src.schemas.issue import IssueCreate, IssueUpdate, IssueRead, IssueListResponse

# 认证依赖在 Router 构造时统一声明
router = APIRouter(dependencies=[Depends(get_current_user)])

# 路径约定
@router.get("", response_model=IssueListResponse)      # 列表
@router.post("", response_model=IssueRead, status_code=201)  # 创建
@router.get("/{issue_id}", response_model=IssueRead)   # 详情
@router.put("/{issue_id}", response_model=IssueRead)   # 更新
@router.delete("/{issue_id}", status_code=204)          # 删除
@router.post("/{issue_id}/defer")                       # 自定义动作

# 分页参数
async def list_issues(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
):
```

**路由注册**（`routes/__init__.py`）：

```python
from fastapi import APIRouter
from src.routes import issues, projects, plans, workflows

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(issues.router, prefix="/issues", tags=["问题管理"])
api_router.include_router(projects.router, prefix="/projects", tags=["项目管理"])
```

**要点：**
- 统一前缀 `/api/v1`
- 中文 tags
- 认证依赖在 Router 级别声明，不在每个路由函数上重复

### 6. MCP Server 工具

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("metis-pm")

@mcp.tool()
async def create_issue(title: str, project_id: int, priority: str = "P2") -> str:
    """创建新 Issue。

    Args:
        title: Issue 标题
        project_id: 项目 ID
        priority: 优先级，可选 P0/P1/P2/P3，默认 P2

    Returns:
        创建结果摘要
    """
    # 通过 httpx 调用后端 REST API
    result = await _api_request("POST", "/api/v1/issues", json={...})
    return f"已创建 Issue #{result['id']}: {result['title']}"
```

**要点：**
- 工具返回 `str`（格式化文本），不返回 JSON
- docstring 写清楚参数含义和可选值
- API 通信用 `httpx.AsyncClient`，通过 JWT 认证

### 7. 错误处理

```python
from fastapi import HTTPException

# 路由中：用 HTTPException
raise HTTPException(status_code=404, detail="Issue not found")

# MCP 中：返回友好文本
return f"错误：未找到 Issue #{issue_id}"
```

### 8. 导入规范

```python
# 1. 标准库
import enum
from datetime import datetime, timezone

# 2. 第三方库
from fastapi import APIRouter, Depends
from sqlalchemy import Column, Integer

# 3. 项目内部
from src.core.database import Base, EnumColumn
from src.schemas.issue import IssueCreate, IssueRead
```

### 9. 数据库操作

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 查询：用 select() 风格，不用 query()
stmt = select(Issue).where(Issue.project_id == project_id).offset(skip).limit(limit)
result = await db.execute(stmt)
items = result.scalars().all()

# 创建
db.add(instance)
await db.commit()
await db.refresh(instance)

# 更新
for key, value in update_data.items():
    setattr(instance, key, value)
await db.commit()
```

---

## 二、前端（React / TypeScript）

### 1. 项目结构

```
frontend/src/
├── main.tsx               # 入口
├── App.tsx                # 路由定义
├── pages/                 # 页面组件（路由级）
│   ├── Projects.tsx
│   ├── Issues.tsx
│   ├── Plans.tsx
│   └── Workflows.tsx
├── components/            # 可复用组件
│   ├── IssueCard.tsx
│   ├── PlanItem.tsx
│   └── Layout.tsx
├── services/              # API 调用层
│   └── api.ts
├── types/                 # TypeScript 类型定义
│   └── index.ts
└── styles/                # 样式
    └── index.css
```

**原则：页面（pages/）与组件（components/）分离**

### 2. 命名规范

| 类别 | 规范 | 示例 |
|------|------|------|
| 组件文件 | PascalCase.tsx | `IssueCard.tsx`, `PlanDetail.tsx` |
| 页面文件 | PascalCase.tsx | `Projects.tsx`, `Workflows.tsx` |
| 服务/工具 | camelCase.ts | `api.ts`, `formatters.ts` |
| 类型文件 | camelCase 或 index | `types/index.ts` |
| 组件名 | PascalCase | `IssueCard`, `WorkflowStep` |
| 函数/变量 | camelCase | `handleSubmit`, `issueList` |
| 常量 | UPPER_SNAKE | `API_BASE_URL` |
| CSS 类 | 小写连字符 或 Tailwind | `issue-card`, `text-primary` |
| 事件处理 | `handle` 前缀 | `handleClick`, `handleSubmit` |
| 布尔变量 | `is`/`has`/`should` 前缀 | `isLoading`, `hasPermission` |

### 3. 类型定义（types/）

```typescript
// 与后端 Schema 对齐，字段名用 camelCase（转换 snake_case）
export interface Issue {
  id: number;
  title: string;
  status: string;
  priority: string;
  issueType: string;      // snake_case → camelCase
  createdAt: string;       // ISO 时间字符串
  updatedAt: string;
  description?: string;   // 可选字段用 ?
}

export interface IssueListResponse {
  total: number;
  items: Issue[];
}

// API 请求参数
export interface CreateIssueRequest {
  title: string;
  description?: string;
  priority?: string;
}
```

**要点：**
- `interface` 优先，不用 `type` 除非需要联合类型
- 后端 `snake_case` → 前端 `camelCase`，API 层做转换
- 可选字段用 `?`，不写 `| undefined`

### 4. API 调用层（services/api.ts）

```typescript
const API_BASE = '/api/v1';

// 统一错误处理
async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  return response.json();
}

// 具体 API：动词 + 实体名
export const fetchIssues = (projectId: number) =>
  request<IssueListResponse>(`/projects/${projectId}/issues`);

export const createIssue = (data: CreateIssueRequest) =>
  request<Issue>('/issues', { method: 'POST', body: JSON.stringify(data) });
```

**要点：**
- API 函数用 `fetch`/`create`/`update`/`delete` + 实体名
- 统一 `request<T>` 泛型封装
- 错误处理在 `request` 中统一拦截

### 5. 页面组件模式

```tsx
import { useState, useEffect } from 'react';
import { Issue, fetchIssues } from '../services/api';

export default function Issues({ projectId }: { projectId: number }) {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadIssues();
  }, [projectId]);

  const loadIssues = async () => {
    try {
      setIsLoading(true);
      const data = await fetchIssues(projectId);
      setIssues(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setIsLoading(false);
    }
  };

  if (loading) return <div className="text-center py-8">加载中...</div>;
  if (error) return <div className="text-red-500">{error}</div>;

  return (
    <div>
      {issues.map(issue => <IssueCard key={issue.id} issue={issue} />)}
    </div>
  );
}
```

**要点：**
- `useState` 三个状态：`data` + `loading` + `error`
- `useEffect` 触发数据加载
- 加载/错误状态提前 return，正常逻辑在最后
- 列表渲染用 `key={item.id}`

### 6. 可复用组件模式

```tsx
interface IssueCardProps {
  issue: Issue;
  onStatusChange?: (id: number, status: string) => void;
}

export default function IssueCard({ issue, onStatusChange }: IssueCardProps) {
  const priorityColors: Record<string, string> = {
    P0: 'bg-red-100 text-red-800',
    P1: 'bg-orange-100 text-orange-800',
    P2: 'bg-blue-100 text-blue-800',
    P3: 'bg-gray-100 text-gray-800',
  };

  return (
    <div className="border rounded-lg p-4 hover:shadow-md transition-shadow">
      <h3 className="font-medium">{issue.title}</h3>
      <span className={`px-2 py-0.5 rounded text-xs ${priorityColors[issue.priority]}`}>
        {issue.priority}
      </span>
    </div>
  );
}
```

**要点：**
- Props 用 `interface XxxProps` 定义
- 回调用 `on` 前缀：`onStatusChange`, `onClick`
- 样式用 Tailwind CSS，不写独立 CSS 文件
- 颜色映射用 `Record<string, string>`

### 7. CSS / 样式

- **Tailwind CSS** 为主，不写独立 `.css` 文件（全局样式除外）
- 常用布局：`flex`, `gap-4`, `grid`, `grid-cols-3`
- 间距：`p-4`, `m-2`, `space-y-2`
- 文字：`text-sm`, `font-medium`, `text-gray-500`

---

## 三、通用规范

### Git Commit

```
feat: 新功能
fix: 修复 bug
docs: 文档更新
refactor: 重构
chore: 构建/配置变更
```

### 代码风格

- **Python**：类型注解必加，`async/await` 全异步
- **TypeScript**：严格模式，不用 `any`
- **注释**：关键逻辑中文注释，代码本身保持英文命名
- **行宽**：Python 88 字符（black 默认），TypeScript 100 字符

### 新增实体 Checklist

新增一个实体（如 `Label`）时，确保以下文件都已创建/更新：

- [ ] `backend/src/models/label.py` — ORM 模型
- [ ] `backend/src/schemas/label.py` — Pydantic Schema（Create/Update/Read/List）
- [ ] `backend/src/routes/label.py` — API 路由
- [ ] `backend/src/routes/__init__.py` — 注册路由
- [ ] `backend/src/models/__init__.py` — 导出模型
- [ ] `backend/mcp_server.py` — 新增 MCP 工具（Agent 通用）
- [ ] `backend/mcp_server_mate.py` — 新增 MCP 工具（First Mate）
- [ ] `backend/mcp_server_tester.py` — 新增 MCP 工具（Tester）
- [ ] `frontend/src/types/index.ts` — TypeScript 类型
- [ ] `frontend/src/services/api.ts` — API 函数
- [ ] `frontend/src/pages/Labels.tsx` — 页面
- [ ] `frontend/src/components/LabelCard.tsx` — 组件（如需要）
- [ ] `CHANGELOG.md` — 记录变更
