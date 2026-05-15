# 012 — Plan/PlanItem/Milestone/Server 的 status 列用 String 而非 Enum

> 优先级: P1 | 类型: code-quality | 状态: open

## 问题描述

`Issue` 模型正确使用了 `Column(Enum(IssueStatus))`，但以下模型的状态字段使用了 `Column(String(20))`：

| 模型 | 字段 | 已定义的 Enum | 实际列类型 |
|------|------|--------------|-----------|
| `Plan` | `status` | `PlanStatus` | `String(20)` |
| `Plan` | `proposed_by` | `PlanSource` | `String(20)` |
| `PlanItem` | `status` | `PlanItemStatus` | `String(20)` |
| `Milestone` | `status` | 无 | `String(20)` |
| `Server` | `server_type` | `ServerType` | `String(20)` |
| `Server` | `status` | `ServerStatus` | `String(20)` |
| `Server` | `environment` | `ServerEnvironment` | `String(20)` |

这导致：
1. **数据库层无约束**：可以写入任意字符串，如 `status="hello"`
2. **与 Schema 层校验不一致**：Pydantic schema 用 `Literal` 做了限制，但数据库层绕过了
3. **代码已定义 Enum 却未使用**：`PlanStatus`、`PlanItemStatus`、`ServerType` 等枚举类已定义但未在 Column 中使用

## 涉及文件

- `backend/src/models/plan.py` L25-L27
- `backend/src/models/plan_item.py` L20
- `backend/src/models/milestone.py` L12
- `backend/src/models/server.py` L33-L35

## 修复方案

将 `String(20)` 改为对应的 Enum 类型：

```python
# Plan
status = Column(Enum(PlanStatus), default=PlanStatus.DRAFT)
proposed_by = Column(Enum(PlanSource), default=PlanSource.USER)

# PlanItem
status = Column(Enum(PlanItemStatus), default=PlanItemStatus.PENDING)

# Milestone — 需新增 MilestoneStatus 枚举
class MilestoneStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
status = Column(Enum(MilestoneStatus), default=MilestoneStatus.OPEN)

# Server
server_type = Column(Enum(ServerType), default=ServerType.OTHER)
status = Column(Enum(ServerStatus), default=ServerStatus.ACTIVE)
environment = Column(Enum(ServerEnvironment), default=ServerEnvironment.DEVELOPMENT)
```

注意：此修改需要数据库迁移（ALTER TABLE），现有数据需确保值合法。
