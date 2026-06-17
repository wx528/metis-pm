import { Card, Tag } from "antd";
import type { Issue } from "../api/issues";

interface IssueCardProps {
  issue: Issue;
  priorityColors: Record<string, string>;
}

const TYPE_COLORS: Record<string, string> = {
  bug: "red",
  feature: "green",
  task: "blue",
};

export default function IssueCard({ issue, priorityColors }: IssueCardProps) {
  return (
    <Card
      size="small"
      hoverable
      style={{ marginBottom: 6, borderRadius: 6, border: "1px solid #f0f0f0" }}
      bodyStyle={{ padding: "8px 10px" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: "#999" }}>#{issue.id}</span>
      </div>
      <div style={{ fontSize: 13, fontWeight: 500, lineHeight: 1.4, marginBottom: 6 }}>
        {issue.title}
      </div>
      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
        <Tag color={priorityColors[issue.priority]} style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px", margin: 0 }}>
          {issue.priority}
        </Tag>
        <Tag color={TYPE_COLORS[issue.issue_type]} style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px", margin: 0 }}>
          {issue.issue_type}
        </Tag>
        {issue.assignee_role && (
          <Tag style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px", margin: 0 }}>
            {issue.assignee_role}
          </Tag>
        )}
      </div>
    </Card>
  );
}
