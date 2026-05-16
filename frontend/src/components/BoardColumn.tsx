import { useDroppable } from "@dnd-kit/core";
import type { ReactNode } from "react";

interface BoardColumnProps {
  id: string;
  title: string;
  color: string;
  count: number;
  children: ReactNode;
}

export default function BoardColumn({ id, title, color, count, children }: BoardColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <div
      ref={setNodeRef}
      style={{
        minWidth: 240,
        maxWidth: 280,
        flex: "1 0 240px",
        background: isOver ? "#f0f5ff" : "#fafafa",
        borderRadius: 8,
        border: isOver ? "2px dashed #1890ff" : "1px solid #f0f0f0",
        display: "flex",
        flexDirection: "column",
        maxHeight: "calc(100vh - 220px)",
        transition: "background 0.2s, border 0.2s",
      }}
    >
      {/* 列头 */}
      <div
        style={{
          padding: "10px 12px",
          borderBottom: "1px solid #f0f0f0",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />
          <span style={{ fontWeight: 600, fontSize: 14 }}>{title}</span>
        </div>
        <span
          style={{
            background: "#f0f0f0",
            borderRadius: 10,
            padding: "0 8px",
            fontSize: 12,
            color: "#666",
          }}
        >
          {count}
        </span>
      </div>

      {/* 卡片列表 */}
      <div style={{ padding: "8px 8px 8px", overflowY: "auto", flex: 1 }}>
        {children}
      </div>
    </div>
  );
}
