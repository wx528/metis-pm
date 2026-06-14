# Graph View 功能地图实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为项目管理系统新增 Graph View 页面，以力导向图方式展示项目功能结构。

**Architecture:** 后端新增 Graph API 返回节点和边数据，前端使用 react-force-graph-2d 渲染力导向图。

**Tech Stack:** Python/FastAPI, React 19, TypeScript, react-force-graph-2d, Ant Design 6

---

## 文件结构

### 后端新增/修改
- `backend/src/schemas/graph.py` — Graph 数据 Schema
- `backend/src/routes/graph.py` — Graph API 路由
- `backend/src/routes/__init__.py` — 注册路由（修改）

### 前端新增/修改
- `frontend/src/api/graph.ts` — Graph API 客户端
- `frontend/src/api/index.ts` — 导出（修改）
- `frontend/src/components/GraphView/index.tsx` — Graph 容器
- `frontend/src/components/GraphView/ForceGraph.tsx` — 力导向图组件
- `frontend/src/components/GraphView/NodePreview.tsx` — 节点预览卡片
- `frontend/src/components/GraphView/Legend.tsx` — 图例组件
- `frontend/src/pages/Graph.tsx` — Graph 页面
- `frontend/src/App.tsx` — 路由注册（修改）
- `frontend/src/components/Layout.tsx` — 侧边栏菜单（修改）

---

## Task 1: 后端 — Graph Schema

**Files:**
- Create: `backend/src/schemas/graph.py`

- [ ] **Step 1: 创建 Graph Schema 文件**

```python
# backend/src/schemas/graph.py
from typing import List, Optional, Dict
from pydantic import BaseModel


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
    size: int = 12
    color: str = "#888888"
    opacity: float = 1.0


class GraphEdge(BaseModel):
    source: int
    target: int


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    labels: Dict[str, str]  # label -> color
```

- [ ] **Step 2: 验证文件语法**

Run: `python -c "from backend.src.schemas.graph import GraphResponse; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/src/schemas/graph.py
git commit -m "feat: add graph schema definitions"
```

---

## Task 2: 后端 — Graph API 路由

**Files:**
- Create: `backend/src/routes/graph.py`
- Modify: `backend/src/routes/__init__.py`

- [ ] **Step 1: 创建 Graph 路由文件**

