# Tailscale 内网部署指南

> 适用版本: v1.0.0+
> 最后更新: 2026-05-28

---

## 一、架构概述

所有设备通过 **Tailscale** 组成虚拟内网，家中服务器作为唯一的 Docker 宿主运行全套服务，其他设备（云机器、工作笔记本）通过 Tailscale IP 或 MagicDNS 域名访问。

```
┌─────────────────┐     Tailscale      ┌─────────────────┐
│   云机器/本机    │ ◄────────────────► │   家中服务器     │
│  (浏览器/Agent)  │    100.x.x.x       │  Docker Compose │
└─────────────────┘                    └────────┬────────┘
                                                │
                           ┌────────────────────┼────────────────────┐
                           ▼                    ▼                    ▼
                      ┌─────────┐        ┌──────────┐         ┌──────────┐
                      │ frontend│        │ backend  │         │  MCP x3  │
                      │  :8080  │        │  :8000   │         │ :9000-2  │
                      └─────────┘        └──────────┘         └──────────┘
                           │                    │
                           └────────────────────┘
                                    SQLite Volume
```

**优势：**
- 无需公网 IP、无需端口暴露到互联网
- 数据全部留存在家服的本地磁盘
- 任意地点的笔记本/云机都能安全接入

---

## 二、前置要求

- 家中服务器已安装 Docker + Docker Compose
- 所有访问设备（家服、云机、本机）已加入**同一个 Tailscale 网络**
- 确认家服的 Tailscale IP：`tailscale ip -4`
- （可选）开启 MagicDNS，记住家服的短域名（如 `homelab.tailxxxxx.ts.net`）

---

## 三、部署步骤

### Step 1: 克隆代码

在家服的 project-manager-system 目录下：

```bash
git pull origin main
```

### Step 2: 准备 .env

```bash
cp .env.example .env
```

编辑 `.env`，**必须修改以下项**：

```env
# 1. 安全密钥（随机 32+ 字符）
SECRET_KEY=your-random-secret-key-here-min-32-chars

# 2. 管理员密码
ADMIN_PASSWORD=your-secure-admin-password

# 3. 加密密钥（用于服务器凭据加密）
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=生成的Fernet密钥

# 4. AI Agent 密码（每个使用 MCP 的 Agent 一个）
AGENT_PASSWORDS=cline:CHANGE-ME,buddy:CHANGE-ME

# 5. 版本号（与根目录 VERSION 保持一致）
APP_VERSION=1.0.0

# 6. 端口（按需修改，避免与家服其他服务冲突）
BACKEND_PORT=8000
FRONTEND_PORT=8080

# 7. Tailscale 关键配置：设为家中服务器的 Tailscale IP
# 查看方式：在家服执行 tailscale ip -4
HOST_IP=100.x.x.x

# 8. CORS（可选：如需多设备通过不同 IP 访问，可显式指定完整列表）
# CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,http://100.x.x.x:8080
```

> **为什么需要 `HOST_IP`**：
> 前端页面运行在浏览器中，它会通过 JavaScript 直接请求后端 API。如果浏览器是通过 `http://100.x.x.x:8080` 访问的前端，那么 API 请求也会被发到 `100.x.x.x:8000`。后端必须允许这个来源，否则会报 CORS 错误。`HOST_IP` 就是干这个的。

### Step 3: 构建并启动

```bash
make up-build
# 或：docker compose up -d --build
```

### Step 4: 验证部署

在家服上：

```bash
docker compose ps

# 健康检查
curl http://localhost:8000/health
# → {"status":"ok","app":"project_manager","version":"1.0.0"}
```

在云机/本机上（确保 Tailscale 已连接）：

```bash
# 用家服的 Tailscale IP 测试后端
curl http://100.x.x.x:8000/health

# 浏览器访问前端
# http://100.x.x.x:8080
```

### Step 5: 首次登录

1. 浏览器打开 `http://100.x.x.x:8080`
2. 使用 `.env` 中 `ADMIN_PASSWORD` 的密码登录

---

## 四、配置 AI Agent（MCP）

AI Agent 运行在本机或云机器上，通过 Tailscale 内网连接到家服的后端。

### 通用配置模板

在任意 AI Agent（CodeBuddy / Cline / Trae 等）的 MCP 设置中添加：

