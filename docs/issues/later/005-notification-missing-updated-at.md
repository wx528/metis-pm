# Notification 模型缺少 updated_at 字段

## 优先级: P2
## 状态: open
## 类型: enhancement

## 问题描述

Notification 模型只有 `created_at`，没有 `updated_at` 字段。而项目中几乎所有其他模型（Issue、Plan、Project、Milestone 等）都有 `updated_at`。标记已读等操作无法追踪时间。

## 影响范围

- 无法知道通知被标记已读的时间
- 与其他模型不一致

## 建议方案

1. 在 `Notification` 模型添加 `updated_at = Column(DateTime, default=..., onupdate=...)`
2. 添加数据库迁移逻辑（检测列是否存在，不存在则添加）
3. 在 `mark_read` 和 `mark_all_read` 操作时自动更新

## 文件

- `backend/src/models/notification.py`
- `backend/src/routes/notifications.py`
