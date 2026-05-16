# 001 - API 端点缺少身份认证保护

- **优先级**: P0
- **类型**: bug/security
- **状态**: open

## 问题描述

系统定义了 `get_current_user` 依赖（在 `src/routes/auth.py`），但除了 `/auth/me` 端点外，**没有任何路由**使用 `Depends(get_current_user)` 保护。所有 CRUD 端点都是完全公开的，任何人无需认证即可操作。

## 影响范围

- `src/routes/issues.py` — 所有端点
- `src/routes/milestones.py` — 所有端点
- `src/routes/plans.py` — 所有端点
- `src/routes/servers.py` — 所有端点
- `src/routes/activity_logs.py` — 所有端点

## 修复方案

在每个 router 级别添加认证依赖：

```python
from src.routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])
```

或在每个需要保护的端点函数签名中添加 `user: dict = Depends(get_current_user)`。

## 备注

Login 和 health check 端点不需要认证。
