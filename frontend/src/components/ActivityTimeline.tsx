import { useEffect, useState } from "react";
import { Timeline, Tag, Spin } from "antd";
import {
  PlusOutlined,
  EditOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PauseCircleOutlined,
  MessageOutlined,
  DeleteOutlined,
  RobotOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { activityLogsApi } from "../api/activity_logs";
import type { ActivityLog } from "../api";

interface Props {
  entityType: string;
  entityId: number;
}

const actionLabels: Record<string, string> = {
  created: "创建",
  updated: "更新",
  status_changed: "状态变更",
  approved: "审批通过",
  rejected: "拒绝",
  deferred: "暂缓",
  commented: "评论",
  completed: "完成",
  deleted: "删除",
};

const actionIcons: Record<string, React.ReactNode> = {
  created: <PlusOutlined />,
  updated: <EditOutlined />,
  status_changed: <EditOutlined />,
  approved: <CheckCircleOutlined style={{ color: "#52c41a" }} />,
  rejected: <CloseCircleOutlined style={{ color: "#ff4d4f" }} />,
  deferred: <PauseCircleOutlined style={{ color: "#faad14" }} />,
  commented: <MessageOutlined />,
  completed: <CheckCircleOutlined style={{ color: "#52c41a" }} />,
  deleted: <DeleteOutlined style={{ color: "#ff4d4f" }} />,
};

export default function ActivityTimeline({ entityType, entityId }: Props) {
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      try {
        const res = await activityLogsApi.list(entityType, entityId, 50);
        setLogs(res.data);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [entityType, entityId]);

  if (loading) return <Spin size="small" />;
  if (logs.length === 0) return <div style={{ color: "#999", padding: 16 }}>暂无活动记录</div>;

  return (
    <Timeline
      mode="left"
      items={logs.map((log) => ({
        dot: actionIcons[log.action] || <EditOutlined />,
        label: log.created_at,
        children: (
          <div>
            <Tag color={log.actor === "ai_agent" ? "purple" : "blue"}>
              {log.actor === "ai_agent" ? <RobotOutlined /> : <UserOutlined />}
              {log.actor === "ai_agent" ? " AI Agent" : " 用户"}
            </Tag>
            <Tag>{actionLabels[log.action] || log.action}</Tag>
            {log.new_value?.comment_type === "handover" && (
              <Tag color="orange">🔄 交接</Tag>
            )}
            {log.new_value && log.action === "status_changed" && (
              <span style={{ color: "#666", marginLeft: 8 }}>
                {log.old_value?.status} → {log.new_value.status}
              </span>
            )}
            {log.new_value && log.action === "deferred" && (
              <span style={{ color: "#666", marginLeft: 8 }}>
                原因: {log.new_value.reason || "-"}
              </span>
            )}
            {log.new_value && log.action === "completed" && (
              <span style={{ color: "#666", marginLeft: 8 }}>
                由 {log.new_value.completed_by || "-"} 完成
              </span>
            )}
          </div>
        ),
      }))}
    />
  );
}
