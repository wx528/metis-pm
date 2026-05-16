# 009 - MCP Server 没有身份验证

- **优先级**: P1
- **类型**: security
- **状态**: open

## 问题描述

MCP Server 通过环境变量 `PM_TOKEN` 获取 JWT token，但：

1. 没有验证 token 是否存在或有效
2. 如果 `PM_TOKEN` 为空，所有 API 请求都会因缺少 Authorization header 而返回 401
3. MCP 工具调用失败时，错误信息不够友好，用户不知道是认证问题还是 API 问题

## 影响文件

- `mcp_server.py` — `TOKEN` 变量和 `get_headers()` 函数

## 修复方案

1. 启动时检查 `PM_TOKEN` 是否已设置，未设置则打印配置提示
2. API 调用返回 401 时，提示用户 token 已过期或未配置
3. 提供 `check_connection` MCP 工具让 Agent 测试连接是否正常
