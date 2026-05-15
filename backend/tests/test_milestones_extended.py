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
async def sample_milestone(client):
    resp = await client.post("/api/v1/milestones", json={
        "title": "v1.0 发布",
        "description": "首个正式版本",
        "due_date": "2026-06-01",
    })
    assert resp.status_code == 201
    return resp.json()["id"]


class TestMilestoneCRUD:
    """里程碑完整 CRUD 测试"""

    @pytest.mark.asyncio
    async def test_create_milestone_with_due_date(self, client):
        resp = await client.post("/api/v1/milestones", json={
            "title": "v3.0",
            "description": "三期",
            "due_date": "2026-12-31",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "v3.0"
        assert data["due_date"] == "2026-12-31"
        assert data["status"] == "open"

    @pytest.mark.asyncio
    async def test_create_milestone_without_due_date(self, client):
        resp = await client.post("/api/v1/milestones", json={
            "title": "Backlog",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["due_date"] is None

    @pytest.mark.asyncio
    async def test_get_milestone(self, client, sample_milestone):
        resp = await client.get(f"/api/v1/milestones/{sample_milestone}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == sample_milestone
        assert data["title"] == "v1.0 发布"

    @pytest.mark.asyncio
    async def test_update_milestone_title_and_due_date(self, client, sample_milestone):
        resp = await client.put(f"/api/v1/milestones/{sample_milestone}", json={
            "title": "v1.0 正式发布",
            "due_date": "2026-07-01",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "v1.0 正式发布"
        assert data["due_date"] == "2026-07-01"


class TestMilestoneFilters:
    """筛选测试"""

    @pytest.mark.asyncio
    async def test_filter_by_status_open(self, client, sample_milestone):
        resp = await client.get("/api/v1/milestones?status=open")
        data = resp.json()
        assert all(m["status"] == "open" for m in data)

    @pytest.mark.asyncio
    async def test_filter_by_status_closed(self, client, sample_milestone):
        await client.put(f"/api/v1/milestones/{sample_milestone}", json={"status": "closed"})
        resp = await client.get("/api/v1/milestones?status=closed")
        data = resp.json()
        assert all(m["status"] == "closed" for m in data)


class TestMilestoneNotFound:
    """404 测试"""

    @pytest.mark.asyncio
    async def test_get_nonexistent_milestone(self, client):
        resp = await client.get("/api/v1/milestones/99999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_nonexistent_milestone(self, client):
        resp = await client.put("/api/v1/milestones/99999", json={"title": "x"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_milestone(self, client):
        resp = await client.delete("/api/v1/milestones/99999")
        assert resp.status_code == 404


class TestMilestoneResponseSchema:
    """响应格式回归测试"""

    @pytest.mark.asyncio
    async def test_list_returns_array(self, client, sample_milestone):
        resp = await client.get("/api/v1/milestones")
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_milestone_has_required_fields(self, client, sample_milestone):
        resp = await client.get(f"/api/v1/milestones/{sample_milestone}")
        data = resp.json()
        required = ["id", "title", "status", "created_at", "updated_at"]
        for field in required:
            assert field in data, f"Missing field: {field}"
