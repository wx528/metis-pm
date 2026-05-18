# 项目知识库 — 日常知识记录 + 主知识库吸收

> 优先级: P2（中期）
> 日期: 2026-05-18

## 核心想法

项目内记录问题和解决方法、零碎规范，方便后续参考。定时被主知识库吸收后清理，避免冗余。

## 第一步：项目知识库（轻量）

### Knowledge 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| project_id | int | 所属项目 |
| title | str | 标题 |
| content | text | 内容 |
| tags | str | 标签（逗号分隔） |
| category | str | 分类（如 solution / convention / note） |
| status | str | draft / published / absorbed |
| source_issue_id | int | 可选，关联来源 Issue |
| created_by | str | 创建者 |
| created_at / updated_at | datetime | 时间戳 |

### MCP 工具

- `create_knowledge`: Agent/人创建知识条目
- `list_knowledge`: 按项目/标签/分类搜索
- `update_knowledge`: 编辑

### 工作流集成

- Issue 关闭时 → 自动提示 "是否提取为知识？"
- Agent 解决问题后 → 工作流触发 → 自动创建知识条目

### 和 Issue 评论的区别

- **结构化**：标题 + 标签 + 分类，可搜索、可引用
- **独立性**：不依附于某个 Issue，可独立存在
- **状态管理**：draft → published → absorbed 生命周期

---

## 第二步：主知识库吸收（可选）

### 全局 Knowledge 模型

- 无 project_id，跨项目通用知识

### 吸收工作流

```
schedule 定时 → 查找 status=draft 的项目知识
  → Agent/人工审批 → 复制到全局
  → 项目知识标记 absorbed
```

### 不急

先有数据再谈吸收流程，等项目知识库积累一定量后自然演进。
