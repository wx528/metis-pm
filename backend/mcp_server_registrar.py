"""
Project Manager MCP Server - Registrar (项目登记管理员)
负责对机器上散落各处的项目进行登记、信息采集和管理

=== Streamable HTTP 模式配置 ===
{
  "mcpServers": {
    "project-manager-registrar": {
      "url": "http://localhost:9003/mcp",
      "headers": {
        "X-PM-Password": "CHANGE-ME"
      }
    }
  }
}

登记管理员职责：
  - 扫描/发现机器上的项目
  - 登记项目信息（路径、技术栈、语言、框架等）
  - 更新/补充项目信息
  - 归档不再维护的项目
  - 查询已登记项目列表

登记管理员不负责：创建 Issue、管理 Plan、审批等（这些是工人/大副的活）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from typing import Optional

from mcp.server.fastmcp import FastMCP

from mcp_common import (
    API_BASE, _api_request, _current_sub, get_headers,
    PasswordMiddleware,
)

mcp = FastMCP("project-manager-registrar")


# ── 连接 ────────────────────────────────────────────

@mcp.tool()
async def check_connection() -> str:
    """测试登记管理员 MCP Server 与后端 API 的连接是否正常"""
    try:
        headers = await get_headers()
    except RuntimeError as e:
        return f"ERROR: {e}"
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/auth/me", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return f"Connected OK. Identity: {data.get('sub', '?')} (role={data.get('role', '?')}) [Registrar]"
        elif resp.status_code == 401:
            return "ERROR: Token invalid or expired (401). Will re-login on next call."
        else:
            return f"ERROR: API returned {resp.status_code}. Is the backend running?"


# ── 登记 ────────────────────────────────────────────

@mcp.tool()
async def register_project(
    name: str,
    path: str,
    description: str = "",
    tech_stack: str = "",
    repo_url: str = "",
    language: str = "",
    framework: str = "",
    notes: str = "",
) -> str:
    """登记一个项目到系统。如果路径已存在则返回错误。

    Args:
        name: 项目名称
        path: 项目本地路径（必须唯一）
        description: 项目描述
        tech_stack: 技术栈，逗号分隔，如 "Python,React,SQLite"
        repo_url: Git 仓库地址
        language: 主要编程语言
        framework: 使用的框架
        notes: 备注

    Returns:
        登记结果摘要
    """
    payload = {
        "name": name,
        "path": path,
    }
    if description:
        payload["description"] = description
    if tech_stack:
        payload["tech_stack"] = tech_stack
    if repo_url:
        payload["repo_url"] = repo_url
    if language:
        payload["language"] = language
    if framework:
        payload["framework"] = framework
    if notes:
        payload["notes"] = notes

    resp = await _api_request("POST", f"{API_BASE}/project-registrations", json=payload)
    if resp.status_code == 409:
        return f"路径已被登记: {path}。请使用 update_registration 更新已有记录。"
    if resp.status_code >= 400:
        return f"登记失败 ({resp.status_code}): {resp.text}"

    data = resp.json()
    return (
        f"已登记项目 #{data['id']}: {data['name']}\n"
        f"  路径: {data['path']}\n"
        f"  语言: {data.get('language') or '-'} | 框架: {data.get('framework') or '-'}\n"
        f"  技术栈: {data.get('tech_stack') or '-'}\n"
        f"  登记人: {data.get('registered_by') or '-'}\n"
        f"  创建时间: {data.get('created_at')}"
    )


# ── 查询 ────────────────────────────────────────────

@mcp.tool()
async def list_registrations(
    status: str = "active",
    language: str = "",
    tech_stack: str = "",
    registered_by: str = "",
    limit: int = 50,
) -> str:
    """查询已登记的项目列表。

    Args:
        status: 状态筛选，active/archived/stale，默认 active
        language: 按语言筛选（模糊匹配）
        tech_stack: 按技术栈筛选（模糊匹配）
        registered_by: 按登记人筛选
        limit: 返回数量，默认 50

    Returns:
        项目列表
    """
    params: dict = {"limit": limit}
    if status:
        params["status"] = status
    if language:
        params["language"] = language
    if tech_stack:
        params["tech_stack"] = tech_stack
    if registered_by:
        params["registered_by"] = registered_by

    resp = await _api_request("GET", f"{API_BASE}/project-registrations", params=params)
    if resp.status_code >= 400:
        return f"查询失败 ({resp.status_code}): {resp.text}"

    data = resp.json()
    items = data.get("items", [])
    total = data.get("total", 0)

    if not items:
        return "没有找到匹配的项目登记。"

    lines = [f"共 {total} 个项目登记（显示 {len(items)} 个）：\n"]
    for item in items:
        lines.append(
            f"  #{item['id']} {item['name']}\n"
            f"    路径: {item['path']}\n"
            f"    语言: {item.get('language') or '-'} | 框架: {item.get('framework') or '-'} | 技术栈: {item.get('tech_stack') or '-'}\n"
            f"    状态: {item['status']} | 登记人: {item.get('registered_by') or '-'}\n"
            f"    更新时间: {item.get('updated_at')}"
        )
    return "\n".join(lines)


@mcp.tool()
async def get_registration(reg_id: int) -> str:
    """查看项目登记详情。

    Args:
        reg_id: 项目登记 ID

    Returns:
        项目完整信息
    """
    resp = await _api_request("GET", f"{API_BASE}/project-registrations/{reg_id}")
    if resp.status_code == 404:
        return f"项目登记 #{reg_id} 不存在。"
    if resp.status_code >= 400:
        return f"查询失败 ({resp.status_code}): {resp.text}"

    data = resp.json()
    return (
        f"项目登记 #{data['id']}: {data['name']}\n"
        f"  路径: {data['path']}\n"
        f"  描述: {data.get('description') or '-'}\n"
        f"  语言: {data.get('language') or '-'}\n"
        f"  框架: {data.get('framework') or '-'}\n"
        f"  技术栈: {data.get('tech_stack') or '-'}\n"
        f"  仓库: {data.get('repo_url') or '-'}\n"
        f"  状态: {data['status']}\n"
        f"  备注: {data.get('notes') or '-'}\n"
        f"  登记人: {data.get('registered_by') or '-'}\n"
        f"  最后扫描: {data.get('last_scanned_at') or '-'}\n"
        f"  创建时间: {data.get('created_at')}\n"
        f"  更新时间: {data.get('updated_at')}"
    )


# ── 更新 ────────────────────────────────────────────

@mcp.tool()
async def update_registration(
    reg_id: int,
    name: str = "",
    description: str = "",
    tech_stack: str = "",
    repo_url: str = "",
    language: str = "",
    framework: str = "",
    status: str = "",
    notes: str = "",
) -> str:
    """更新项目登记信息。只传需要修改的字段。

    Args:
        reg_id: 项目登记 ID
        name: 项目名称
        description: 项目描述
        tech_stack: 技术栈
        repo_url: Git 仓库地址
        language: 主要编程语言
        framework: 使用的框架
        status: 状态，active/archived/stale
        notes: 备注

    Returns:
        更新结果
    """
    payload: dict = {}
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    if tech_stack:
        payload["tech_stack"] = tech_stack
    if repo_url:
        payload["repo_url"] = repo_url
    if language:
        payload["language"] = language
    if framework:
        payload["framework"] = framework
    if status:
        payload["status"] = status
    if notes:
        payload["notes"] = notes

    if not payload:
        return "没有提供任何更新字段。"

    resp = await _api_request("PUT", f"{API_BASE}/project-registrations/{reg_id}", json=payload)
    if resp.status_code == 404:
        return f"项目登记 #{reg_id} 不存在。"
    if resp.status_code >= 400:
        return f"更新失败 ({resp.status_code}): {resp.text}"

    data = resp.json()
    return (
        f"已更新项目登记 #{data['id']}: {data['name']}\n"
        f"  更新字段: {', '.join(payload.keys())}\n"
        f"  更新时间: {data.get('updated_at')}"
    )


@mcp.tool()
async def mark_scanned(reg_id: int) -> str:
    """标记项目已扫描，更新 last_scanned_at 为当前时间。

    Args:
        reg_id: 项目登记 ID

    Returns:
        标记结果
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    resp = await _api_request(
        "PUT", f"{API_BASE}/project-registrations/{reg_id}",
        json={"last_scanned_at": now},
    )
    if resp.status_code == 404:
        return f"项目登记 #{reg_id} 不存在。"
    if resp.status_code >= 400:
        return f"标记失败 ({resp.status_code}): {resp.text}"

    data = resp.json()
    return f"已标记项目 #{data['id']} ({data['name']}) 为已扫描，时间: {data.get('last_scanned_at')}"


