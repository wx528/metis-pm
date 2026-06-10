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


@pytest.fixture
async def sample_milestone(client, auth_headers):
    resp = await client.post("/api/v1/milestones", json={
        "title": "v1.0 发布",
        "description": "首个正式版本",
        "due_date": "2026-06-01",
    }, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_milestone(client, auth_headers):
    resp = await client.post("/api/v1/milestones", json={
        "title": "v2.0 规划",
        "description": "二期功能",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "v2.0 规划"
    assert data["status"] == "open"


@pytest.mark.asyncio
async def test_list_milestones(client, auth_headers, sample_milestone):
    resp = await client.get("/api/v1/milestones", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_update_milestone(client, auth_headers, sample_milestone):
    resp = await client.put(f"/api/v1/milestones/{sample_milestone}", json={
        "status": "closed",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "closed"


@pytest.mark.asyncio
async def test_delete_milestone(client, auth_headers, sample_milestone):
    resp = await client.delete(f"/api/v1/milestones/{sample_milestone}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/milestones/{sample_milestone}", headers=auth_headers)
    assert resp.status_code == 404
