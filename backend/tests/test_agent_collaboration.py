import pytest
from httpx import AsyncClient
from asgi_lifespan import LifespanManager

from main import app


@pytest.fixture
async def client():
    async with LifespanManager(app):
        async with AsyncClient(app=app, base_url="http://test") as c:
            yield c


@pytest.mark.asyncio
async def test_notify_role_creates_notification(client: AsyncClient):
    """测试 notify_role 工具通过 API 创建角色通知"""
    login_resp = await client.post("/api/v1/auth/login", json={"password": "admin"})
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/v1/notifications", json={
        "recipient": "mate",
        "type": "role_notification",
        "title": "Test notification for mate",
        "body": "Please review issue #1",
        "entity_type": "issue",
        "entity_id": 1,
    }, headers=headers)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["recipient"] == "mate"
    assert data["type"] == "role_notification"


@pytest.mark.asyncio
async def test_comment_handover_type(client: AsyncClient):
    """测试 comment_type=handover 的评论创建"""
    login_resp = await client.post("/api/v1/auth/login", json={"password": "admin"})
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    issue_resp = await client.post("/api/v1/issues", json={
        "title": "Test handover comment",
        "issue_type": "task",
        "priority": "P2",
    }, headers=headers)
    issue_id = issue_resp.json()["id"]

    comment_resp = await client.post(f"/api/v1/issues/{issue_id}/comments", json={
        "content": "## 交接: Issue 开发完成\n\n### 改动范围\n- 文件: test.py",
        "author": "cursor",
        "comment_type": "handover",
    }, headers=headers)
    assert comment_resp.status_code in (200, 201)
    data = comment_resp.json()
    assert data["comment_type"] == "handover"


@pytest.mark.asyncio
async def test_dashboard_agents_endpoint(client: AsyncClient):
    """测试 Agent 状态聚合 API"""
    login_resp = await client.post("/api/v1/auth/login", json={"password": "admin"})
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/dashboard/agents", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data
    assert "pending_handovers" in data
