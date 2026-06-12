"""
MCP Server 共享模块
统一 MCP Server (mcp_server_unified.py) 的认证、API 请求、中间件
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from contextvars import ContextVar
from typing import Optional

import httpx

API_BASE = os.environ.get("PM_API_URL", "http://localhost:8000/api/v1")
AGENT_PASSWORD = os.environ.get("PM_AGENT_PASSWORD", "")

_request_password: ContextVar[str] = ContextVar("_request_password", default="")


def _get_password() -> str:
    return _request_password.get() or AGENT_PASSWORD


_token_cache: dict[str, dict] = {}


def _cache_key(password: str) -> str:
    return password


async def _ensure_token() -> str:
    password = _get_password()
    key = _cache_key(password)
    if _token_cache.get(key, {}).get("token"):
        return _token_cache[key]["token"]
    return await _login(password)


async def _login(password: str = "") -> str:
    password = password or _get_password()
    if not password:
        raise RuntimeError("No agent password. Set PM_AGENT_PASSWORD env (stdio) or X-PM-Password header (HTTP).")
    key = _cache_key(password)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/auth/login",
            json={"password": password},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Login failed ({resp.status_code}): {resp.text}")
        data = resp.json()
        _token_cache[key] = {
            "token": data["token"],
            "sub": data.get("sub", "unknown"),
            "role": data.get("role", "unknown"),
        }
        return _token_cache[key]["token"]


import asyncio


async def _api_request(method: str, url: str, *, max_retries: int = 3, **kwargs) -> httpx.Response:
    """API 请求（带重试和指数退避）
    
    自动处理：
    - 401 Token 过期：清缓存重登录
    - 连接错误：指数退避重试
    - 超时：最多重试 3 次
    """
    password = _get_password()
    headers = kwargs.pop("headers", None) or await get_headers()
    last_exception: Exception | None = None
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.request(method, url, headers=headers, **kwargs)
                
                # Token 过期，清缓存重试
                if resp.status_code == 401 and attempt < max_retries - 1:
                    key = _cache_key(password)
                    _token_cache.pop(key, None)
                    headers = await get_headers()
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                    
                return resp
                
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = 1.0 * (2 ** attempt)  # 指数退避：1s, 2s, 4s
                await asyncio.sleep(wait_time)
                continue
    
    # 所有重试耗尽
    raise last_exception or RuntimeError(f"API request failed after {max_retries} retries")


async def get_headers() -> dict:
    token = await _ensure_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def _current_sub() -> str:
    password = _get_password()
    key = _cache_key(password)
    if not _token_cache.get(key, {}).get("sub"):
        await _ensure_token()
    return _token_cache.get(key, {}).get("sub", "ai_agent")


class PasswordMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope.get("headers", []))
            pw = headers.get(b"x-pm-password", b"").decode()
            if pw:
                _request_password.set(pw)
        await self.app(scope, receive, send)
