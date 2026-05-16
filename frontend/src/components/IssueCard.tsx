import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Card, Tag } from "antd";
import { RobotOutlined, UserOutlined, TeamOutlined } from "@ant-design/icons";

interface IssueItem {
  id: number;
  title: string;
  priority: string;
  status: string;
  source: string;
  assignee: string | null;
  issue_type: string;
}

interface IssueCardProps {
  issue: IssueItem;
  priorityColors: Record<string, string>;
  isDragOverlay?: boolean;
}

const SOURCE_ICONS: Record<string, React.ReactNode> = {
  ai_agent: <RobotOutlined style={{ color: "#722ed1" }} />,
  user: <UserOutlined style={{ color: "#1890ff" }} />,
  collaborative: <TeamOutlined style={{ color: "#13c2c2" }} />,
};

const TYPE_COLORS: Record<string, string> = {
  bug: "red",
  feature: "green",
  task: "blue",
  improvement: "purple",
  documentation: "default",
};

export default function IssueCard({ issue, priorityColors, isDragOverlay }: IssueCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: issue.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <Card
        size="small"
        hoverable
        style={{
          marginBottom: 6,
          borderRadius: 6,
          border: "1px solid #f0f0f0",
          cursor: isDragOverlay ? "grabbing" : "grab",
          boxShadow: isDragOverlay ? "0 4px 12px rgba(0,0,0,0.15)" : undefined,
        }}
        bodyStyle={{ padding: "8px 10px" }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
          <span style={{ fontSize: 11, color: "#999" }}>#{issue.id}</span>
          {SOURCE_ICONS[issue.source] || null}
        </div>
        <div
          style={{
            fontSize: 13,
            fontWeight: 500,
            lineHeight: 1.4,
            marginBottom: 6,
            overflow: "hidden",
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
          }}
        >
          {issue.title}
        </div>
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          <Tag color={priorityColors[issue.priority]} style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px", margin: 0 }}>
            {issue.priority}
          </Tag>
          <Tag color={TYPE_COLORS[issue.issue_type]} style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px", margin: 0 }}>
            {issue.issue_type}
          </Tag>
          {issue.assignee && (
            <Tag style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px", margin: 0 }}>
              {issue.assignee}
            </Tag>
          )}
        </div>
      </Card>
    </div>
  );
}