```python
# backend/src/routes/graph.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.dependencies import get_db
from src.models.project import Project
from src.models.milestone import Milestone
from src.models.issue import Issue
from src.schemas.graph import GraphNode, GraphEdge, GraphResponse

router = APIRouter(dependencies=[Depends(get_db)])

# 预设色板
COLOR_PALETTE = [
    "#ff6b6b", "#51cf66", "#4a9eff", "#ffd43b",
    "#cc5de8", "#20c997", "#ff922b", "#845ef7"
]

# 优先级 -> 节点大小
PRIORITY_SIZE = {
    "P0": 20,
    "P1": 16,
    "P2": 12,
    "P3": 8,
}

# 状态 -> 透明度
STATUS_OPACITY = {
    "open": 0.9,
    "in_progress": 0.9,
    "review": 0.85,
    "deferred": 0.7,
    "closed": 0.4,
    "cancelled": 0.4,
}


def assign_label_colors(labels: list[str]) -> dict[str, str]:
    """为标签分配颜色"""
    sorted_labels = sorted(set(labels))
    return {
        label: COLOR_PALETTE[i % len(COLOR_PALETTE)]
        for i, label in enumerate(sorted_labels)
    }


@router.get("", response_model=GraphResponse)
async def get_project_graph(
    slug: str,
    status: Optional[str] = Query(None, description="逗号分隔的状态筛选"),
    issue_type: Optional[str] = Query(None, description="逗号分隔的类型筛选"),
    labels: Optional[str] = Query(None, description="逗号分隔的标签筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取项目 Graph 数据"""
    # 1. 查询项目
    stmt = select(Project).where(Project.slug == slug)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. 查询 milestones
    stmt = select(Milestone).where(Milestone.project_id == project.id)
    result = await db.execute(stmt)
    milestones = result.scalars().all()

    # 3. 构建筛选条件
    stmt = select(Issue).where(Issue.project_id == project.id)

    if status:
        status_list = [s.strip() for s in status.split(",")]
        stmt = stmt.where(Issue.status.in_(status_list))

    if issue_type:
        type_list = [t.strip() for t in issue_type.split(",")]
        stmt = stmt.where(Issue.issue_type.in_(type_list))

    if labels:
        label_list = [l.strip() for l in labels.split(",")]
        # labels 字段是逗号分隔的字符串，使用 like 匹配
        for label in label_list:
            stmt = stmt.where(Issue.labels.contains(label))

    result = await db.execute(stmt)
    issues = result.scalars().all()

    # 4. 收集所有 labels 并分配颜色
    all_labels = []
    for issue in issues:
        if issue.labels:
            all_labels.extend([l.strip() for l in issue.labels.split(",") if l.strip()])
    label_colors = assign_label_colors(all_labels)

    # 5. 构建节点
    nodes: list[GraphNode] = []

    # Milestone 节点
    for ms in milestones:
        nodes.append(GraphNode(
            id=ms.id,
            type="milestone",
            title=ms.title or f"Milestone {ms.id}",
            size=30,
            color="#4a9eff",
            opacity=0.3,
        ))

    # Issue 节点
    for issue in issues:
        issue_labels = []
        if issue.labels:
            issue_labels = [l.strip() for l in issue.labels.split(",") if l.strip()]

        # 确定颜色（取第一个标签的颜色）
        color = label_colors.get(issue_labels[0], "#888888") if issue_labels else "#888888"

        # 确定大小
        size = PRIORITY_SIZE.get(issue.priority, 12)

        # 确定透明度
        opacity = STATUS_OPACITY.get(issue.status, 0.9)

        nodes.append(GraphNode(
            id=issue.id,
            type="issue",
            title=issue.title,
            priority=issue.priority,
            status=issue.status,
            issue_type=issue.issue_type,
            labels=issue_labels,
            milestone_id=issue.milestone_id,
            parent_id=issue.parent_id,
            size=size,
            color=color,
            opacity=opacity,
        ))

    # 6. 构建边（父子关系）
    edges: list[GraphEdge] = []
    issue_ids = {issue.id for issue in issues}
    for issue in issues:
        if issue.parent_id and issue.parent_id in issue_ids:
            edges.append(GraphEdge(source=issue.id, target=issue.parent_id))

    return GraphResponse(nodes=nodes, edges=edges, labels=label_colors)
```

- [ ] **Step 2: 注册路由**

修改 `backend/src/routes/__init__.py`，在导入和注册部分添加：

```python
# 在导入部分添加
from src.routes import graph

# 在注册部分添加（在 projects 之后）
api_router.include_router(graph.router, prefix="/projects/{slug}/graph", tags=["Graph View"])
```

完整的修改后文件：

```python
from fastapi import APIRouter

from src.routes import issues, milestones, plans, servers, activity_logs, auth, dashboard, projects, notifications, stats, workflows, agent_memory, project_registrations, agent_status, monitoring, comments, feedback, git_webhook, graph

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(projects.router, prefix="/projects", tags=["项目管理"])
api_router.include_router(graph.router, prefix="/projects/{slug}/graph", tags=["Graph View"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["仪表盘"])
api_router.include_router(issues.router, prefix="/issues", tags=["问题管理"])
api_router.include_router(milestones.router, prefix="/milestones", tags=["里程碑/分期"])
api_router.include_router(plans.router, prefix="/plans", tags=["计划管理"])
api_router.include_router(servers.router, prefix="/servers", tags=["服务器管理"])
api_router.include_router(activity_logs.router, prefix="/activity-logs", tags=["活动日志"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["通知"])
api_router.include_router(stats.router, prefix="/stats", tags=["统计分析"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["工作流"])
api_router.include_router(agent_memory.router, prefix="/agent-memories", tags=["Agent记忆"])
api_router.include_router(project_registrations.router, prefix="/project-registrations", tags=["项目登记"])
api_router.include_router(agent_status.router, prefix="/dashboard", tags=["Agent状态"])
api_router.include_router(monitoring.public_router, prefix="/monitoring", tags=["系统监控"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["系统监控"])
api_router.include_router(comments.router, prefix="/issue-comments", tags=["评论管理"])
api_router.include_router(feedback.router, prefix="/feedbacks", tags=["意见箱"])
api_router.include_router(git_webhook.router, prefix="", tags=["Git Webhook"])
```

