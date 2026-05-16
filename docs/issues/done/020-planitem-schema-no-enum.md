# 020 — PlanItem schema 缺少枚举校验

> 优先级: P1 | 类型: bug | 状态: **fixed**

## 问题描述

`PlanItemCreate` 和 `PlanItemUpdate` 的 `status` 字段使用 `str` 类型，没有枚举校验：

```python
class PlanItemCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    status: str = "pending"       # 任意字符串！
    sort_order: int = 0

class PlanItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None  # 任意字符串！
    sort_order: Optional[int] = None
    completed_by: Optional[str] = None
    completed_at: Optional[datetime] = None
```

同样的问题也存在于：

| Schema | 字段 | 问题 |
|--------|------|------|
| `PlanItemCreate` | `status` | 无枚举校验 |
| `PlanItemUpdate` | `status` | 无枚举校验 |
| `PlanCreate` | `status` | 无枚举校验 |
| `PlanUpdate` | `status` | 无枚举校验 |
| `PlanCreate` | `proposed_by` | 无枚举校验 |
| `MilestoneUpdate` | `status` | 无枚举校验 |

而 `IssueCreate`/`IssueUpdate` 和 `ServerCreate`/`ServerUpdate` 已正确使用 `Literal` 类型做枚举校验。

## 涉及文件

- `backend/src/schemas/plan.py` L37-L38, L42-L47
- `backend/src/schemas/milestone.py` L17

## 修复方案

使用 `Literal` 类型限制合法值：

```python
PlanItemStatusType = Literal["pending", "in_progress", "done", "blocked"]
PlanStatusType = Literal["draft", "pending_approval", "active", "completed", "abandoned"]
PlanSourceType = Literal["user", "ai_agent", "collaborative"]
MilestoneStatusType = Literal["open", "closed"]

class PlanItemCreate(BaseModel):
    status: PlanItemStatusType = "pending"

class PlanItemUpdate(BaseModel):
    status: Optional[PlanItemStatusType] = None

class PlanCreate(BaseModel):
    status: PlanStatusType = "draft"
    proposed_by: PlanSourceType = "user"

class PlanUpdate(BaseModel):
    status: Optional[PlanStatusType] = None

class MilestoneUpdate(BaseModel):
    status: Optional[MilestoneStatusType] = None
```
