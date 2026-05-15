# 002 - 服务器密码明文存储且 API 完整返回

- **优先级**: P0
- **类型**: security
- **状态**: open

## 问题描述

1. `Server` 模型中 `password` 和 `ssh_key` 以明文存储在数据库中
2. `ServerRead` schema 直接将 `password` 和 `ssh_key` 完整返回给前端，无脱敏
3. MCP `get_server_credentials` 工具直接将密码暴露给 AI Agent

## 影响文件

- `src/models/server.py` — 明文字段
- `src/schemas/server.py` — `ServerRead` 直接返回 password/ssh_key
- `mcp_server.py` — `get_server_credentials` 工具

## 修复方案

**短期**（当前阶段，仅本地/内网）：
- `ServerRead` 中 `password` 默认显示为 `***`，前端点击才请求完整值
- 新增 `GET /servers/{id}/credentials` 端点，单独返回凭据

**中期**（如需公网部署）：
- 使用 `cryptography.fernet` 加密存储
- SSH 私钥不应通过 API 返回

## 备注

设计文档已明确"明文存储，仅本地/内网使用"，但 API 返回时至少应脱敏。
