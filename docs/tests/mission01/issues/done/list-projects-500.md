# Bug #5: list_projects API 返回 500 ✅ 已修复

**严重程度**: 中

**发现时间**: 2026-05-17

**修复时间**: 2026-05-18

**状态**: ✅ 已修复

## 问题描述

`GET /api/v1/projects` 不带参数时返回 500 Internal Server Error，但：
- 带过滤参数 `?status=active` 时正常返回 200
- 单个项目查询 `GET /api/v1/projects/{slug}` 正常返回 200

## 根因

1. 数据库 WAL 未正确 checkpoint，导致数据库文件异常
2. `_get_project_stats` 中统计查询在数据异常时抛出未捕获异常

## 修复

- Phase 7 重构后，数据库迁移逻辑更加健壮（`_run_migrations` 增加 `if not exists` 保护）
- `ENCRYPTION_KEY` 配置和凭据加密迁移增加了容错处理
- 后端重启后自动修复，不再出现 500
