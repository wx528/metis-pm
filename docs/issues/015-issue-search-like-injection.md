# 015 — Issue 列表搜索 SQL 注入风险

> 优先级: P1 | 类型: security | 状态: open

## 问题描述

Issue 列表接口的 `search` 参数使用了 SQLAlchemy 的 `.contains()` 方法：

```python
if search:
    query = query.where(Issue.title.contains(search) | Issue.description.contains(search))
```

虽然 SQLAlchemy 的 ORM 层面会对参数进行绑定（parameterized query），不会产生经典 SQL 注入，但 `.contains()` 生成的是 `LIKE '%search%'` 语句，存在以下风险：

1. **LIKE 通配符注入**：用户输入 `%` 或 `_` 会被当作 LIKE 通配符，导致意外匹配。例如输入 `%` 会匹配所有记录
2. **性能风险**：`LIKE '%xxx%'` 无法使用索引，大数据量时全表扫描
3. **反斜杠转义**：不同数据库对 `\` 的处理不一致

## 涉及文件

- `backend/src/routes/issues.py` L52-L53

## 修复方案

1. 对 search 参数中的 LIKE 通配符进行转义：

```python
if search:
    escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    query = query.where(
        Issue.title.contains(escaped, autoescape=True) |
        Issue.description.contains(escaped, autoescape=True)
    )
```

2. 或者使用 `ilike` + 手动转义实现更安全的全文搜索
3. 长期考虑引入 SQLite FTS5 全文搜索
