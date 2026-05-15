# 004 - CommentRead 重复定义且字段不一致

- **优先级**: P1
- **类型**: bug
- **状态**: open

## 问题描述

`CommentRead` 在两个文件中各定义了一次，字段不一致：

- `src/schemas/issue.py` 中的 `CommentRead`：无 `issue_id` 字段
- `src/schemas/comment.py` 中的 `CommentRead`：有 `issue_id` 字段

`IssueReadWithComments` 使用的是 `issue.py` 中的版本，导致通过 Issue 详情返回的评论缺少 `issue_id`，但通过评论 API 直接返回则有——行为不一致。

## 影响文件

- `src/schemas/issue.py` — 第 6-13 行
- `src/schemas/comment.py` — 第 11-19 行

## 修复方案

删除 `issue.py` 中的 `CommentRead` 定义，改为从 `comment.py` 导入统一版本。
