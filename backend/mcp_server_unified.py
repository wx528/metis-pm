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
import time
import inspect

sys.path.insert(0, os.path.dirname(__file__))

import httpx
from mcp.server.fastmcp import FastMCP

from mcp_common import (
    API_BASE, _api_request, _current_sub, get_headers,
    PasswordMiddleware, AGENT_PASSWORD, _get_password,
    _token_cache, _cache_key, _check_rate_limit, _audit_log,
)

# 延迟导入 metrics（避免循环依赖）
_mcp_metrics = None

def _get_mcp_metrics():
    global _mcp_metrics
    if _mcp_metrics is None:
        from src.core.metrics import mcp_tool_duration_seconds, mcp_tool_total
        _mcp_metrics = (mcp_tool_duration_seconds, mcp_tool_total)
    return _mcp_metrics

mcp = FastMCP("project-manager")

ROLES = {"agent", "mate", "tester", "registrar", "admin"}


async def _current_role() -> str:
    """通过后端 API 验证密码并获取角色"""
    from src.settings import settings
    pwd = _get_password()
    identity = settings.resolve_identity(pwd)
    if identity:
        _, role = identity
        return role
    return "unknown"


async def _current_identity() -> str:
    """获取当前身份标识（用于限流和审计）"""
    from src.settings import settings
    pwd = _get_password()
    identity = settings.resolve_identity(pwd)
    if identity:
        name, _ = identity
        return name
    return _current_sub()


def require_role(*roles):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            role = await _current_role()
            if role not in roles:
                return f"❌ 权限拒绝：需要角色 {list(roles)}，当前为 '{role}'"

            # 限流检查
            identity = await _current_identity()
            rate_msg = _check_rate_limit(identity, role)
            if rate_msg:
                return rate_msg

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def safe_tool(func):
    """工具函数装饰器：错误处理 + 限流 + 审计日志"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        tool_name = func.__name__
        start = time.monotonic()
        success = True
        result = ""
        role = "unknown"
        identity = "unknown"

        try:
            # 限流检查（safe_tool 在 require_role 之后执行，角色已验证）
            role = await _current_role()
            identity = await _current_identity()
            rate_msg = _check_rate_limit(identity, role)
            if rate_msg:
                return rate_msg

            result = await func(*args, **kwargs)
            return result
        except httpx.ConnectError as e:
            success = False
            result = f"❌ 后端 API 连接失败：{e}。请检查后端服务是否正常运行。"
            return result
        except httpx.TimeoutException as e:
            success = False
            result = f"❌ 后端 API 请求超时：{e}。请稍后重试。"
            return result
        except Exception as e:
            success = False
            result = f"❌ 工具执行出错：{type(e).__name__}: {str(e)}\n请稍后重试或联系管理员。"
            return result
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            # Prometheus 指标
            try:
                duration_s, mcp_total = _get_mcp_metrics()
                duration_s.labels(tool=tool_name, role=role, success=str(success).lower()).observe(duration_ms / 1000)
                mcp_total.labels(tool=tool_name, role=role, success=str(success).lower()).inc()
            except Exception:
                pass
            # 异步写入审计日志（不阻塞返回）
            try:
                import asyncio
                asyncio.create_task(_audit_log(
                    tool_name, kwargs, result, duration_ms,
                    identity, role, success,
                ))
            except Exception:
                pass  # 审计失败不影响工具

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
