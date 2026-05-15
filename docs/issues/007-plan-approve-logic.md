# 007 - Plan 审批逻辑缺陷

- **优先级**: P1
- **类型**: bug/ux
- **状态**: open

## 问题描述

### 7a. approve/reject 端点用 `__import__("datetime")` 获取时间

`plans.py` 中 `approve_plan` 和 `reject_plan` 使用 `__import__("datetime").datetime.utcnow()`，这是不规范的写法，且 Python 3.12 已弃用 `datetime.utcnow()`。

### 7b. 审批逻辑不严谨

- `approved_by` 硬编码为 `"user"`，无法区分不同审批者
- reject 后 `approved_by` 也被设为 `"user"`，语义不对（应该是 `rejected_by`）
- 没有记录拒绝原因
- 前端审批通过后 Plan 状态变为 active，但没有提示用户确认

## 影响文件

- `src/routes/plans.py` — 第 96-101 行、第 113-118 行

## 修复方案

1. 用 `from datetime import datetime, timezone; datetime.now(timezone.utc)` 替代
2. 审批时从 JWT token 获取用户身份
3. reject 接口增加 `reason` 参数
4. 前端审批操作增加确认弹窗
