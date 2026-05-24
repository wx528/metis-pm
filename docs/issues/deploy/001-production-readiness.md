# 内网部署就绪性分析报告

> 分析日期：2026-05-25 | 版本：v0.10.0 | 目标：本地内网生产部署

## 总体评估

| 维度 | 评级 | 说明 |
|------|------|------|
| 功能完整性 | ✅ 可用 | 核心功能齐全，MCP 工具链完整 |
| 安全性 | ⚠️ 需改进 | 密码明文存储于 .env，无 HTTPS，无速率限制 |
| 数据可靠性 | ⚠️ 需改进 | SQLite 单文件，无自动备份，无 WAL 模式 |
| 运维可观测性 | ⚠️ 需改进 | 有基础日志，无监控告警，无结构化日志 |
| 高可用性 | ❌ 缺失 | 单点部署，无健康自愈，restart 策略偏弱 |

**结论：功能层面可以部署使用，但安全性和数据可靠性需要先做加固。**

---

## P0 — 必须在部署前修复

### P0-1: SECRET_KEY 使用开发默认值

**位置**: `.env` 第 1 行
**现状**: `SECRET_KEY=dev-secret-key-change-in-production-min-32-chars`
**风险**: JWT 签名密钥泄露 → 任何人可伪造 admin token，完全接管系统
**修复**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# 将输出写入 .env 的 SECRET_KEY
```

### P0-2: ADMIN_PASSWORD 使用弱密码

**位置**: `.env` 第 2 行
**现状**: `ADMIN_PASSWORD=CHANGE-ME`
**风险**: 任何人可用 "admin" 登录管理后台
**修复**: 设置强密码（≥12 位，含大小写+数字+特殊字符）

### P0-3: ENCRYPTION_KEY 未设置

**位置**: `.env`（缺失）
**现状**: 未配置 `ENCRYPTION_KEY`
**风险**: 服务器凭据（password/ssh_key）无法加密存储，`get_server_credentials` 功能不可用
**修复**:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# 将输出写入 .env 的 ENCRYPTION_KEY
```

### P0-4: 全链路 HTTP 明文传输

**位置**: 全栈（backend:8000, frontend:80, mcp:9000）
**现状**: 所有服务均为 HTTP，密码、JWT token、服务器凭据均明文传输
**风险**: 内网嗅探可截获所有敏感数据
**修复方案**（二选一）:
- **方案 A（推荐）**: 在前端加 Nginx 反向代理层，配置 TLS 证书（内网可用自签或内部 CA）
- **方案 B**: 在 docker-compose 中加 Caddy/Nginx 容器做 TLS 终结

### P0-5: MCP Server 端口直接暴露

**位置**: `docker-compose.yml` 第 48 行
**现状**: `MCP_PORT=9000` 直接映射到宿主机 `0.0.0.0`
**风险**: 内网任何人知道 MCP 地址即可尝试用 agent 密码操作系统
**修复**: 根据部署场景选择方案

```yaml
# 方案 1: Agent 全部在同一台服务器上运行（stdio 模式）
# → 不暴露端口，删除 ports 映射即可

# 方案 2: Agent 从其他内网机器远程访问（Streamable HTTP 模式）
# → 保持端口暴露，但通过以下方式加固：
ports:
  - "${MCP_PORT:-9000}:9000"
# 加固措施：
#   a) 强 agent 密码（已在 AGENT_PASSWORDS 中配置）
#   b) 服务器防火墙限制 9000 端口仅允许特定 IP 访问
#   c) 后续配合 HTTPS 反向代理加密传输
```

> **注意**: 如果 Agent 从本机远程访问 MCP（Streamable HTTP 模式），**不能**绑定 `127.0.0.1`，
> 否则只有服务器本机进程能访问。应保持 `0.0.0.0` 暴露，用认证 + 防火墙保护。

---

## P1 — 部署后尽快修复

### P1-1: 无 API 速率限制

**位置**: `backend/main.py` — 无 rate limit 中间件
**现状**: 登录接口无任何频率限制
**风险**: 暴力破解 admin/agent 密码
**修复**: 引入 `slowapi` 或 FastAPI 内置限流

```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, data: LoginRequest):
    ...
```

### P1-2: SQLite 未启用 WAL 模式

**位置**: `backend/src/core/database.py`
**现状**: 使用默认 journal 模式
**风险**: 并发写入时锁竞争严重，SSE 推送 + Agent 操作 + 用户操作同时进行时可能超时
**修复**: 在 `lifespan` 中启用 WAL

```python
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA busy_timeout=5000"))
        await _run_migrations(conn)
    yield
```

### P1-3: 无自动数据库备份

