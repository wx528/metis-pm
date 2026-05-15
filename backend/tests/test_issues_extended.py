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
async def sample_issue(client):
    resp = await client.post("/api/v1/issues", json={
        "title": "示例 Bug",
        "description": "这是一个测试问题",
        "issue_type": "bug",
        "priority": "high",
        "assignee": "dev1",
        "labels": "backend,urgent",
    })
    assert resp.status_code == 201
    return resp.json()["id"]


class TestIssuePagination:
    """分页测试"""

    @pytest.mark.asyncio
    async def test_pagination_skip_limit(self, client):
        # 创建 5 条数据
        for i in range(5):
            await client.post("/api/v1/issues", json={
                "title": f"Issue {i}",
                "issue_type": "task",
                "priority": "low",
            })

        resp = await client.get("/api/v1/issues?skip=0&limit=2")
        data = resp.json()
        assert data["total"] >= 5
        assert len(data["items"]) == 2

        resp = await client.get("/api/v1/issues?skip=2&limit=2")
        data = resp.json()
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_pagination_limit_boundary(self, client):
        resp = await client.get("/api/v1/issues?limit=100")
        assert resp.status_code == 200

        resp = await client.get("/api/v1/issues?limit=101")
        assert resp.status_code == 422  # 超过最大值


class TestIssueFilters:
    """筛选测试"""

    @pytest.mark.asyncio
    async def test_filter_by_priority(self, client, sample_issue):
        resp = await client.get("/api/v1/issues?priority=high")
        data = resp.json()
        assert all(i["priority"] == "high" for i in data["items"])

    @pytest.mark.asyncio
    async def test_filter_by_status(self, client, sample_issue):
        resp = await client.get("/api/v1/issues?status=open")
        data = resp.json()
        assert all(i["status"] == "open" for i in data["items"])

    @pytest.mark.asyncio
    async def test_filter_by_assignee(self, client, sample_issue):
        resp = await client.get("/api/v1/issues?assignee=dev1")
        data = resp.json()
        assert all(i["assignee"] == "dev1" for i in data["items"])

    @pytest.mark.asyncio
    async def test_search_by_title(self, client, sample_issue):
        resp = await client.get("/api/v1/issues?search=示例")
        data = resp.json()
        assert any("示例" in i["title"] for i in data["items"])

    @pytest.mark.asyncio
    async def test_combined_filters(self, client, sample_issue):
        resp = await client.get("/api/v1/issues?issue_type=bug&priority=high&status=open")
        data = resp.json()
        for item in data["items"]:
            assert item["issue_type"] == "bug"
            assert item["priority"] == "high"
            assert item["status"] == "open"


class TestIssueTypes:
    """所有问题类型测试"""

    @pytest.mark.asyncio
    async def test_create_all_issue_types(self, client):
        types = ["bug", "feature", "task", "improvement", "documentation"]
        for t in types:
            resp = await client.post("/api/v1/issues", json={
                "title": f"{t} test",
                "issue_type": t,
                "priority": "medium",
            })
            assert resp.status_code == 201, f"Failed for type {t}"
            assert resp.json()["issue_type"] == t


class TestIssueNotFound:
    """404 测试"""

    @pytest.mark.asyncio
    async def test_get_nonexistent_issue(self, client):
        resp = await client.get("/api/v1/issues/99999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_nonexistent_issue(self, client):
        resp = await client.put("/api/v1/issues/99999", json={"title": "updated"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_issue(self, client):
        resp = await client.delete("/api/v1/issues/99999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_add_comment_to_nonexistent_issue(self, client):
        resp = await client.post("/api/v1/issues/99999/comments", json={
            "content": "comment",
        })
        assert resp.status_code == 404


class TestIssueStatusTransitions:
    """状态流转测试"""

    @pytest.mark.asyncio
    async def test_status_open_to_in_progress(self, client, sample_issue):
        resp = await client.put(f"/api/v1/issues/{sample_issue}", json={
            "status": "in_progress",
        })
        assert resp.json()["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_status_in_progress_to_review(self, client, sample_issue):
        await client.put(f"/api/v1/issues/{sample_issue}", json={"status": "in_progress"})
        resp = await client.put(f"/api/v1/issues/{sample_issue}", json={"status": "review"})
        assert resp.json()["status"] == "review"

    @pytest.mark.asyncio
    async def test_status_review_to_closed(self, client, sample_issue):
        await client.put(f"/api/v1/issues/{sample_issue}", json={"status": "review"})
        resp = await client.put(f"/api/v1/issues/{sample_issue}", json={"status": "closed"})
        assert resp.json()["status"] == "closed"


class TestIssueResponseSchema:
    """响应格式回归测试"""

    @pytest.mark.asyncio
    async def test_list_response_has_total_and_items(self, client, sample_issue):
        resp = await client.get("/api/v1/issues")
        data = resp.json()
        assert set(data.keys()) == {"total", "items"}
        assert isinstance(data["total"], int)
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_issue_has_required_fields(self, client, sample_issue):
        resp = await client.get(f"/api/v1/issues/{sample_issue}")
        data = resp.json()
        required = ["id", "title", "issue_type", "status", "priority", "created_at", "updated_at"]
        for field in required:
            assert field in data, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_issue_detail_has_comments(self, client, sample_issue):
        resp = await client.get(f"/api/v1/issues/{sample_issue}")
        data = resp.json()
        assert "comments" in data
        assert isinstance(data["comments"], list)