```json
{
  "mcpServers": {
    "project-manager": {
      "command": "python",
      "args": ["D:/AI-learning/project-manager-system/backend/mcp_server.py"],
      "env": {
        "PM_API_URL": "http://100.x.x.x:8000/api/v1",
        "PM_AGENT_PASSWORD": "CHANGE-ME"
      }
    }
  }
}
```

**关键替换项：**
- `args`：改为你本机上 `mcp_server.py` 的绝对路径
- `PM_API_URL`：改为家中服务器的 **Tailscale IP**（不是 localhost）
- `PM_AGENT_PASSWORD`：对应 `.env` 中 `AGENT_PASSWORDS` 的某个密码

### 大副（Mate）配置

```json
{
  "mcpServers": {
    "project-manager-mate": {
      "command": "python",
      "args": ["D:/AI-learning/project-manager-system/backend/mcp_server_mate.py"],
      "env": {
        "PM_API_URL": "http://100.x.x.x:8000/api/v1",
        "PM_AGENT_PASSWORD": "CHANGE-ME"
      }
    }
  }
}
```

### 测试者（Tester）配置

```json
{
  "mcpServers": {
    "project-manager-tester": {
      "command": "python",
      "args": ["D:/AI-learning/project-manager-system/backend/mcp_server_tester.py"],
      "env": {
        "PM_API_URL": "http://100.x.x.x:8000/api/v1",
        "PM_AGENT_PASSWORD": "CHANGE-ME"
      }
    }
  }
}
```

### 验证 MCP 连接

在 AI Agent 对话中请求：

```
请用 check_connection 工具测试连接
```

预期返回：

```
Connected OK. Identity: buddy (role=agent)
```

---

## 五、常用运维操作

### 查看日志

```bash
make logs          # 后端日志
make logs-front    # 前端日志
make logs-all      # 所有服务日志
```

### 重启/更新

```bash
git pull
make up-build
```

### 数据库备份

```bash
docker compose exec backend python -c "
import sqlite3, shutil, datetime, os
src = '/data/project_manager.db'
os.makedirs('/data/backups', exist_ok=True)
ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
dst = f'/data/backups/pm_{ts}.db'
conn = sqlite3.connect(src)
conn.execute(f'VACUUM INTO \"{dst}\"')
conn.close()
print(f'Backup saved: {dst}')
"
```

> 建议设置 cron 每日自动备份：`0 3 * * * cd /path/to/project && docker compose exec -T backend python -c "..."`

### 停止/清理

```bash
make down          # 停止并移除容器（数据保留在 volume 中）
make clean         # ⚠️ 彻底清理（含数据卷，慎用）
```

---

## 六、安全与网络

1. **不暴露公网端口**：家服的 8000/8080/9000-9002 端口只需监听本地网络，Tailscale 负责加密传输
2. **防火墙**：确保家服的操作系统防火墙允许 Docker 容器端口（或限制为 Tailscale 接口 `tailscale0`）
3. **密码强度**：`ADMIN_PASSWORD` 和 `AGENT_PASSWORDS` 必须修改，不要用默认值
4. **ENCRYPTION_KEY**：凭据加密密钥不要泄露，不要提交到 Git
5. **Tailscale ACL**：可通过 Tailscale Admin Console 设置 ACL，限制哪些设备可以访问家服的端口

---

## 七、故障排查

### 前端页面空白，控制台报 CORS 错误

**原因**：`HOST_IP` 未设置或设置错误，后端拒绝跨域请求。

**解决**：
1. 在家服执行 `tailscale ip -4`，获取 100.x.x.x 地址
2. 更新 `.env` 中 `HOST_IP=100.x.x.x`
3. `make restart`

### MCP 连接失败

**原因**：Agent 所在机器无法访问家服的 Tailscale IP，或 `PM_API_URL` 写成了 localhost。

**解决**：
1. 在 Agent 机器上执行 `ping 100.x.x.x`，确认 Tailscale 连通
2. 确认 `PM_API_URL` 使用的是家服的 Tailscale IP，不是 `localhost` 或 `127.0.0.1`

### 容器重启循环

**原因**：通常是 `.env` 中 `SECRET_KEY` 或 `ADMIN_PASSWORD` 未设置，后端启动失败。

**解决**：

```bash
make logs
# 查看报错，补全 .env 中的必填项
```