**位置**: `backend/backup.sh` 存在但未集成到 docker-compose
**现状**: 备份脚本存在，但无定时任务、无 volume 挂载
**风险**: 数据库文件损坏/误删 = 数据全丢
**修复**:
1. 在 docker-compose 中挂载备份 volume
2. 添加定时备份容器或 cron

```yaml
volumes:
  sqlite_data:
  backup_data:

services:
  backend:
    volumes:
      - sqlite_data:/data
      - backup_data:/backups
    # ... 添加 cron 或在 entrypoint 中启动定时任务
```

### P1-4: JWT Token 无刷新机制

**位置**: `backend/src/routes/auth.py` 第 32 行
**现状**: Token 24h 过期，无 refresh token
**风险**: Agent 长时间运行时 token 过期，MCP Server 需重新登录（已有 401 重试逻辑，但体验不佳）
**修复**: 增加 refresh token 或延长 agent token 有效期

### P1-5: restart 策略偏弱

**位置**: `docker-compose.yml`
**现状**: `restart: on-failure`
**风险**: 服务器重启后服务不会自动恢复
**修复**: 改为 `restart: unless-stopped`

```yaml
services:
  backend:
    restart: unless-stopped
  mcp:
    restart: unless-stopped
  frontend:
    restart: unless-stopped
```

### P1-6: SSE 连接无上限保护

**位置**: `backend/src/core/notification.py`
**现状**: `_sse_connections` 字典无大小限制
**风险**: 恶意或异常客户端可建立大量 SSE 连接，耗尽内存
**修复**: 添加连接数上限

```python
MAX_SSE_CONNECTIONS_PER_USER = 5

def register_sse_connection(recipient: str, queue: asyncio.Queue):
    if recipient not in _sse_connections:
        _sse_connections[recipient] = []
    if len(_sse_connections[recipient]) >= MAX_SSE_CONNECTIONS_PER_USER:
        # 关闭最旧的连接
        oldest = _sse_connections[recipient].pop(0)
        oldest.put_nowait(None)  # 发送关闭信号
    _sse_connections[recipient].append(queue)
```

---

## P2 — 持续改进

### P2-1: 无结构化日志

**现状**: 使用 Python 标准 `logging`，输出纯文本
**建议**: 引入 `structlog` 或 JSON 格式日志，方便 ELK/Loki 采集

### P2-2: 无健康检查告警

**现状**: docker-compose 有 healthcheck，但无外部监控
**建议**: 配置 Prometheus + Alertmanager，或使用 Uptime Kuma 监控 `/health` 端点

### P2-3: 前端无构建优化

**位置**: `frontend/Dockerfile`
**现状**: 每次构建都重新 `npm install`
**建议**: 添加 `.dockerignore` 排除 `node_modules`（已有），利用 Docker layer cache 优化

### P2-4: CORS 配置需更新

**位置**: `.env` + `docker-compose.yml`
**现状**: `CORS_ORIGINS` 通过 docker-compose 环境变量拼接，格式复杂
**建议**: 在 `.env` 中直接配置完整的 CORS_ORIGINS

```env
# 内网部署示例
CORS_ORIGINS=http://192.168.1.100:8099,http://localhost:8099
```

### P2-5: MCP Server 无请求日志

**位置**: `backend/mcp_server.py`
**现状**: MCP 工具调用无审计日志
**建议**: 在 `_api_request` 中添加调用日志，记录 agent 身份 + 操作 + 时间

### P2-6: 前端 Nginx 无 gzip

**位置**: `frontend/nginx.conf`
**现状**: 未启用 gzip 压缩
**建议**: 添加 gzip 配置减少传输体积

```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml;
gzip_min_length 1024;
```

---

## 部署 Checklist

部署前逐项确认：

- [ ] 生成并设置 `SECRET_KEY`（≥32 字符随机串）
- [ ] 设置强 `ADMIN_PASSWORD`
- [ ] 生成并设置 `ENCRYPTION_KEY`
- [ ] 配置 `CORS_ORIGINS` 为实际前端访问地址
- [ ] MCP 端口绑定到 `127.0.0.1` 或不暴露
- [ ] 将 `restart` 策略改为 `unless-stopped`
- [ ] 配置 SQLite WAL 模式
- [ ] 设置自动数据库备份
- [ ] （可选）配置 HTTPS 反向代理
- [ ] （可选）配置 API 速率限制

## 快速部署命令

```bash
# 1. 生成密钥
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"

# 2. 编辑 .env，填入上述密钥 + 强 ADMIN_PASSWORD + CORS_ORIGINS

# 3. 启动
docker compose up -d

# 4. 验证
curl http://localhost:8098/health
curl http://localhost:8099/

# 5. 首次备份
docker exec pm-backend python scripts/backup_db.py
```
