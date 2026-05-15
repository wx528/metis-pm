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
async def sample_issue(client, auth_headers):
    resp = await client.post("/api/v1/issues", json={
        "title": "示例 Bug",
        "description": "这是一个测试问题",
        "issue_type": "bug",
        "priority": "high",
        "assignee": "dev1",
        "labels": "backend,urgent",
    }, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_issue(client, auth_headers):
    resp = await client.post("/api/v1/issues", json={
        "title": "新功能需求",
        "description": "需要添加导出功能",
        "issue_type": "feature",
        "priority": "medium",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "新功能需求"
    assert data["status"] == "open"
    assert data["issue_type"] == "feature"


@pytest.mark.asyncio
async def test_list_issues(client, auth_headers, sample_issue):
    resp = await client.get("/api/v1/issues", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_list_issues_with_filter(client, auth_headers, sample_issue):
    resp = await client.get("/api/v1/issues?issue_type=bug", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert all(i["issue_type"] == "bug" for i in data["items"])


@pytest.mark.asyncio
async def test_get_issue(client, auth_headers, sample_issue):
    resp = await client.get(f"/api/v1/issues/{sample_issue}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == sample_issue
    assert data["title"] == "示例 Bug"


@pytest.mark.asyncio
async def test_update_issue(client, auth_headers, sample_issue):
    resp = await client.put(f"/api/v1/issues/{sample_issue}", json={
        "status": "in_progress",
        "assignee": "dev2",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "in_progress"
    assert data["assignee"] == "dev2"


@pytest.mark.asyncio
async def test_delete_issue(client, auth_headers, sample_issue):
    resp = await client.delete(f"/api/v1/issues/{sample_issue}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/issues/{sample_issue}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_comment(client, auth_headers, sample_issue):
    resp = await client.post(f"/api/v1/issues/{sample_issue}/comments", json={
        "content": "这个问题需要优先处理",
        "author": "pm1",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "这个问题需要优先处理"
    assert data["author"] == "pm1"

    resp = await client.get(f"/api/v1/issues/{sample_issue}", headers=auth_headers)
    data = resp.json()
    assert len(data["comments"]) >= 1
