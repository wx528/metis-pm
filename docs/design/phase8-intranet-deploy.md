# Phase 8 设计：内网部署 + MCP 升级

> 版本: v0.8.0
> 日期: 2026-05-18
> 状态: 设计中

---

## 一、背景

当前系统（v0.7.0）仅适用于本地开发环境，存在以下限制：

1. **MCP 配置使用本地路径和 localhost**，无法在内网多机环境使用
2. **CORS_ORIGINS 硬编码 localhost**，内网其他机器无法访问
3. **docker-compose 中 CORS 只允许 localhost**，前端在 8080 端口但 CORS 写的也是 localhost
4. **MCP 文档过时**，仍使用 `PM_TOKEN` 而非 `PM_AGENT_PASSWORD`，工具列表不完整
5. **缺少生产级部署配置**（HTTPS、健康检查、日志、备份）

---

## 二、需要变更的内容

### 2.1 MCP Server 配置升级

#### 现状问题

| 问题 | 说明 |
|------|------|
| `PM_API_URL` 硬编码 localhost | 内网其他机器无法连接 |
| 旧文档使用 `PM_TOKEN` | 实际代码已改为 `PM_AGENT_PASSWORD` 自动登录 |
| 工具列表不完整 | 缺少 create_project、create_milestone、create_workflow、trigger_workflow 等 |
| `get_server_credentials` 描述过时 | 仍写"获取用户名/密码"，实际已改为元数据 |

#### 变更方案

**mcp_server.py 无需代码改动**，仅需更新文档和配置模板：

```json
// 内网部署 MCP 配置示例
{
  "mcpServers": {
    "project-manager": {
      "command": "python",
      "args": ["D:/AI-learning/project-manager-system/backend/mcp_server.py"],
      "env": {
        "PM_API_URL": "http://192.168.1.100:8000/api/v1",
        "PM_AGENT_PASSWORD": "your-agent-password"
      }
    }
  }
}
```

> 关键变更：`PM_API_URL` 改为内网服务器 IP，`PM_TOKEN` 废弃改用 `PM_AGENT_PASSWORD`

### 2.2 CORS 配置

#### 现状问题

```yaml
# docker-compose.yml 当前
CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080
```

内网其他机器通过 `http://192.168.1.100:8080` 访问前端时，浏览器会因 CORS 被拒绝。

#### 变更方案

CORS 应允许前端所在服务器的所有访问方式：

```
# .env
CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,http://192.168.1.100:8080
```

更好的方案：**通过 Nginx 统一入口，前端和 API 同域**，彻底消除 CORS 问题。

### 2.3 Nginx 反向代理优化

#### 现状问题

当前 Nginx 仅做简单代理，缺少：
- 内网 IP 绑定
- 请求体大小限制
- 安全头
- 健康检查端点

#### 变更方案

```nginx
server {
    listen 80;
    server_name _;  # 内网不需要域名，接受所有请求

    # 安全头
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-XSS-Protection "1; mode=block";

    # 请求体大小限制
    client_max_body_size 10m;

    # 前端静态文件
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    location /assets/ {
        expires 1h;
        add_header Cache-Control "public, must-revalidate";
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_read_timeout 86400s;
    }

    # 健康检查
    location /health {
        proxy_pass http://backend:8000/health;
    }
}
```

### 2.4 docker-compose 升级

#### 现状问题

| 问题 | 说明 |
|------|------|
| `APP_VERSION` 硬编码 0.6.0 | 应自动从 VERSION 文件读取 |
| 无 ENCRYPTION_KEY 配置 | v0.7.0 新增的必需配置 |
| 无 AGENT_PASSWORDS | MCP Agent 登录需要 |
| 无健康检查 | 容器挂掉无法自动发现 |
| 无日志配置 | 默认 json 日志，不方便查看 |
| 无数据库备份策略 | SQLite volume 无备份 |

#### 变更方案

```yaml
services:
  backend:
    build: ./backend
    container_name: pm-backend
    ports:
      - "8000:8000"
    volumes:
      - sqlite_data:/data
    env_file:
      - .env
    environment:
      - DATABASE_URL=sqlite+aiosqlite:////data/project_manager.db
      - CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080
      - DEBUG=false
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  frontend:
    build:
      context: ./frontend
      args:
        APP_VERSION: "0.7.0"
    container_name: pm-frontend
    ports:
      - "8080:80"
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "5m"
        max-file: "3"

volumes:
  sqlite_data:
```

### 2.5 .env 完整配置模板

