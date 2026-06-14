# Graph View 功能地图设计文档

> 日期：2026-06-14
> 状态：设计中

## 概述

为项目管理系统新增 Graph View 页面，以类似 Obsidian 的力导向图方式展示项目的功能结构。随着项目 Issue 的增长，Graph 自动扩展，帮助用户直观理解功能分布和层级关系。

## 目的

- 提供项目整体功能的可视化地图
- 展示 Issue 之间的父子层级关系
- 通过颜色区分不同功能领域（标签）
- 支持筛选和交互，便于探索

## 设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 用途 | 功能地图 | 展示项目功能结构 |
| 布局 | 力导向图 | 类似 Obsidian，视觉效果好 |
| 节点 | Milestone 容器 + Issue 节点 | 层级清晰 |
| 边 | 父子关系（parent_id） | 已有数据，无需新增字段 |
| 颜色 | 按 label 区分 | 已有数据，自动聚类 |
| 交互 | 悬浮预览 + 点击跳转 | 兼顾信息和导航 |

## 架构设计

### 路由

- 前端：`/projects/:projectSlug/graph`
- 后端：`GET /api/v1/projects/{slug}/graph`

### 技术选型

- 前端渲染库：`react-force-graph-2d`
- 理由：React 集成简单，开箱即用，支持交互

## API 设计

### 请求

```
GET /api/v1/projects/{slug}/graph
  ?status=open,in_progress
  &issue_type=feature,task
  &labels=auth,backend
```

### 响应

```json
{
  "nodes": [
    {
      "id": 1,
      "type": "milestone",
      "title": "Phase 1",
      "color": "#4a9eff",
      "issue_count": 15
    },
    {
      "id": 12,
      "type": "issue",
      "title": "认证模块重构",
      "priority": "P1",
      "status": "in_progress",
      "issue_type": "feature",
      "labels": ["auth", "backend"],
      "milestone_id": 1,
      "parent_id": null,
      "size": 16,
      "color": "#ff6b6b",
      "opacity": 0.85
    }
  ],
  "edges": [
    { "source": 12, "target": 13 },
    { "source": 12, "target": 14 }
  ],
  "labels": {
    "auth": "#ff6b6b",
    "backend": "#51cf66",
    "frontend": "#4a9eff"
  }
}
```

### 节点大小映射

| 优先级 | 半径 |
|--------|------|
| P0 | 20 |
| P1 | 16 |
| P2 | 12 |
| P3 | 8 |

### 状态样式

| 状态 | 样式 |
|------|------|
| open / in_progress / review | 正常显示 |
| closed / cancelled | 灰色 `#888` + opacity 0.4 |
| deferred | 虚线边框 |

### 颜色分配

- 预设色板：`['#ff6b6b', '#51cf66', '#4a9eff', '#ffd43b', '#cc5de8', '#20c997', '#ff922b', '#845ef7']`
- 按 label 字母排序后循环分配
- 无 label 的 Issue 使用默认灰色 `#888`

## 前端设计

### 文件结构

```
frontend/src/
├── pages/
│   └── Graph.tsx              # 主页面
├── components/
│   └── GraphView/
│       ├── index.tsx           # Graph 容器 + 工具栏
│       ├── ForceGraph.tsx      # react-force-graph 封装
│       ├── NodePreview.tsx     # 悬浮预览卡片
│       └── Legend.tsx          # 图例组件
```

### 页面布局

```
┌─────────────────────────────────────────────────────────┐
│ Graph View          [筛选: 状态 ▼ 类型 ▼ 标签 ▼] [图例] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│                    力导向图区域                          │
│                                                         │
│   ┌─────────────┐              ┌────────────┐          │
│   │  Phase 1    │              │  Phase 2   │          │
│   │  (虚线圆)   │              │  (虚线圆)  │          │
│   │             │              │            │          │
│   │  [Issue]    │              │   [Issue]  │          │
│   │    |        │              │     |      │          │
│   │  [Sub] [Sub]│              │   [Sub]    │          │
│   │             │              │            │          │
│   └─────────────┘              └────────────┘          │
│                                                         │
│              + 悬浮预览卡片                             │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ 节点: 15   连线: 12                    缩放: 100%  ⊕ ⊖ │
└─────────────────────────────────────────────────────────┘
```

