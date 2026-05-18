# Mission01 测试发现的问题

## Bug #1: MCP propose_plan 的 proposed_by 值不兼容 ✅ 已修复

**严重程度**: 中

**描述**: `mcp_server.py` 中 `propose_plan` 函数使用 `_token_cache.get("sub", "ai_agent")` 作为 `proposed_by` 的值，实际传入的是 agent 用户名（如 `codebuddy`），但后端 API 的 `proposed_by` 字段是枚举类型，只接受 `user`/`ai_agent`/`collaborative`，导致 422 错误。

**修复**: 将 `proposed_by` 硬编码为 `"ai_agent"`。`mcp_server.py` 已改为 `"proposed_by": "ai_agent"`。

---

## Bug #2: 后端未重启导致新路由不可用 ✅ 已修复

**严重程度**: 低（运维问题）

**描述**: 代码中已添加 projects、notifications、stats、workflows 路由，但运行中的后端进程未包含这些路由。

**修复**: 已重启后端服务，通过 `/openapi.json` 确认所有路由可用。

---

## Bug #3: MCP 缺少 create_milestone 工具 ✅ 已修复

**严重程度**: 低

**描述**: MCP server 有 `list_milestones` 但没有 `create_milestone`，无法通过 MCP 创建里程碑。

**修复**: 在 `mcp_server.py` 中添加了 `create_milestone` 工具，支持 title、phase、description、project_id、due_date 参数。

---

## Bug #4: MCP 缺少 create_project 工具 ✅ 已修复

**严重程度**: 中

**描述**: MCP server 有 `list_projects` 但没有 `create_project`，无法通过 MCP 创建项目。AI Agent 只能查询项目但不能创建，严重限制了项目初始化能力。

**修复**: 在 `mcp_server.py` 中添加了 `create_project` 工具，支持 name、slug、description、repo_url 参数。
