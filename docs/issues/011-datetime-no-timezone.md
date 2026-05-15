# 011 — 所有 Model 的 datetime.utcnow 无时区

> 优先级: P1 | 类型: bug | 状态: open

## 问题描述

所有 SQLAlchemy Model 中的 `created_at` 和 `updated_at` 字段使用 `default=datetime.utcnow`，这有两个问题：

1. **`datetime.utcnow` 已被 Python 3.12 标记为 deprecated**，推荐使用 `datetime.now(timezone.utc)`
2. **生成的时间戳是 naive datetime（无时区信息）**，而路由层（如 `plans.py` 的 `approve_plan`）使用 `datetime.now(timezone.utc)` 生成的是 aware datetime，两者混用会导致比较和序列化不一致

## 涉及文件

| 文件 | 行号 |
|------|------|
| `backend/src/models/issue.py` | L57-L58 |
| `backend/src/models/milestone.py` | L16-L17 |
| `backend/src/models/comment.py` | L13 |
| `backend/src/models/plan.py` | L34-L35 |
| `backend/src/models/plan_item.py` | L24-L25 |
| `backend/src/models/activity_log.py` | L16 |
| `backend/src/models/server.py` | L43-L44 |

## 修复方案

将所有 `datetime.utcnow` 替换为 `datetime.now(timezone.utc)`：

```python
# Before
from datetime import datetime
created_at = Column(DateTime, default=datetime.utcnow)
updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# After
from datetime import datetime, timezone
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
```

注意：需要使用 `lambda` 包装，否则 `default` 会在模块加载时立即求值。