### 交互行为

| 操作 | 行为 |
|------|------|
| 鼠标悬停 Issue 节点 | 显示 `NodePreview` 卡片 |
| 点击 Issue 节点 | 跳转到 `/projects/:slug/issues/:id` |
| 鼠标悬停 Milestone 区域 | 高亮该阶段所有节点 |
| 拖拽空白区域 | 平移画布 |
| 滚轮 | 缩放 |
| 拖拽 Issue 节点 | 调整位置（不持久化） |

### 悬浮预览卡片

```
┌────────────────────────┐
│ [P1] #12               │
│ 认证模块重构            │
│                        │
│ [auth] [backend]       │
│ 状态: in_progress      │
└────────────────────────┘
```

### 筛选工具栏

- **状态筛选**：多选下拉，选项 `open / in_progress / review / closed / deferred / cancelled`
- **类型筛选**：多选下拉，选项 `bug / feature / task / improvement / documentation / idea`
- **标签筛选**：多选下拉，动态加载项目内所有标签

筛选后 Graph 实时更新（防抖 300ms）。

### 图例组件

显示所有 label 及其对应颜色，点击可快速筛选该标签。

## 后端设计

### 新增文件

- `backend/src/routes/graph.py` — Graph API 路由
- `backend/src/schemas/graph.py` — 请求/响应 Schema

### 路由注册

```python
# backend/src/routes/__init__.py
api_router.include_router(graph.router, prefix="/projects/{slug}/graph", tags=["Graph View"])
```

### API 逻辑

```python
async def get_project_graph(
    slug: str,
    status: Optional[str] = None,
    issue_type: Optional[str] = None,
    labels: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    # 1. 查询项目
    # 2. 查询项目所有 milestones
    # 3. 查询项目所有 issues（含筛选条件）
    # 4. 收集所有 labels，分配颜色
    # 5. 构建节点列表
    #    - Milestone 节点：type="milestone"
    #    - Issue 节点：计算 size/color/opacity
    # 6. 构建边列表（parent_id 不为空的 issue）
    # 7. 返回 { nodes, edges, labels }
```

### Schema 定义

```python
# backend/src/schemas/graph.py

class GraphNode(BaseModel):
    id: int
    type: str  # "milestone" | "issue"
    title: str
    # Issue 专属字段
    priority: Optional[str] = None
    status: Optional[str] = None
    issue_type: Optional[str] = None
    labels: Optional[List[str]] = None
    milestone_id: Optional[int] = None
    parent_id: Optional[int] = None
    # 视觉属性
    size: int
    color: str
    opacity: float = 1.0

class GraphEdge(BaseModel):
    source: int
    target: int

class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    labels: Dict[str, str]  # label -> color
```

## 导航集成

### 侧边栏菜单

在 `Layout.tsx` 的项目菜单中添加：

```tsx
{ key: 'graph', icon: <ApartmentOutlined />, label: 'Graph' }
```

### 路由配置

在 `App.tsx` 中添加：

```tsx
<Route path="projects/:projectSlug/graph" element={<Graph />} />
```

## 依赖

### 前端新增

```json
{
  "dependencies": {
    "react-force-graph-2d": "^1.25.0"
  }
}
```

## 验收标准

- [ ] 访问 `/projects/:slug/graph` 显示力导向图
- [ ] 节点按 label 着色，按优先级设置大小
- [ ] closed/cancelled 节点显示为灰色
- [ ] 悬浮节点显示预览卡片
- [ ] 点击节点跳转到 Issue 详情
- [ ] 筛选功能正常工作
- [ ] 图例正确显示所有标签
- [ ] 支持缩放和平移
- [ ] Milestone 显示为虚线容器区域

## 未来扩展

- 支持 Issue 之间的依赖关系边（需新增 `depends_on` 字段）
- 节点位置持久化（localStorage）
- 导出 Graph 为图片
- 支持按时间轴动画展示 Issue 创建过程
