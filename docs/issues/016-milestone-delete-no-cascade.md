# 016 — Milestone 删除未检查关联 Issue

> 优先级: P1 | 类型: data-integrity | 状态: open

## 问题描述

删除 Milestone 时未检查是否有 Issue 关联到该 Milestone。直接删除会导致：

1. **外键约束错误**：如果数据库启用了外键约束（SQLite 默认不启用），删除会失败
2. **数据悬空**：如果外键约束未启用，Issue 的 `milestone_id` 会指向不存在的 Milestone
3. **同样的问题存在于 `deferred_to_milestone_id`**：如果被删除的 Milestone 是某个 Issue 的推迟目标，也会悬空

```python
@router.delete("/{milestone_id}", status_code=204)
async def delete_milestone(milestone_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Milestone).where(Milestone.id == milestone_id))
    milestone = result.scalar_one_or_none()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    await db.delete(milestone)  # 直接删除，无检查
    await db.commit()
    return None
```

同样的问题也存在于 Plan 删除（PlanItem 有 cascade），但 Milestone 没有 cascade 设置。

## 涉及文件

- `backend/src/routes/milestones.py` L85-L92

## 修复方案

方案 A：删除前检查并拒绝

```python
issue_count = await db.execute(
    select(func.count(Issue.id)).where(
        (Issue.milestone_id == milestone_id) |
        (Issue.deferred_to_milestone_id == milestone_id)
    )
)
if issue_count.scalar() > 0:
    raise HTTPException(status_code=400, detail="该里程碑下还有关联 Issue，无法删除")
```

方案 B：删除时将关联 Issue 的 milestone_id 置为 NULL

```python
await db.execute(
    update(Issue).where(Issue.milestone_id == milestone_id).values(milestone_id=None)
)
await db.execute(
    update(Issue).where(Issue.deferred_to_milestone_id == milestone_id).values(deferred_to_milestone_id=None)
)
```