# ── 删除 ────────────────────────────────────────────

@mcp.tool()
async def delete_registration(reg_id: int) -> str:
    """删除项目登记记录。

    Args:
        reg_id: 项目登记 ID

    Returns:
        删除结果
    """
    # 先查名字用于显示
    resp = await _api_request("GET", f"{API_BASE}/project-registrations/{reg_id}")
    if resp.status_code == 404:
        return f"项目登记 #{reg_id} 不存在。"
    name = resp.json().get("name", "?")

    resp = await _api_request("DELETE", f"{API_BASE}/project-registrations/{reg_id}")
    if resp.status_code >= 400:
        return f"删除失败 ({resp.status_code}): {resp.text}"

    return f"已删除项目登记 #{reg_id}: {name}"


# ── 启动 ────────────────────────────────────────────

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "9003"))

    if transport == "streamable-http":
        app = mcp.streamable_http_app()
        from starlette.applications import Starlette
        from starlette.routing import Mount
        starlette_app = Starlette(routes=[Mount("/", app=app)])
        starlette_app = PasswordMiddleware(starlette_app)

        import uvicorn
        uvicorn.run(starlette_app, host=host, port=port)
    elif transport == "sse":
        sse_app = mcp.sse_app()
        sse_app = PasswordMiddleware(sse_app)

        import uvicorn
        uvicorn.run(sse_app, host=host, port=port)
    else:
        mcp.run(transport="stdio")
