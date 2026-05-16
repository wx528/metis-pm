# SSE 连接内存泄漏与超时清理

## 优先级: P2
## 状态: open
## 类型: enhancement

## 问题描述

`_sse_connections` 是进程内字典，以下场景可能导致连接堆积：

1. 客户端关闭但 `CancelledError` 未触发（网络问题、浏览器崩溃）
2. 长时间不活跃的连接堆积在内存中
3. 无连接上限控制

## 影响范围

- 长期运行后内存缓慢增长
- 极端情况下可能导致 OOM

## 建议方案

1. 添加连接超时机制：如果队列超过一定时间（如 1 小时）没有消费者，自动清理
2. 添加连接数上限：单 recipient 最多 N 个 SSE 连接
3. 定期清理：后台任务扫描并移除死连接
4. 结合 #001 的 Redis Pub/Sub 方案一起优化

## 参考

- `backend/src/core/notification.py` — `_sse_connections` 字典
- `backend/src/routes/notifications.py` — `notification_stream` SSE 端点
