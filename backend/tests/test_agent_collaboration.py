import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from src.core.dependencies import get_db
from src.models.notification import Notification


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with LifespanManager(app):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.mark.asyncio
async def test_role_based_notification_filtering(client: AsyncClient):
    """测试角色通知过滤：admin 可以看到发给 mate 角色的通知"""
    login_resp = await client.post("/api/v1/auth/login", json={"password": "testadmin"})
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 直接创建一条发给 mate 角色的通知
    async for db in get_db():
        notification = Notification(
            recipient="mate",
            type="role_notification",
            title="Test for mate role",
            body="Please review",
        )
        db.add(notification)
        await db.commit()
        break

    # admin 应该能在通知列表中看到这条通知（因为 _recipient_filter 包含 admin）
    resp = await client.get("/api/v1/notifications", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert any(n["recipient"] == "mate" for n in data["items"])


@pytest.mark.asyncio
async def test_comment_handover_type(client: AsyncClient):
    """测试 comment_type=handover 的评论创建"""
    login_resp = await client.post("/api/v1/auth/login", json={"password": "testadmin"})
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
    login_resp = await client.post("/api/v1/auth/login", json={"password": "testadmin"})
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/dashboard/agents", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data
    assert "pending_handovers" in data