- [ ] **Step 3: 启动后端验证 API**

Run: `cd backend && python main.py`
然后在浏览器访问 `http://localhost:8000/docs`，应该能看到新的 Graph View 端点。

或使用 curl 测试：
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/projects/default/graph
```

Expected: 返回 JSON 包含 nodes, edges, labels

- [ ] **Step 4: Commit**

```bash
git add backend/src/routes/graph.py backend/src/routes/__init__.py
git commit -m "feat: add graph API endpoint"
```

---

## Task 3: 前端 — 安装依赖 + API 客户端

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/api/graph.ts`
- Modify: `frontend/src/api/index.ts`

- [ ] **Step 1: 安装 react-force-graph-2d**

Run: `cd frontend && npm install react-force-graph-2d`

- [ ] **Step 2: 创建 Graph API 客户端**

```typescript
// frontend/src/api/graph.ts
import { api } from "./client";

export interface GraphNode {
  id: number;
  type: "milestone" | "issue";
  title: string;
  priority?: string;
  status?: string;
  issue_type?: string;
  labels?: string[];
  milestone_id?: number;
  parent_id?: number;
  size: number;
  color: string;
  opacity: number;
}

export interface GraphEdge {
  source: number;
  target: number;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  labels: Record<string, string>;
}

export interface GraphParams {
  status?: string;
  issue_type?: string;
  labels?: string;
}

export const graphApi = {
  get: (slug: string, params?: GraphParams) =>
    api.get<GraphResponse>(`/projects/${slug}/graph`, { params }),
};
```

- [ ] **Step 3: 导出 API**

修改 `frontend/src/api/index.ts`，添加：

```typescript
export * from "./graph";
```

- [ ] **Step 4: 验证 TypeScript 编译**

Run: `cd frontend && npm run build`
Expected: 编译成功

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/api/graph.ts frontend/src/api/index.ts
git commit -m "feat: add graph API client and install react-force-graph-2d"
```

---

## Task 4: 前端 — NodePreview 组件

**Files:**
- Create: `frontend/src/components/GraphView/NodePreview.tsx`

- [ ] **Step 1: 创建 NodePreview 组件**

```tsx
// frontend/src/components/GraphView/NodePreview.tsx
import { Tag } from "antd";
import type { GraphNode } from "../../api/graph";

interface NodePreviewProps {
  node: GraphNode;
  x: number;
  y: number;
}

const priorityColors: Record<string, string> = {
  P0: "red",
  P1: "orange",
  P2: "blue",
  P3: "default",
};

const statusLabels: Record<string, string> = {
  open: "待处理",
  in_progress: "进行中",
  review: "审核中",
  deferred: "已暂缓",
  closed: "已完成",
  cancelled: "已取消",
};

