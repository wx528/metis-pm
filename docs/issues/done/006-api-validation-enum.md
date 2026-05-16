# 006 - API 输入缺少枚举值校验

- **优先级**: P1
- **类型**: bug
- **状态**: open

## 问题描述

Schema 中的枚举字段（如 `status`、`priority`、`source`、`issue_type`）使用 `str` 类型而非 `Enum`，API 不校验传入值是否合法。

例如：
- `POST /issues` 传入 `priority: "P5"` → 接受但写入数据库时 SQLAlchemy Enum 校验失败返回 500
- `POST /plans/{id}/approve` 对 `pending_approval` 状态的计划才能审批，但若传入非法 status 如 `"pending_approval"` 绕过创建，审批逻辑可能异常

## 影响范围

所有 schema 中的 `str` 类型枚举字段：
- `IssueCreate.priority` — 应限制为 P0/P1/P2/P3
- `IssueCreate.source` — 应限制为 user/ai_agent/collaborative
- `PlanCreate.status` — 应限制为合法值
- `ServerCreate.server_type` / `status` / `environment` — 同理

## 修复方案

在 Pydantic schema 中使用 `Literal` 或 `enum.Enum` 类型：

```python
from typing import Literal

Priority = Literal["P0", "P1", "P2", "P3"]

class IssueCreate(BaseModel):
    priority: Priority = "P2"
```
