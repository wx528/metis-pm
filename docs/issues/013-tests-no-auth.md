# 013 — 测试全部未认证，无法通过

> 优先级: P1 | 类型: bug | 状态: open

## 问题描述

所有测试文件（`test_issues.py`、`test_integration.py` 等）的 HTTP 客户端未携带 JWT token，但所有 API 路由（除 `/auth/login` 和 `/health`）都要求认证：

```python
# routes 中
router = APIRouter(dependencies=[Depends(get_current_user)])
```

```python
# 测试中 — 没有 Authorization header
resp = await client.post("/api/v1/issues", json={...})
# 期望 201，实际会返回 401
```

这意味着**所有测试都会因 401 而失败**。

## 涉及文件

- `backend/tests/test_issues.py`
- `backend/tests/test_issues_extended.py`
- `backend/tests/test_milestones.py`
- `backend/tests/test_milestones_extended.py`
- `backend/tests/test_integration.py`

## 修复方案

在 `conftest.py` 中添加认证 fixture：

```python
@pytest.fixture
async def auth_client(client):
    # 先获取 token
    resp = await client.post("/api/v1/auth/login", json={"password": "test_password"})
    token = resp.json()["token"]
    # 给 client 注入默认 Authorization header
    client.headers["Authorization"] = f"Bearer {token}"
    return client
```

同时需要在测试环境配置 `SECRET_KEY` 和 `ADMIN_PASSWORD`（可通过 `.env` 或环境变量）。
