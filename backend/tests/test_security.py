"""
P0 安全修复测试：
1. Fernet 加密/解密工具
2. 服务器凭据加密存储
3. 凭据 API 仅 admin 可访问
4. 凭据 API 审计日志
5. agent 角色无法访问凭据
6. CORS 配置收紧
7. JWT 过期机制
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager

from main import app
from src.core.crypto import encrypt_value, decrypt_value


# ── Fixtures ─────────────────────────────────────────


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with LifespanManager(app):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
async def admin_headers(client):
    resp = await client.post("/api/v1/auth/login", json={"password": "testadmin"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def agent_headers(client):
    resp = await client.post("/api/v1/auth/login", json={"password": "agentpass"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def sample_server(client, admin_headers):
    resp = await client.post("/api/v1/servers", json={
        "name": "Test Server",
        "ip_address": "192.168.1.100",
        "port": 22,
        "username": "root",
        "password": "super-secret-password",
        "ssh_key": "-----BEGIN RSA PRIVATE KEY-----\nFAKE_KEY_DATA\n-----END RSA PRIVATE KEY-----",
        "server_type": "web",
        "environment": "production",
    }, headers=admin_headers)
    assert resp.status_code == 201
    return resp.json()["id"]


# ── 1. 加密/解密工具测试 ─────────────────────────────


@pytest.mark.asyncio
async def test_encrypt_decrypt_roundtrip():
    plain = "my-secret-password-123"
    encrypted = encrypt_value(plain)
    assert encrypted != plain
    assert decrypt_value(encrypted) == plain


@pytest.mark.asyncio
async def test_encrypt_none():
    assert encrypt_value(None) is None


@pytest.mark.asyncio
async def test_encrypt_empty_string():
    assert encrypt_value("") == ""


@pytest.mark.asyncio
async def test_decrypt_none():
    assert decrypt_value(None) is None


@pytest.mark.asyncio
async def test_decrypt_empty_string():
    assert decrypt_value("") == ""


@pytest.mark.asyncio
async def test_encrypt_produces_different_ciphertext():
    """相同明文每次加密应产生不同密文（Fernet 包含时间戳）"""
    plain = "same-password"
    enc1 = encrypt_value(plain)
    enc2 = encrypt_value(plain)
    assert enc1 != enc2  # Fernet 内含时间戳，每次不同
    assert decrypt_value(enc1) == plain
    assert decrypt_value(enc2) == plain


@pytest.mark.asyncio
async def test_encrypt_ssh_key():
    key = "-----BEGIN RSA PRIVATE KEY-----\nFAKE\n-----END RSA PRIVATE KEY-----"
    encrypted = encrypt_value(key)
    assert decrypt_value(encrypted) == key


# ── 2. 服务器凭据加密存储 ────────────────────────────


@pytest.mark.asyncio
async def test_server_list_no_credentials_in_response(client, admin_headers, sample_server):
    """列表接口不应包含密码/SSH Key"""
    resp = await client.get("/api/v1/servers", headers=admin_headers)
    assert resp.status_code == 200
    servers = resp.json()
    server = next(s for s in servers if s["id"] == sample_server)
    assert "password" not in server
    assert "ssh_key" not in server
    assert server["has_password"] is True
    assert server["has_ssh_key"] is True


@pytest.mark.asyncio
async def test_server_detail_no_credentials(client, admin_headers, sample_server):
    """详情接口不应包含密码/SSH Key"""
    resp = await client.get(f"/api/v1/servers/{sample_server}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "password" not in data
    assert "ssh_key" not in data
    assert data["has_password"] is True
    assert data["has_ssh_key"] is True


@pytest.mark.asyncio
async def test_credentials_endpoint_returns_decrypted(client, admin_headers, sample_server):
    """凭据端点（admin）返回解密后的明文"""
    resp = await client.get(f"/api/v1/servers/{sample_server}/credentials", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["password"] == "super-secret-password"
    assert "FAKE_KEY_DATA" in data["ssh_key"]


@pytest.mark.asyncio
async def test_server_without_credentials(client, admin_headers):
    """没有凭据的服务器"""
    resp = await client.post("/api/v1/servers", json={
        "name": "No Cred Server",
        "ip_address": "10.0.0.1",
    }, headers=admin_headers)
    assert resp.status_code == 201
    server_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/servers/{server_id}", headers=admin_headers)
    data = resp.json()
    assert data["has_password"] is False
    assert data["has_ssh_key"] is False


@pytest.mark.asyncio
async def test_update_password_encrypts(client, admin_headers, sample_server):
    """更新密码时自动加密"""
    resp = await client.put(
        f"/api/v1/servers/{sample_server}",
        json={"password": "new-password-456"},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    # 通过凭据端点验证新密码已正确加密/解密
    resp = await client.get(f"/api/v1/servers/{sample_server}/credentials", headers=admin_headers)
    data = resp.json()
    assert data["password"] == "new-password-456"


# ── 3. 凭据 API 权限控制 ─────────────────────────────


@pytest.mark.asyncio
async def test_admin_can_access_credentials(client, admin_headers, sample_server):
    resp = await client.get(f"/api/v1/servers/{sample_server}/credentials", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_agent_cannot_access_credentials(client, agent_headers, sample_server):
    """agent 角色应被拒绝 403"""
    resp = await client.get(f"/api/v1/servers/{sample_server}/credentials", headers=agent_headers)
    assert resp.status_code == 403
    assert "Admin access required" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_credentials(client, sample_server):
    """未认证应返回 401"""
    resp = await client.get(f"/api/v1/servers/{sample_server}/credentials")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_agent_can_still_list_servers(client, agent_headers, sample_server):
    """agent 仍可访问服务器列表（不含凭据）"""
    resp = await client.get("/api/v1/servers", headers=agent_headers)
    assert resp.status_code == 200
    servers = resp.json()
    server = next(s for s in servers if s["id"] == sample_server)
    assert "password" not in server
    assert "ssh_key" not in server


@pytest.mark.asyncio
async def test_agent_can_view_server_detail(client, agent_headers, sample_server):
    """agent 仍可查看服务器详情（不含凭据）"""
    resp = await client.get(f"/api/v1/servers/{sample_server}", headers=agent_headers)
    assert resp.status_code == 200


# ── 4. 审计日志 ───────────────────────────────────────


@pytest.mark.asyncio
async def test_credentials_access_creates_audit_log(client, admin_headers, sample_server):
    """访问凭据端点应创建审计日志（凭据端点返回成功即表示审计日志已写入）"""
    resp = await client.get(f"/api/v1/servers/{sample_server}/credentials", headers=admin_headers)
    assert resp.status_code == 200
    # 审计日志在同一个事务中写入，若失败会回滚导致请求失败
    # 进一步验证：直接查询 activity_logs 表
    from sqlalchemy import text
    from src.core.database import engine
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT * FROM activity_logs WHERE entity_type='server' AND action='credentials_viewed' ORDER BY id DESC LIMIT 1")
        )
        row = result.fetchone()
        assert row is not None, "Audit log for credentials_viewed not found"


# ── 5. CORS 配置 ──────────────────────────────────────


@pytest.mark.asyncio
async def test_cors_allowed_methods(client):
    """OPTIONS 预检请求应被允许"""
    resp = await client.options(
        "/api/v1/servers",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_cors_disallowed_method_in_preflight(client):
    """PATCH 方法不在允许列表中"""
    resp = await client.options(
        "/api/v1/servers",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
        },
    )
    # FastAPI CORSMiddleware 会拒绝不允许的方法
    assert resp.status_code != 200 or "PATCH" not in resp.headers.get("access-control-allow-methods", "")


@pytest.mark.asyncio
async def test_cors_allowed_headers_in_preflight(client):
    """Authorization 和 Content-Type 应在允许列表中"""
    resp = await client.options(
        "/api/v1/servers",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert resp.status_code == 200
    assert "Authorization" in resp.headers.get("access-control-allow-headers", "")


@pytest.mark.asyncio
async def test_cors_disallowed_header_in_preflight(client):
    """X-Custom-Header 不在允许列表中"""
    resp = await client.options(
        "/api/v1/servers",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Custom-Header",
        },
    )
    allowed = resp.headers.get("access-control-allow-headers", "")
    assert "X-Custom-Header" not in allowed


# ── 6. Auth 角色系统 + JWT 过期 ──────────────────────


@pytest.mark.asyncio
async def test_admin_role(client, admin_headers):
    resp = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_agent_role(client, agent_headers):
    resp = await client.get("/api/v1/auth/me", headers=agent_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "agent"


@pytest.mark.asyncio
async def test_jwt_has_expiry(client, admin_headers):
    """JWT Token 应包含 exp 过期时间"""
    import jwt
    from src.settings import settings

    token = admin_headers["Authorization"].replace("Bearer ", "")
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert "exp" in payload
    assert "iat" in payload
