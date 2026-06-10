"""
Project Manager MCP Server - Unified
Combines all roles: agent, mate, tester, registrar

=== Streamable HTTP 模式配置 ===
{
  "mcpServers": {
    "project-manager": {
      "url": "http://localhost:9000/mcp",
      "headers": {
        "X-PM-Password": "your-password"
      }
    }
  }
}

角色通过 AGENT_PASSWORDS 环境变量解析：identity:password,...
identity 包含 mate/tester/registrar 关键词则对应角色，否则为 agent
"""
import functools
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import httpx
from mcp.server.fastmcp import FastMCP

from mcp_common import (
    API_BASE, _api_request, _current_sub, get_headers,
    PasswordMiddleware, AGENT_PASSWORD, _get_password,
    _token_cache, _cache_key,
)

mcp = FastMCP("project-manager")

ROLES = {"agent", "mate", "tester", "registrar", "admin"}


def get_role_by_password(password: str) -> str:
    passwords = os.environ.get("AGENT_PASSWORDS", "")
    for entry in passwords.split(","):
        if ":" not in entry:
            continue
        identity, pwd = entry.strip().split(":", 1)
        if pwd == password:
            identity_lower = identity.lower()
            if "mate" in identity_lower:
                return "mate"
            if "tester" in identity_lower:
                return "tester"
            if "registrar" in identity_lower:
                return "registrar"
            return "agent"
    return "unknown"


async def _current_role() -> str:
    pwd = _get_password()
    return get_role_by_password(pwd)


def require_role(*roles):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            role = await _current_role()
            if role not in roles:
                return f"❌ 权限拒绝：需要角色 {list(roles)}，当前为 '{role}'"
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def safe_tool(func):
    """工具函数错误处理装饰器：捕获异常，防止 MCP Server 崩溃"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except httpx.ConnectError as e:
            return f"❌ 后端 API 连接失败：{e}。请检查后端服务是否正常运行。"
        except httpx.TimeoutException as e:
            return f"❌ 后端 API 请求超时：{e}。请稍后重试。"
        except Exception as e:
            import traceback
            return f"❌ 工具执行出错：{type(e).__name__}: {str(e)}\n请稍后重试或联系管理员。"
    return wrapper


# ═══════════════════════════════════════════════════════
#  注册所有角色的工具
# ═══════════════════════════════════════════════════════

from mcp_tools import register_all_tools

register_all_tools(mcp, require_role, safe_tool)


# ═══════════════════════════════════════════════════════
#  启动入口
# ═══════════════════════════════════════════════════════

MCP_PORT = int(os.environ.get("MCP_PORT", "9000"))
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio")


def main():
    if MCP_TRANSPORT == "sse":
        mcp.settings.host = MCP_HOST
        mcp.settings.port = MCP_PORT
        app = PasswordMiddleware(mcp.sse_app())
        import uvicorn
        uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
    elif MCP_TRANSPORT == "streamable-http":
        mcp.settings.host = MCP_HOST
        mcp.settings.port = MCP_PORT
        app = PasswordMiddleware(mcp.streamable_http_app())
        import uvicorn
        uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
