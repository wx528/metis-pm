import { useState, useEffect, useRef, useCallback } from "react";
import { Select, Space, Empty } from "antd";
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

  const handleNodeClick = useCallback((node: GraphNode) => {
    if (node.type === "issue" && node.issue_id && currentProject) {
      navigate(`/projects/${currentProject.slug}/issues/${node.issue_id}`);
    }
  }, [navigate, currentProject]);

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
        {data && !loading && data.nodes.length > 0 && (
          <ForceGraph
            nodes={data.nodes}
            edges={data.edges}
            onNodeClick={handleNodeClick}
            width={size.width}
            height={size.height}
          />
        )}
        {data && !loading && data.nodes.length === 0 && (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
            <Empty description="暂无数据，请先创建 Issue 或 Milestone" />
          </div>
        )}
      </div>

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
