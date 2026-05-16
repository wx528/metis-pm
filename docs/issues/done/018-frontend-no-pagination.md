# 018 — 前端 Issues 列表无分页

> 优先级: P2 | 类型: ux | 状态: **fixed**

## 问题描述

前端 Issues 列表页面硬编码 `limit: 100` 获取所有 Issue：

```typescript
const res = await issuesApi.list({ ...filters, limit: 100 });
setIssues(res.data.items);
```

同时 Table 组件使用的是前端分页：

```tsx
<Table
    rowKey="id"
    columns={columns}
    dataSource={issues}
    loading={loading}
    pagination={{ pageSize: 20 }}  // 前端分页，每次只显示 20 条
/>
```

问题：
1. **数据量大时性能差**：如果有 1000+ 个 Issue，每次都加载全部数据
2. **筛选器变更时重新加载全部数据**：每次筛选变化都请求 100 条
3. **后端支持分页但前端未使用**：后端已有 `skip` 和 `limit` 参数

## 涉及文件

- `frontend/src/pages/Issues.tsx` L38-L42, L161-L165

## 修复方案

改为服务端分页：

```typescript
const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });

const fetchIssues = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
        const res = await issuesApi.list({
            ...filters,
            skip: (page - 1) * pageSize,
            limit: pageSize,
        });
        setIssues(res.data.items);
        setPagination(prev => ({ ...prev, current: page, pageSize, total: res.data.total }));
    } finally {
        setLoading(false);
    }
};

// Table
<Table
    rowKey="id"
    columns={columns}
    dataSource={issues}
    loading={loading}
    pagination={{
        current: pagination.current,
        pageSize: pagination.pageSize,
        total: pagination.total,
        onChange: (page, pageSize) => fetchIssues(page, pageSize),
    }}
/>
```
