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
