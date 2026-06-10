"""测试 MCP SSE 通知和交接已读回执"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager

from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with LifespanManager(app):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
async def auth_headers(client):
    resp = await client.post("/api/v1/auth/login", json={"password": "testadmin"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


class TestHandoverReadReceipt:
    """交接已读回执测试"""

    @pytest.mark.asyncio
    async def test_mark_comment_read(self, client, auth_headers):
        """测试标记评论为已读"""
        # 1. 先创建一个 Issue
        issue_resp = await client.post(
            "/api/v1/issues",
            json={"title": "Test handover read", "project_id": 1},
            headers=auth_headers,
        )
        assert issue_resp.status_code == 201
        issue_id = issue_resp.json()["id"]
        
        # 2. 添加交接评论
        comment_resp = await client.post(
            f"/api/v1/issues/{issue_id}/comments",
            json={"content": "Handover from dev", "comment_type": "handover"},
            headers=auth_headers,
        )
        assert comment_resp.status_code == 201
        comment_id = comment_resp.json()["id"]
        
        # 3. 初始状态：未读
        assert comment_resp.json()["read_by"] is None
        assert comment_resp.json()["read_at"] is None
        
        # 4. 标记已读
        read_resp = await client.put(
            f"/api/v1/issue-comments/{comment_id}/read",
            headers=auth_headers,
        )
        assert read_resp.status_code == 200
        data = read_resp.json()
        assert data["comment"]["read_by"] is not None
        assert data["comment"]["read_at"] is not None

    @pytest.mark.asyncio
    async def test_mark_normal_comment_read(self, client, auth_headers):
        """测试普通评论也可以标记已读"""
        issue_resp = await client.post(
            "/api/v1/issues",
            json={"title": "Test normal comment", "project_id": 1},
            headers=auth_headers,
        )
        assert issue_resp.status_code == 201
        issue_id = issue_resp.json()["id"]
        
        comment_resp = await client.post(
            f"/api/v1/issues/{issue_id}/comments",
            json={"content": "Normal comment", "comment_type": "normal"},
            headers=auth_headers,
        )
        assert comment_resp.status_code == 201
        comment_id = comment_resp.json()["id"]
        
        # 普通评论也可以标记已读
        read_resp = await client.put(
            f"/api/v1/issue-comments/{comment_id}/read",
            headers=auth_headers,
        )
        assert read_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_unread_handovers(self, client, auth_headers):
        """测试查询未读交接评论"""
        # 创建 Issue 和交接评论
        issue_resp = await client.post(
            "/api/v1/issues",
            json={"title": "Test unread handovers", "project_id": 1},
            headers=auth_headers,
        )
        issue_id = issue_resp.json()["id"]
        
        await client.post(
            f"/api/v1/issues/{issue_id}/comments",
            json={"content": "Handover 1", "comment_type": "handover"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/issues/{issue_id}/comments",
            json={"content": "Handover 2", "comment_type": "handover"},
            headers=auth_headers,
        )
        
        # 查询未读交接
        resp = await client.get(
            "/api/v1/issue-comments?comment_type=handover&unread_only=true",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 2

    @pytest.mark.asyncio
    async def test_mark_handover_read_then_not_in_unread(self, client, auth_headers):
        """测试标记已读后不再出现在未读列表中"""
        issue_resp = await client.post(
            "/api/v1/issues",
            json={"title": "Test read then unread list", "project_id": 1},
            headers=auth_headers,
        )
        issue_id = issue_resp.json()["id"]
        
        comment_resp = await client.post(
            f"/api/v1/issues/{issue_id}/comments",
            json={"content": "Handover to mark read", "comment_type": "handover"},
            headers=auth_headers,
        )
        comment_id = comment_resp.json()["id"]
        
        # 先标记已读
        await client.put(
            f"/api/v1/issue-comments/{comment_id}/read",
            headers=auth_headers,
        )
        
        # 再查询未读，应该不包含这个评论
        resp = await client.get(
            "/api/v1/issue-comments?comment_type=handover&unread_only=true",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        items = resp.json()
        comment_ids = [item["id"] for item in items]
        assert comment_id not in comment_ids


class TestNotificationSSE:
    """SSE 实时通知测试"""

    @pytest.mark.skip(reason="SSE is a long-lived connection, tested manually")
    @pytest.mark.asyncio
    async def test_sse_stream_connects(self, client, auth_headers):
        """测试 SSE 连接可以建立（长连接，手动测试）"""
        pass
