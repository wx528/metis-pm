# 005 - get_db 函数重复定义

- **优先级**: P1
- **类型**: code-quality
- **状态**: open

## 问题描述

`get_db` 函数在两个文件中重复定义：

- `src/core/database.py` — 第 24-29 行
- `src/core/dependencies.py` — 第 1-9 行

所有路由文件都从 `dependencies.py` 导入，`database.py` 中的版本从未被使用。如果只修改了其中一个文件，行为会出现不一致。

## 影响文件

- `src/core/database.py` — 第 24-29 行
- `src/core/dependencies.py` — 全文

## 修复方案

删除 `database.py` 中的 `get_db` 函数，只保留 `dependencies.py` 中的版本。