export default function NodePreview({ node, x, y }: NodePreviewProps) {
  if (node.type === "milestone") return null;

  return (
    <div
      style={{
        position: "fixed",
        left: x + 15,
        top: y - 10,
        background: "var(--ant-color-bg-container)",
        border: "1px solid var(--ant-color-border)",
        borderRadius: 8,
        padding: 12,
        width: 200,
        boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
        zIndex: 1000,
        pointerEvents: "none",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        {node.priority && (
          <Tag color={priorityColors[node.priority]} style={{ margin: 0 }}>
            {node.priority}
          </Tag>
        )}
        <span style={{ color: "var(--ant-color-text-secondary)", fontSize: 12 }}>
          #{node.id}
        </span>
      </div>
      <div style={{ fontWeight: 500, marginBottom: 8, lineHeight: 1.4 }}>
        {node.title}
      </div>
      {node.labels && node.labels.length > 0 && (
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 8 }}>
          {node.labels.map((label) => (
            <span
              key={label}
              style={{
                background: "var(--ant-color-fill-secondary)",
                padding: "2px 6px",
                borderRadius: 3,
                fontSize: 10,
                color: "var(--ant-color-text-secondary)",
              }}
            >
              {label}
            </span>
          ))}
        </div>
      )}
      {node.status && (
        <div style={{ fontSize: 11, color: "var(--ant-color-text-secondary)" }}>
          状态: {statusLabels[node.status] || node.status}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/GraphView/NodePreview.tsx
git commit -m "feat: add NodePreview component for graph hover"
```

---

## Task 5: 前端 — Legend 组件

**Files:**
- Create: `frontend/src/components/GraphView/Legend.tsx`

- [ ] **Step 1: 创建 Legend 组件**

```tsx
// frontend/src/components/GraphView/Legend.tsx
import { Tag } from "antd";

interface LegendProps {
  labels: Record<string, string>;
  onLabelClick?: (label: string) => void;
}

export default function Legend({ labels, onLabelClick }: LegendProps) {
  const entries = Object.entries(labels).sort(([a], [b]) => a.localeCompare(b));

  if (entries.length === 0) {
    return null;
  }

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 8,
        alignItems: "center",
      }}
    >
      <span style={{ fontSize: 12, color: "var(--ant-color-text-secondary)" }}>
        标签:
      </span>
      {entries.map(([label, color]) => (
        <Tag
          key={label}
          color={color}
          style={{ cursor: onLabelClick ? "pointer" : "default", margin: 0 }}
          onClick={() => onLabelClick?.(label)}
        >
          {label}
        </Tag>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/GraphView/Legend.tsx
git commit -m "feat: add Legend component for graph"
```

---

## Task 6: 前端 — ForceGraph 组件

**Files:**
- Create: `frontend/src/components/GraphView/ForceGraph.tsx`

- [ ] **Step 1: 创建 ForceGraph 组件**

```tsx
// frontend/src/components/GraphView/ForceGraph.tsx
import { useCallback, useMemo, useRef, useState } from "react";
import ForceGraph2D, { type ForceGraphMethods } from "react-force-graph-2d";
import type { GraphNode, GraphEdge } from "../../api/graph";
import NodePreview from "./NodePreview";

interface ForceGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (node: GraphNode) => void;
  width: number;
  height: number;
}

interface GraphNodeType {
  id: number;
  type: string;
  title: string;
  size: number;
  color: string;
  opacity: number;
  x?: number;
  y?: number;
  __data?: GraphNode;
}

interface GraphLinkType {
  source: number | GraphNodeType;
  target: number | GraphNodeType;
}

export default function ForceGraph({ nodes, edges, onNodeClick, width, height }: ForceGraphProps) {
  const fgRef = useRef<ForceGraphMethods>();
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // 转换节点数据
  const graphNodes = useMemo(() =>
    nodes.map((node) => ({
      id: node.id,
      type: node.type,
      title: node.title,
      size: node.size,
      color: node.color,
      opacity: node.opacity,
      __data: node,
    })),
    [nodes]
  );

  // 转换边数据
  const graphLinks = useMemo(() =>
    edges.map((edge) => ({
      source: edge.source,
      target: edge.target,
    })),
    [edges]
  );

  const handleNodeClick = useCallback((node: GraphNodeType) => {
    if (node.__data && onNodeClick) {
      onNodeClick(node.__data);
    }
  }, [onNodeClick]);

  const handleNodeHover = useCallback((node: GraphNodeType | null) => {
    setHoveredNode(node?.__data || null);
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    setMousePos({ x: e.clientX, y: e.clientY });
  }, []);

  // 自定义节点绘制
  const nodeCanvasObject = useCallback((node: GraphNodeType, ctx: CanvasRenderingContext2D) => {
    const size = node.size;
    const x = node.x || 0;
    const y = node.y || 0;

    ctx.globalAlpha = node.opacity;

    if (node.type === "milestone") {
      // Milestone: 虚线圆
      ctx.beginPath();
      ctx.arc(x, y, size, 0, 2 * Math.PI);
      ctx.strokeStyle = node.color;
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 3]);
      ctx.stroke();
      ctx.setLineDash([]);
    } else {
      // Issue: 实心圆
      ctx.beginPath();
      ctx.arc(x, y, size / 2, 0, 2 * Math.PI);
      ctx.fillStyle = node.color;
      ctx.fill();

      // 如果是 closed/cancelled，绘制虚线边框
      if (node.opacity < 0.5) {
        ctx.strokeStyle = "#888";
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 2]);
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }

    ctx.globalAlpha = 1;
  }, []);

  return (
    <>
      <ForceGraph2D
        ref={fgRef}
        width={width}
        height={height}
        graphData={{ nodes: graphNodes, links: graphLinks }}
        nodeCanvasObject={nodeCanvasObject as any}
        nodePointerAreaPaint={(node: GraphNodeType, color: string, ctx: CanvasRenderingContext2D) => {
          ctx.beginPath();
          ctx.arc(node.x || 0, node.y || 0, node.size / 2, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        onBackgroundClick={() => {}}
        linkColor={() => "rgba(100, 100, 100, 0.3)"}
        linkWidth={1}
        linkDirectionalArrowLength={0}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        cooldownTicks={100}
      />
      {hoveredNode && (
        <NodePreview node={hoveredNode} x={mousePos.x} y={mousePos.y} />
      )}
    </>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/GraphView/ForceGraph.tsx
git commit -m "feat: add ForceGraph component using react-force-graph-2d"
```

---

## Task 7: 前端 — GraphView 容器组件

**Files:**
- Create: `frontend/src/components/GraphView/index.tsx`

- [ ] **Step 1: 创建 GraphView 容器组件**

```tsx
// frontend/src/components/GraphView/index.tsx
import { useState, useEffect, useRef, useCallback } from "react";
import { Select, Space, Button } from "antd";
import { ZoomInOutlined, ZoomOutOutlined, ExpandOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { graphApi, type GraphResponse, type GraphNode, type GraphParams } from "../../api/graph";
import ForceGraph from "./ForceGraph";
import Legend from "./Legend";
import { useProject } from "../../hooks/useProject";

const { Option } = Select;

const STATUS_OPTIONS = [
  { value: "open", label: "待处理" },
  { value: "in_progress", label: "进行中" },
  { value: "review", label: "审核中" },
  { value: "deferred", label: "已暂缓" },
  { value: "closed", label: "已完成" },
  { value: "cancelled", label: "已取消" },
];

const TYPE_OPTIONS = [
  { value: "bug", label: "Bug" },
  { value: "feature", label: "功能" },
  { value: "task", label: "任务" },
  { value: "improvement", label: "改进" },
  { value: "documentation", label: "文档" },
  { value: "idea", label: "想法" },
];

export default function GraphView() {
  const navigate = useNavigate();
  const { currentProject } = useProject();
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });
  const [data, setData] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<GraphParams>({});
  const [nodeCount, setNodeCount] = useState(0);
  const [edgeCount, setEdgeCount] = useState(0);

  // 监听容器大小
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setSize({ width: rect.width, height: rect.height });
      }
    };
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  // 加载数据
  const loadData = useCallback(async () => {
    if (!currentProject) return;
    setLoading(true);
    try {
      const res = await graphApi.get(currentProject.slug, filters);
      setData(res.data);
      setNodeCount(res.data.nodes.length);
      setEdgeCount(res.data.edges.length);
    } catch (err) {
      console.error("Failed to load graph data:", err);
    } finally {
      setLoading(false);
    }
  }, [currentProject, filters]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 节点点击
  const handleNodeClick = useCallback((node: GraphNode) => {
    if (node.type === "issue" && currentProject) {
      navigate(`/projects/${currentProject.slug}/issues/${node.id}`);
    }
  }, [navigate, currentProject]);

  // 标签点击筛选
  const handleLabelClick = useCallback((label: string) => {
    setFilters((prev) => {
      const current = prev.labels ? prev.labels.split(",") : [];
      if (current.includes(label)) {
        const filtered = current.filter((l) => l !== label);
        return { ...prev, labels: filtered.length > 0 ? filtered.join(",") : undefined };
      }
      return { ...prev, labels: [...current, label].join(",") };
    });
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* 工具栏 */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid var(--ant-color-border)",
          display: "flex",
          alignItems: "center",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <span style={{ fontWeight: 600 }}>Graph View</span>
        <div style={{ flex: 1 }} />
        <Space>
          <Select
            mode="multiple"
            placeholder="状态筛选"
            style={{ minWidth: 120 }}
            value={filters.status?.split(",") || []}
            onChange={(values) =>
              setFilters((prev) => ({ ...prev, status: values.length > 0 ? values.join(",") : undefined }))
            }
            allowClear
            maxTagCount={1}
          >
            {STATUS_OPTIONS.map((opt) => (
              <Option key={opt.value} value={opt.value}>{opt.label}</Option>
            ))}
          </Select>
          <Select
            mode="multiple"
            placeholder="类型筛选"
            style={{ minWidth: 120 }}
            value={filters.issue_type?.split(",") || []}
            onChange={(values) =>
              setFilters((prev) => ({ ...prev, issue_type: values.length > 0 ? values.join(",") : undefined }))
            }
            allowClear
            maxTagCount={1}
          >
            {TYPE_OPTIONS.map((opt) => (
              <Option key={opt.value} value={opt.value}>{opt.label}</Option>
            ))}
          </Select>
        </Space>
        {data && <Legend labels={data.labels} onLabelClick={handleLabelClick} />}
      </div>

      {/* 图区域 */}
      <div ref={containerRef} style={{ flex: 1, position: "relative", overflow: "hidden" }}>
        {loading && (
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              color: "var(--ant-color-text-secondary)",
            }}
          >
            加载中...
          </div>
        )}
        {data && !loading && (
          <ForceGraph
            nodes={data.nodes}
            edges={data.edges}
            onNodeClick={handleNodeClick}
            width={size.width}
            height={size.height}
          />
        )}
      </div>

      {/* 状态栏 */}
      <div
        style={{
          padding: "8px 16px",
          borderTop: "1px solid var(--ant-color-border)",
          display: "flex",
          alignItems: "center",
          gap: 16,
          fontSize: 12,
          color: "var(--ant-color-text-secondary)",
        }}
      >
        <span>节点: {nodeCount}</span>
        <span>连线: {edgeCount}</span>
        {filters.status && <span>状态: {filters.status}</span>}
        {filters.issue_type && <span>类型: {filters.issue_type}</span>}
        {filters.labels && <span>标签: {filters.labels}</span>}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/GraphView/index.tsx
git commit -m "feat: add GraphView container component with filters"
```

---

## Task 8: 前端 — Graph 页面 + 路由

**Files:**
- Create: `frontend/src/pages/Graph.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: 创建 Graph 页面**

```tsx
// frontend/src/pages/Graph.tsx
import GraphView from "../components/GraphView";

export default function Graph() {
  return (
    <div style={{ height: "calc(100vh - 64px)" }}>
      <GraphView />
    </div>
  );
}
```

- [ ] **Step 2: 注册路由**

修改 `frontend/src/App.tsx`，在 import 部分添加：

```tsx
import Graph from "./pages/Graph";
```

在 Routes 中添加（在 board 路由之后）：

```tsx
<Route path="projects/:projectSlug/graph" element={<Graph />} />
```

- [ ] **Step 3: 添加侧边栏菜单**

修改 `frontend/src/components/Layout.tsx`：

1. 在 import 部分添加图标：

```tsx
import {
  // ... existing imports
  ApartmentOutlined,  // 添加这个
} from "@ant-design/icons";
```

2. 在 menuItems 数组中添加（在 board 之后）：

```tsx
const menuItems = [
  { key: `${basePath}/dashboard` || "/", icon: <DashboardOutlined />, label: "仪表盘" },
  { key: `${basePath}/board`, icon: <AppstoreOutlined />, label: "看板" },
  { key: `${basePath}/graph`, icon: <ApartmentOutlined />, label: "Graph" },
  { key: `${basePath}/issues`, icon: <BugOutlined />, label: "Issues" },
  // ... rest
];
```

- [ ] **Step 4: 验证前端编译**

Run: `cd frontend && npm run build`
Expected: 编译成功

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Graph.tsx frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "feat: add Graph page with routing and menu"
```

---

## Task 9: 集成测试 + 最终修复

- [ ] **Step 1: 启动后端和前端**

```bash
# Terminal 1
cd backend && python main.py

# Terminal 2
cd frontend && npm run dev
```

- [ ] **Step 2: 手动测试**

1. 打开 `http://localhost:5173`
2. 选择一个项目
3. 点击侧边栏 "Graph"
4. 验证：
   - 力导向图正常渲染
   - 节点按 label 着色
   - 节点按优先级设置大小
   - 悬浮显示预览卡片
   - 点击跳转到 Issue 详情
   - 筛选功能正常

- [ ] **Step 3: 修复问题（如有）**

根据手动测试结果修复发现的问题。

- [ ] **Step 4: 最终提交**

```bash
git add -A
git commit -m "feat: graph view feature complete"
```

---

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
