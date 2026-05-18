# 内网部署指南

> 适用版本: v0.7.0+
> 最后更新: 2026-05-18

---

## 一、前置要求

- Docker + Docker Compose
- 内网服务器一台（如 `192.168.1.100`）
- Python 3.11+（MCP Server 所在机器）

---

## 二、部署步骤

### Step 1: 准备配置文件

```bash
cd project-manager-system

# 复制环境变量模板
cp backend/.env.example .env
```

编辑 `.env`，**必须修改以下项**：

```env
# 1. 生成 SECRET_KEY（随机 32+ 字符）
SECRET_KEY=your-random-secret-key-here-min-32-chars

# 2. 设置管理员密码
ADMIN_PASSWORD=your-secure-admin-password

# 3. 生成 ENCRYPTION_KEY（用于凭据加密）
# 运行以下命令生成：
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=生成的Fernet密钥

# 4. 设置 AI Agent 密码（每个使用 MCP 的 Agent 一个）
AGENT_PASSWORDS=cline:CHANGE-ME,buddy:CHANGE-ME

# 5. CORS 允许的前端地址（内网部署需添加服务器 IP）
CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,http://192.168.1.100:8080
```

### Step 2: 构建并启动

```bash
docker compose up -d --build
```

### Step 3: 验证部署

```bash
# 检查容器状态
docker compose ps

# 检查后端健康
curl http://192.168.1.100:8000/health
# → {"status":"ok","app":"project_manager","version":"0.7.0"}

# 浏览器访问前端
# http://192.168.1.100:8080
```

### Step 4: 首次登录

1. 浏览器打开 `http://192.168.1.100:8080`
2. 使用 `.env` 中 `ADMIN_PASSWORD` 的密码登录
3. 登录后可在仪表盘看到系统信息

---

## 三、配置 AI Agent（MCP）

### 3.1 CodeBuddy 配置

在 CodeBuddy 的 MCP 设置中添加：

```json
{
  "mcpServers": {
    "project-manager": {
      "command": "python",
      "args": ["D:/AI-learning/project-manager-system/backend/mcp_server.py"],
      "env": {
        "PM_API_URL": "http://192.168.1.100:8000/api/v1",
        "PM_AGENT_PASSWORD": "CHANGE-ME"
      }
    }
  }
}
```

> **关键**：`PM_API_URL` 改为内网服务器 IP，`PM_AGENT_PASSWORD` 对应 `.env` 中 `AGENT_PASSWORDS` 的某个密码

### 3.2 Cline 配置

在 Cline 的 MCP 配置中添加相同配置，修改 `PM_AGENT_PASSWORD` 为对应的 agent 密码：

```json
{
  "mcpServers": {
    "project-manager": {
      "command": "python",
      "args": ["D:/AI-learning/project-manager-system/backend/mcp_server.py"],
      "env": {
        "PM_API_URL": "http://192.168.1.100:8000/api/v1",
        "PM_AGENT_PASSWORD": "CHANGE-ME"
      }
    }
  }
}
```

### 3.3 验证 MCP 连接

在 AI Agent 对话中请求：

```
请用 check_connection 工具测试连接
```

预期返回：

```
Connected OK. Identity: buddy (role=agent)
```

---

## 四、常用运维操作

### 查看日志

```bash
# 后端日志
docker compose logs -f backend

# 前端日志
docker compose logs -f frontend
```

### 数据库备份

```bash
# 在服务器上执行
docker compose exec backend python -c "
import sqlite3, shutil, datetime
src = '/data/project_manager.db'
ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
dst = f'/data/backups/pm_{ts}.db'
import os; os.makedirs('/data/backups', exist_ok=True)
conn = sqlite3.connect(src)
conn.execute(f'VACUUM INTO \"{dst}\"')
conn.close()
print(f'Backup saved: {dst}')
"
```

### 更新版本

```bash
git pull
docker compose up -d --build
```

### 停止服务

```bash
docker compose down
# 数据保留在 sqlite_data volume 中，不会丢失
```

### 完全清理（含数据）

```bash
docker compose down -v
# ⚠️ 这会删除所有数据！
```

---

## 五、网络架构

```
浏览器 ──► http://192.168.1.100:8080 ──► Nginx (前端+反代)
                                              │
                                         /api/* ──► FastAPI:8000
                                              │
                                         SQLite Volume
                                             
AI Agent ──► MCP Server ──► http://192.168.1.100:8000/api/v1 ──► FastAPI
```

- **浏览器**：通过 Nginx 8080 端口访问，API 请求由 Nginx 反代到后端（同域，无 CORS 问题）
- **MCP Server**：在 AI Agent 本机运行，直连后端 8000 端口

---

## 六、安全注意事项

1. **修改默认密码**：`.env` 中的 `ADMIN_PASSWORD` 和 `AGENT_PASSWORDS` 必须修改
2. **ENCRYPTION_KEY 保密**：凭据加密密钥泄露等于加密无效，不要提交到 Git
3. **内网隔离**：确保 8000/8080 端口仅内网可访问，不暴露到公网
4. **定期备份**：建议通过 cron 每日自动备份 SQLite
5. **MCP Agent 最小权限**：每个 Agent 只能访问其角色允许的资源（agent 角色无法获取凭据明文）
