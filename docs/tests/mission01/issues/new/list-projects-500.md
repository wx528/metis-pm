# Bug #5: list_projects API 返回 500

**严重程度**: 中

**发现时间**: 2026-05-17 08:13

**状态**: 🔴 待排查

## 问题描述

`GET /api/v1/projects` 不带参数时返回 500 Internal Server Error，但：
- 带过滤参数 `?status=active` 时正常返回 200
- 单个项目查询 `GET /api/v1/projects/{slug}` 正常返回 200

## 复现步骤

```bash
# 1. 登录获取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password":"CHANGE-ME"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

# 2. 列出项目（失败）
curl -s http://localhost:8000/api/v1/projects -H "Authorization: Bearer $TOKEN"
# → 500 Internal Server Error

# 3. 带过滤参数（成功）
curl -s "http://localhost:8000/api/v1/projects?status=active" -H "Authorization: Bearer $TOKEN"
# → 200 OK，返回项目列表

# 4. 单个项目查询（成功）
curl -s http://localhost:8000/api/v1/projects/ai-learning-system -H "Authorization: Bearer $TOKEN"
# → 200 OK
```

## 分析

1. `list_projects` 不带 filter 时走全量查询 + 统计，带 `status` 过滤时结果集可能更小
2. 数据库 `project_manager.db` 在后端重启后大小为 0 字节（可能 WAL 未正确 checkpoint）
3. 猜测：某条 project 记录的统计查询（`_get_project_stats`）中有字段缺失或外键引用异常，导致序列化失败

## 涉及代码

- `backend/src/routes/projects.py` 第 62-91 行 `list_projects` 函数
- `backend/src/routes/projects.py` 第 28-59 行 `_get_project_stats` 统计查询
- `backend/src/models/project.py` Project 模型（含 `default_milestone_id` 外键）
