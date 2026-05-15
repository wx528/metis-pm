# 017 — 前端 Milestones 页面 N+1 查询

> 优先级: P2 | 类型: performance | 状态: **fixed**

## 问题描述

Milestones 页面在获取列表后，对每个 Milestone 单独调用详情接口获取统计数据：

```typescript
const fetch = async () => {
    const listRes = await milestonesApi.list();
    const withStats = await Promise.all(
        listRes.data.map(async (m) => {
            const detailRes = await milestonesApi.get(m.id);  // N 次请求
            return detailRes.data;
        })
    );
    setMilestones(withStats);
};
```

如果有 20 个 Milestone，就会发出 1 + 20 = 21 次 HTTP 请求。每次详情请求还会执行 SQL 聚合查询，造成不必要的数据库负载。

## 涉及文件

- `frontend/src/pages/Milestones.tsx` L18-L25

## 修复方案

方案 A：后端列表接口直接返回统计数据

在 `GET /milestones` 接口中添加可选参数 `with_stats=true`，返回 `MilestoneReadWithStats` 列表：

```python
@router.get("", response_model=List[MilestoneReadWithStats])
async def list_milestones(
    db: AsyncSession = Depends(get_db),
    with_stats: bool = Query(False),
    ...
):
```

方案 B：前端只显示基本信息，点击详情时再获取统计

当前页面只需要显示 open/closed/deferred 计数，可以在列表接口中用子查询一次性获取。
