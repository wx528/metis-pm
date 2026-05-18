# 资源管理 + 商业谋划

> 日期: 2026-05-18

## 1. 资源管理 — 服务器配置、到期时间

**优先级: P2（中期）**

### 已具备

- Server 模型（IP、名称、描述、凭据）
- MCP `list_servers` / `get_server_credentials`
- 工作流定时触发 + 通知

### 待补充

Server 模型新增字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `instance_type` | str | 如 "4C8G"、"t3.medium" |
| `provider` | str | 如 "aliyun"、"aws"、"self-hosted" |
| `region` | str | 如 "cn-beijing" |
| `expire_at` | datetime | 到期时间 |
| `cost_monthly` | float | 月费用 |
| `status` | str | running / expired / archived |

### 实现路径

1. **字段扩展**：Server 模型加字段 + API 更新 + 前端展示
2. **到期提醒**：工作流 schedule 触发 → 检查 expire_at → 通知
3. **成本看板**：配合数据看板展示资源成本

---

## 2. 商业谋划 — AI 资源分配建议

**优先级: P3（不紧急）**

### 拆解

| 子功能 | 评估 | 说明 |
|--------|------|------|
| 到期/成本预警 | ⭐⭐⭐⭐ 高 | 资源字段有了之后自然实现，规则简单 |
| 资源分配建议 | ⭐⭐⭐ 中 | Agent + MCP 可实现，不需要新模块 |
| 商业战略谋划 | ❌ 超出边界 | 不是 PM 系统职责，属于 BI/战略工具 |

### 资源分配建议实现思路

不需要新模块，Agent + MCP 即可编排：

```
Agent 查询 → list_servers（配置+成本）+ list_projects（需求）
         → LLM 分析 → 输出建议到 Issue/Plan
```

### 不做

- 商业战略谋划 — 超出 PM 系统边界，应该是独立 BI 工具的职责
