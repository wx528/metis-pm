# 014 — MCP get_server_credentials 调用错误端点，泄露凭据

> 优先级: P0 | 类型: security | 状态: open

## 问题描述

MCP Server 的 `get_server_credentials` 工具存在两个严重问题：

### 1. 调用了错误的端点

```python
@mcp.tool()
async def get_server_credentials(server_id: int) -> str:
    """获取服务器凭据（IP、用户名、密码）"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/servers/{server_id}", headers=get_headers())
        # ...
```

它调用的是 `/servers/{id}`（通用详情接口），而不是专门设计的 `/servers/{id}/credentials` 端点。虽然两者返回的内容目前一样（`ServerRead` 包含 password），但语义上应该用凭据专用接口。

### 2. ServerRead 仍然包含 password 和 ssh_key

`GET /servers/{id}` 返回的 `ServerRead` schema 包含 `password` 和 `ssh_key` 字段：

```python
class ServerRead(BaseModel):
    # ...
    password: Optional[str] = None
    ssh_key: Optional[str] = None
```

这意味着：
- **列表接口** `GET /servers` 也会返回所有服务器的密码和 SSH 密钥
- **MCP 工具** `list_servers` 虽然只显示 IP，但 HTTP 响应中实际包含了密码
- 任何认证用户都可以通过列表接口批量获取所有凭据

### 3. MCP 工具直接将密码打印到 AI Agent 上下文

```python
f"Password: {data.get('password', 'N/A')}\n"
```

密码会进入 AI Agent 的上下文窗口，可能被日志记录或意外泄露。

## 涉及文件

- `backend/mcp_server.py` L302-L316
- `backend/src/schemas/server.py` L46-L60 (`ServerRead`)
- `backend/src/routes/servers.py` L30-L40 (`list_servers`)

## 修复方案

1. **`ServerRead` 移除 `password` 和 `ssh_key` 字段**，列表和详情接口不再返回凭据
2. **凭据只能通过 `/servers/{id}/credentials` 获取**，该接口可考虑增加额外权限检查
3. **MCP `get_server_credentials` 改为调用正确的 credentials 端点**
4. **MCP 工具返回凭据时添加警告**，提示用户密码已进入 AI 上下文
