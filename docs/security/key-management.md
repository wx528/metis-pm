# SECRET_KEY 和凭据管理指南

## 概述

本文档说明 Project Manager System 中敏感密钥的管理策略，包括 SECRET_KEY、ENCRYPTION_KEY 和密码哈希的生成、存储和轮换。

## 密钥类型

| 密钥 | 用途 | 存储位置 |
|------|------|---------|
| `SECRET_KEY` | JWT Token 签名 | 环境变量 `.env` |
| `ADMIN_PASSWORD_HASH` | Admin 登录验证 | 环境变量 `.env` |
| `AGENT_PASSWORDS_JSON` | Agent 登录验证 | 环境变量 `.env` |
| `ENCRYPTION_KEY` | 服务器凭据加密 | 环境变量 `.env` |

## 生成密钥

### SECRET_KEY

要求：至少 32 个字符的随机字符串

```bash
# Linux/macOS
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### ENCRYPTION_KEY

要求：32 字节的 Base64 编码字符串（用于 Fernet 加密）

```bash
# Python
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 密码哈希

使用 bcrypt 生成密码哈希：

```bash
# Admin 密码
python -c "import bcrypt; print(bcrypt.hashpw('admin_password'.encode(), bcrypt.gensalt()).decode())"

# Agent 密码
python -c "import bcrypt; print(bcrypt.hashpw('agent_password'.encode(), bcrypt.gensalt()).decode())"
```

## .env 文件配置

```bash
# 必需配置
SECRET_KEY="your-64-char-hex-secret-key-here-minimum-32-chars-long!!"
ADMIN_PASSWORD_HASH="$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
AGENT_PASSWORDS_JSON='{"dev1":{"password_hash":"$2b$12$...","role":"agent"},"reviewer1":{"password_hash":"$2b$12$...","role":"mate"}}'
ENCRYPTION_KEY="your-fernet-key-base64-encoded="

# 可选配置
DEBUG=false
DATABASE_URL="sqlite+aiosqlite:///./project_manager.db"
CORS_ORIGINS="http://localhost:5173"
```

## 密钥轮换策略

### 定期轮换

| 密钥 | 建议轮换周期 | 操作 |
|------|------------|------|
| SECRET_KEY | 每 90 天 | 重新生成并重启服务 |
| ENCRYPTION_KEY | 每 180 天 | 解密 → 重新生成 → 重新加密 |
| 密码 | 每 90 天 | 通知用户更新密码 |

### 轮换步骤

1. **SECRET_KEY 轮换**
   ```bash
   # 1. 生成新密钥
   python -c "import secrets; print(secrets.token_hex(32))"
   
   # 2. 更新 .env 文件
   # 3. 重启服务（所有现有 Token 失效，用户需要重新登录）
   ```

2. **ENCRYPTION_KEY 轮换**
   ```bash
   # 1. 备份数据库
   cp project_manager.db project_manager.db.backup.$(date +%Y%m%d)
   
   # 2. 使用旧密钥解密所有凭据
   # 3. 生成新密钥
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   
   # 4. 使用新密钥重新加密
   # 5. 更新 .env 文件
   # 6. 重启服务
   ```

3. **密码轮换**
   ```bash
   # 1. 生成新密码哈希
   python -c "import bcrypt; print(bcrypt.hashpw('new_password'.encode(), bcrypt.gensalt()).decode())"
   
   # 2. 更新 AGENT_PASSWORDS_JSON
   # 3. 通知用户新密码
   # 4. 重启服务（可选，新密码立即生效）
   ```

## 安全最佳实践

### 环境变量安全

1. **文件权限**: `.env` 文件应设置为 600 权限
   ```bash
   chmod 600 .env
   ```

2. **不要提交到 Git**: 确保 `.env` 在 `.gitignore` 中
   ```gitignore
   .env
   *.db
   *.key
   ```

3. **容器安全**: 在 Docker 中使用 secrets 或环境变量注入
   ```yaml
   # docker-compose.yml
   services:
     backend:
       env_file: .env
       secrets:
         - secret_key
   
   secrets:
     secret_key:
       file: ./secrets/secret_key.txt
   ```

### 生产环境建议

1. **使用密钥管理服务**: 考虑使用 HashiCorp Vault、AWS Secrets Manager 或 Azure Key Vault
2. **启用 HTTPS**: 所有 API 通信应通过 HTTPS
3. **Token 过期**: JWT Token 默认 24 小时过期，可根据需要调整
4. **审计日志**: 定期检查 `activity_logs` 表中的异常登录

### 密码复杂度要求

| 类型 | 最小长度 | 要求 |
|------|---------|------|
| Admin 密码 | 12 | 大写、小写、数字、特殊字符 |
| Agent 密码 | 8 | 大写、小写、数字 |
| API Token | 32 | 随机生成 |

## 故障排除

### "SECRET_KEY must be set in .env file"

- 检查 `.env` 文件是否存在
- 确认 `SECRET_KEY` 已设置且长度 ≥ 32

### "ADMIN_PASSWORD_HASH must be set"

- 检查 `ADMIN_PASSWORD_HASH` 是否为有效的 bcrypt 哈希
- 格式应为 `$2b$12$...` 或 `$2a$12$...`

### "Invalid password" 登录失败

- 确认密码正确
- 检查 `AGENT_PASSWORDS_JSON` 格式是否正确
- 确认 bcrypt 哈希与密码匹配

## 工具脚本

项目提供密钥生成工具：

```bash
# 生成所有必需的密钥
python scripts/generate_keys.py
```
