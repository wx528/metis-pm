# SSE 跨 Worker 广播

## 优先级: P1
## 状态: open
## 类型: enhancement

## 问题描述

当前 SSE 连接管理使用进程内字典 `_sse_connections`，在多 worker 部署（gunicorn/uvicorn multi-worker）时，通知只会推送到当前 worker 的连接，其他 worker 的新通知无法实时推送。

## 影响范围

- Docker 生产部署时如果使用多 worker，SSE 实时推送失效
- 单 worker 开发环境不受影响

## 建议方案

使用 Redis Pub/Sub 做跨 worker 通知广播：

1. `create_notification` 时发布到 Redis channel
2. 每个 worker 启动时订阅 channel
3. 收到消息后推送到本 worker 的 SSE 连接

## 备选方案

- 使用 SQLite 的 `listen/notify` 替代 Redis（无额外依赖）
- 使用数据库轮询（最简单但有延迟）

## 依赖

需要引入 `redis` 依赖和 Redis 服务，或选择无外部依赖的方案。
