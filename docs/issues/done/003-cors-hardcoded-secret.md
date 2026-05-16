# 003 - CORS 允许所有来源 + 硬编码密钥

- **优先级**: P1
- **类型**: security
- **状态**: open

## 问题描述

### 3a. CORS 配置不安全

`main.py` 中 `allow_origins=["*"]` 配合 `allow_credentials=True`。浏览器规范不允许 credentials 为 True 时使用通配符 origin，这种组合极其危险——允许任何网站携带用户凭据访问 API。

### 3b. 硬编码的 SECRET_KEY 和 ADMIN_PASSWORD

`settings.py` 中：
- `SECRET_KEY` 默认值 `project-manager-secret-key-change-in-production`
- `ADMIN_PASSWORD` 默认值 `admin`

`.env` 文件中未覆盖这两个值。

### 3c. 缺少 .env.example

项目没有 `.env.example` 模板文件，新用户不知道需要配置哪些环境变量。

## 影响文件

- `backend/main.py` — CORS 配置
- `backend/src/settings.py` — 默认密钥值
- `backend/.env` — 缺少 SECRET_KEY/ADMIN_PASSWORD

## 修复方案

1. CORS：`allow_origins=["http://localhost:5173"]` 或通过环境变量配置
2. settings.py：`SECRET_KEY` 和 `ADMIN_PASSWORD` 不设默认值，启动时未配置则抛异常
3. 创建 `.env.example` 模板
