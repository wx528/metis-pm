"""
MCP Server 共享模块
统一 MCP Server (mcp_server_unified.py) 的认证、API 请求、中间件、限流、审计
"""
import os
import sys
import time
import json
import logging
from collections import defaultdict
from contextvars import ContextVar
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

API_BASE = os.environ.get("PM_API_URL", "http://localhost:8000/api/v1")
AGENT_PASSWORD = os.environ.get("PM_AGENT_PASSWORD", "")

_request_password: ContextVar[str] = ContextVar("_request_password", default="")
_request_client_ip: ContextVar[str] = ContextVar("_request_client_ip", default="")


def _get_password() -> str:
    return _request_password.get() or AGENT_PASSWORD


_token_cache: dict[str, dict] = {}

# ─── 限流 ────────────────────────────────────────────

# 按角色的限流配置：{role: (max_calls, window_seconds)}
RATE_LIMITS = {
    "agent": (200, 60),       # agent: 200 次/分钟
    "mate": (200, 60),        # mate: 200 次/分钟
    "tester": (100, 60),      # tester: 100 次/分钟
    "registrar": (50, 60),    # registrar: 50 次/分钟
    "admin": (500, 60),       # admin: 500 次/分钟
    "unknown": (30, 60),      # 未识别: 30 次/分钟
}

# 滑动窗口计数器：{identity: [timestamp1, timestamp2, ...]}
_rate_limit_counters: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(identity: str, role: str) -> Optional[str]:
    """检查限流，返回 None 表示通过，返回字符串表示被限流的提示"""
    max_calls, window = RATE_LIMITS.get(role, RATE_LIMITS["unknown"])
    now = time.monotonic()
    counter = _rate_limit_counters[identity]

    # 清理过期记录
    cutoff = now - window
    while counter and counter[0] < cutoff:
        counter.pop(0)

    if len(counter) >= max_calls:
        return f"❌ 请求过于频繁：{role} 角色限制 {max_calls} 次/{window}秒，请稍后再试"

    counter.append(now)
    return None


# ─── 审计日志 ─────────────────────────────────────────

async def _audit_log(tool_name: str, args: dict, result: str, duration_ms: float,
                     identity: str, role: str, success: bool):
    """记录 MCP 工具调用审计日志（写入后端 API）"""
    try:
        # 截断过长的参数和结果
        args_str = json.dumps(args, ensure_ascii=False, default=str)
        if len(args_str) > 500:
            args_str = args_str[:500] + "..."
        result_str = result[:300] if len(result) > 300 else result

        await _api_request("POST", f"{API_BASE}/activity-logs", json={
            "entity_type": "mcp_tool",
            "entity_id": 0,
            "action": tool_name,
            "actor": identity,
            "new_value": {
                "tool": tool_name,
                "args": args_str,
                "result_preview": result_str,
                "duration_ms": round(duration_ms, 1),
                "role": role,
                "client_ip": _request_client_ip.get(""),
                "success": success,
            },
        })
    except Exception as e:
        # 审计日志写入失败不应影响工具执行
        logger.warning(f"Audit log write failed: {e}")


# ─── Token 管理 ───────────────────────────────────────

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
    """API 请求（带重试和指数退避）"""
    password = _get_password()
    headers = kwargs.pop("headers", None) or await get_headers()
    last_exception: Exception | None = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.request(method, url, headers=headers, **kwargs)

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
                wait_time = 1.0 * (2 ** attempt)
                await asyncio.sleep(wait_time)
                continue

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

            # 提取客户端 IP
            client = scope.get("client")
            if client:
                _request_client_ip.set(client[0])
            xff = headers.get(b"x-forwarded-for", b"").decode()
            if xff:
                _request_client_ip.set(xff.split(",")[0].strip())

        await self.app(scope, receive, send)
