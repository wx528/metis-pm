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


class TestIssueMilestoneIntegration:
    """问题与里程碑关联测试"""

    @pytest.mark.asyncio
    async def test_create_issue_with_milestone(self, client):
        # 创建里程碑
        resp = await client.post("/api/v1/milestones", json={
            "title": "Sprint 1",
            "due_date": "2026-06-15",
        })
        milestone_id = resp.json()["id"]

        # 创建关联问题
        resp = await client.post("/api/v1/issues", json={
            "title": "Sprint 1 Task",
            "issue_type": "task",
            "priority": "medium",
            "milestone_id": milestone_id,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["milestone_id"] == milestone_id

    @pytest.mark.asyncio
    async def test_filter_issues_by_milestone(self, client):
        # 创建里程碑
        resp = await client.post("/api/v1/milestones", json={"title": "Sprint 2"})
        milestone_id = resp.json()["id"]

        # 创建关联问题
        await client.post("/api/v1/issues", json={
            "title": "Task A",
            "issue_type": "task",
            "milestone_id": milestone_id,
        })
        await client.post("/api/v1/issues", json={
            "title": "Task B",
            "issue_type": "task",
            "milestone_id": milestone_id,
        })

        # 筛选
        resp = await client.get(f"/api/v1/issues?milestone_id={milestone_id}")
        data = resp.json()
        assert data["total"] == 2
        assert all(i["milestone_id"] == milestone_id for i in data["items"])


class TestHealthCheck:
    """健康检查"""

    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["app"] == "project_manager"


class TestCommentsIntegration:
    """评论集成测试"""

    @pytest.mark.asyncio
    async def test_multiple_comments(self, client):
        # 创建问题
        resp = await client.post("/api/v1/issues", json={
            "title": "讨论问题",
            "issue_type": "bug",
        })
        issue_id = resp.json()["id"]

        # 添加多条评论
        for i in range(3):
            resp = await client.post(f"/api/v1/issues/{issue_id}/comments", json={
                "content": f"Comment {i}",
                "author": f"user{i}",
            })
            assert resp.status_code == 201

        # 验证详情
        resp = await client.get(f"/api/v1/issues/{issue_id}")
        data = resp.json()
        assert len(data["comments"]) == 3
        assert data["comments"][0]["content"] == "Comment 0"

    @pytest.mark.asyncio
    async def test_comment_default_author(self, client):
        resp = await client.post("/api/v1/issues", json={
            "title": "匿名评论测试",
            "issue_type": "task",
        })
        issue_id = resp.json()["id"]

        resp = await client.post(f"/api/v1/issues/{issue_id}/comments", json={
            "content": "匿名评论",
        })
        data = resp.json()
        assert data["author"] == "anonymous"
