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