```env
# ===== 必填 =====
SECRET_KEY=change-me-to-a-random-32-char-string
ADMIN_PASSWORD=change-me-to-a-secure-admin-password
ENCRYPTION_KEY=change-me-generate-with-fernet

# Agent 密码（格式: agent_name:password, 逗号分隔）
# 每个使用 MCP 的 AI Agent 用自己的密码获取 JWT 身份
AGENT_PASSWORDS=cline:CHANGE-ME,buddy:CHANGE-ME

# ===== 可选 =====
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:////data/project_manager.db

# CORS：允许访问前端的所有地址（逗号分隔）
# 内网部署时需添加服务器 IP
CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,http://192.168.1.100:8080
```

### 2.6 MCP 文档更新

更新 `docs/mcp-config.md`：
- 废弃 `PM_TOKEN`，全面使用 `PM_AGENT_PASSWORD`
- 更新内网部署配置示例
- 更新工具列表（新增 8 个工具）
- 更新安全注意事项（凭据已加密）

### 2.7 SQLite 备份脚本

```bash
#!/bin/bash
# backup.sh — SQLite 数据库备份
BACKUP_DIR="/data/backups"
DB_FILE="/data/project_manager.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=7

mkdir -p $BACKUP_DIR

# 使用 sqlite3 一致性备份
sqlite3 "$DB_FILE" ".backup '$BACKUP_DIR/pm_$TIMESTAMP.db'"

# 清理旧备份
find $BACKUP_DIR -name "pm_*.db" -mtime +$KEEP_DAYS -delete

echo "Backup completed: pm_$TIMESTAMP.db"
```

---

## 三、变更清单

| # | 文件 | 变更 | 优先级 |
|---|------|------|--------|
| 1 | `docs/mcp-config.md` | 全面更新：PM_AGENT_PASSWORD、内网配置、工具列表、安全说明 | P0 |
| 2 | `docker-compose.yml` | 增加健康检查、日志、ENCRYPTION_KEY、APP_VERSION | P0 |
| 3 | `frontend/nginx.conf` | 增加安全头、请求体限制、健康检查代理 | P1 |
| 4 | `.env.example` → `.env.production` | 新增生产环境配置模板 | P0 |
| 5 | `backend/backup.sh` | 新增 SQLite 备份脚本 | P1 |
| 6 | `docs/deploy-guide.md` | 新增内网部署指南 | P0 |
| 7 | `docker-compose.yml` CORS | 动态读取或文档说明 | P1 |

---

## 四、内网部署架构

```
┌─────────────────────────────────────────────────┐
│                内网 192.168.1.100                │
│                                                 │
│  ┌──────────┐  80   ┌──────────┐  8000         │
│  │  Nginx   │◄──────┤  FastAPI  │               │
│  │ (前端+   │  /api │  (后端)   │               │
│  │  反代)   │──────►│           │               │
│  └──────────┘       └─────┬────┘               │
│       ▲                   │                     │
│       │              ┌────▼────┐                │
│       │              │ SQLite  │                │
│       │              │ Volume  │                │
│       │              └─────────┘                │
│       │                                         │
│  浏览器访问 http://192.168.1.100:8080            │
│                                                 │
└─────────────────────────────────────────────────┘
         │
         │ 内网
         ▼
┌─────────────────────────────────────────────────┐
│  AI Agent 开发机 (如 192.168.1.50)              │
│                                                 │
│  MCP Server ──► PM_API_URL=http://192.168.1.100:8000/api/v1
│                PM_AGENT_PASSWORD=<agent-password>
│                                                 │
└─────────────────────────────────────────────────┘
```

**关键点**：
- 浏览器通过 `http://192.168.1.100:8080` 访问前端（Nginx）
- API 请求由 Nginx 反代到后端，**同域无 CORS 问题**
- MCP Server 在 AI Agent 开发机上运行，直连后端 8000 端口

---

## 五、MCP 完整工具列表（v0.7.0）

| 工具 | 功能 | 新增 |
|------|------|------|
| `check_connection` | 连接测试 | |
| `list_projects` | 列出项目 | |
| `create_project` | 创建项目 | ✅ |
| `create_issue` | 创建 Issue | |
| `list_issues` | 查询 Issues | |
| `update_issue_status` | 更新状态 | |
| `update_issue_priority` | 更新优先级 | |
| `defer_issue` | 暂缓 Issue | |
| `add_issue_comment` | 添加评论 | |
| `propose_plan` | 提议计划 | |
| `list_plans` | 查询计划 | |
| `update_plan_progress` | 更新计划进度 | |
| `list_milestones` | 查询里程碑 | |
| `create_milestone` | 创建里程碑 | ✅ |
| `list_servers` | 查询服务器 | |
| `get_server_credentials` | 查询凭据元数据 | ✅ 改版 |
| `check_notifications` | 检查通知 | |
| `mark_notification_read` | 标记已读 | |
| `list_workflows` | 列出工作流 | ✅ |
| `create_workflow` | 创建工作流 | ✅ |
| `trigger_workflow` | 触发工作流 | ✅ |
| `list_workflow_runs` | 查看执行记录 | ✅ |

共 **22** 个工具。
