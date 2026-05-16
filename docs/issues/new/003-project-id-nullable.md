# project_id 字段 nullable 导致潜在孤立数据

## 优先级: P2
## 状态: open
## 类型: enhancement

## 问题描述

Issue、Milestone、Plan、Server、ActivityLog 的 `project_id` 外键均为 `nullable=True`。多项目系统里可能出现不属于任何项目的孤立记录，这些记录无法通过任何项目被 UI 发现和访问。

## 影响范围

- 通过 API 直接调用（绕过前端）可能创建无 `project_id` 的记录
- 迁移回填后，新创建的数据理论上都应有 `project_id`
- 孤立数据在 UI 中"消失"

## 建议方案

1. **应用层校验**：在 Schema 层（如 `IssueCreate`）将 `project_id` 设为必填字段
2. **数据库层约束**：迁移完成后，将 `project_id` 列改为 `NOT NULL`
3. **渐进式推进**：先做应用层校验（小改动），DB 层约束需谨慎评估迁移风险

## 注意事项

改为 NOT NULL 需要确保所有现有数据都已被回填，且所有创建路径都提供了 `project_id`。建议在 v0.5.0 经过充分验证后再执行。
