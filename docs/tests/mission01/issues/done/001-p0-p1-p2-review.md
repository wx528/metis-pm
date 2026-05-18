# Project Manager System v0.7.0 — 项目评审报告（修订版）

> 原始评审基于 v0.6.0，本文件标注 v0.7.0 的修复状态。

## 一、总体评价

这是一个**定位精准、设计有特色**的项目。核心亮点是"人机协作"理念——让 AI Coding Agent 通过 MCP 协议与人类用户在同一平台协同管理项目，这在当前 AI 辅助开发工具爆发的背景下很有价值。从 v0.1.0 到 v0.7.0，7 个 Phase 迭代推进，功能覆盖了 Issue/Milestone/Plan/Server/Workflow/Notification 等完整领域，**交付节奏和质量都不错**。

v0.7.0 完成了安全治理，P0 问题已全部清零，P1/P2 大部分修复。

**综合评分：7.0/10 → 8.5/10**

---

## 二、亮点 ✅

| # | 方面 | 说明 |
|---|------|------|
| 1 | **人机协作理念** | AI Agent 通过 MCP 接入，ActivityLog 精确追踪"谁做了什么"，审批流让人保持控制权 — 定位独特且实用 |
| 2 | **功能完整度** | Issue → Plan → Milestone → Workflow → Notification 形成完整闭环，覆盖项目管理核心场景 |
| 3 | **MCP 工具生态** | 20+ 个 MCP 工具，AI Agent 可创建/查询/更新/审批，开箱即用 |
| 4 | **看板 + 拖拽** | dnd-kit 实现 Drag & Drop，乐观更新 + 失败回滚，用户体验好 |
| 5 | **SSE 实时通知** | 通知铃铛 + 心跳保活 + 断线指数退避重连，实现完整 |
| 6 | **多 Agent 身份** | JWT sub/role 区分 admin/agent，ActivityLog 精确追踪 |
| 7 | **Docker 一键部署** | docker-compose + Nginx + SQLite volume，开箱即用 |

---

## 三、关键问题及修复状态

### 🔴 P0 — 必须修复（✅ 全部已修复）

#### 1. 服务器凭据明文存储 ✅ 已修复
**修复**: 新增 `src/core/crypto.py`，使用 Fernet 对称加密。Server 模型 password/ssh_key 改为 property，写入自动加密，读取自动解密。迁移脚本自动加密已有明文凭据。`ENCRYPTION_KEY` 从环境变量读取。

#### 2. 凭据 API 无角色权限控制 ✅ 已修复
**修复**: `GET /servers/{id}/credentials` 新增 `get_admin_user` 依赖，仅 admin 角色可访问。每次访问自动写入 ActivityLog（action=`credentials_viewed`）。

#### 3. MCP 工具将凭据明文推入 AI 上下文 ✅ 已修复
**修复**: `get_server_credentials` MCP 工具改为仅返回元数据（"密码: 已设置"/"SSH Key: 已设置"），不再返回明文。提示用户通过 Web UI (admin) 查看完整凭据。

#### 4. CORS 配置过宽 ✅ 已修复
**修复**: `allow_methods` 从 `["*"]` 改为 `["GET", "POST", "PUT", "DELETE", "OPTIONS"]`，`allow_headers` 从 `["*"]` 改为 `["Authorization", "Content-Type"]`。

---

### 🟡 P1 — 应该修复

#### 5. 数据库迁移方案脆弱 ⏳ 未修复
引入 Alembic 是架构级改动，建议独立 Phase 处理。

#### 6. SQLite 不适合生产 ⏳ 未修复
架构级改动。当前 SQLAlchemy 抽象层已具备切换条件，生产环境可切换到 PostgreSQL。

#### 7. 工作流引擎 RETRY 策略名不副实 ✅ 已修复
**修复**: `on_failure=RETRY` 实现指数退避重试（最多 3 次，延迟 2s→4s→8s）。重试次数记录在 `run.context` 中。

#### 8. JWT 无过期机制 ✅ 原已存在
经检查，JWT 已有 `exp` 声明（24h 过期），此问题在评审时描述有误。测试已覆盖。

#### 9. MCP Token 缓存无过期处理 ✅ 已修复
**修复**: 新增 `_api_request()` 统一请求函数，401 时自动清缓存→重新登录→重试。所有 20+ 个 MCP 工具统一使用此函数。

---

### 🟢 P2 — 建议改进

#### 10. 测试覆盖不足 ✅ 已改善
新增 `test_security.py`（25 项）和 `test_p1_p2_fixes.py`（17 项），覆盖加密/解密、凭据权限、审计日志、CORS、JWT、工作流 RETRY、check_server、MCP 401 重试等。

#### 11. 错误处理不一致 ✅ 已改善
MCP 工具统一使用 `_api_request()` 发送请求，替代散落的 `httpx.AsyncClient` 直接调用。

#### 12. 前端状态管理 ⏳ 未修复
建议独立 Phase 引入 Zustand/Jotai。

#### 13. `check_server` 功能形同虚设 ✅ 已修复
**修复**: `POST /servers/{id}/check` 新增 TCP 连通性测试。不可达时标记 offline，可连通且之前 offline 时恢复 active。无 IP/端口仅更新 `last_checked_at`。

---

## 四、修复进度汇总

| 优先级 | 问题 | 状态 | 修复版本 |
|--------|------|------|----------|
| P0 | 凭据加密 | ✅ 已修复 | v0.7.0 |
| P0 | 凭据 API 权限控制 | ✅ 已修复 | v0.7.0 |
| P0 | MCP 凭据工具限制 | ✅ 已修复 | v0.7.0 |
| P0 | CORS 收紧 | ✅ 已修复 | v0.7.0 |
| P1 | 引入 Alembic | ⏳ 未修复 | — |
| P1 | JWT 过期 | ✅ 原已存在 | — |
| P1 | RETRY 策略 | ✅ 已修复 | v0.7.0 |
| P1 | MCP 401 处理 | ✅ 已修复 | v0.7.0 |
| P1 | SQLite → PostgreSQL | ⏳ 未修复 | — |
| P2 | 测试覆盖 | ✅ 已改善 | v0.7.0 |
| P2 | 错误处理统一 | ✅ 已改善 | v0.7.0 |
| P2 | 前端状态管理 | ⏳ 未修复 | — |
| P2 | check_server | ✅ 已修复 | v0.7.0 |

**修复率**: 10/13 已修复，3 项为架构级改动留待后续 Phase。
