import { useEffect, useState } from "react";
import { Card, Row, Col, Tag, Spin, Empty, Badge } from "antd";
import {
  RobotOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  MessageOutlined,
  ArrowRightOutlined,
} from "@ant-design/icons";
import { agentStatusApi } from "../api/agentStatus";
import type { AgentStatus, PendingHandover } from "../api/agentStatus";
import { useProject } from "../hooks/useProject";

const statusConfig: Record<string, { color: string; text: string }> = {
  online: { color: "#52c41a", text: "在线" },
  idle: { color: "#faad14", text: "空闲" },
  offline: { color: "#d9d9d9", text: "离线" },
};

const roleLabels: Record<string, string> = {
  agent: "开发",
  mate: "审查",
  tester: "测试",
  registrar: "登记",
};

const roleColors: Record<string, string> = {
  agent: "blue",
  mate: "purple",
  tester: "orange",
  registrar: "cyan",
};

interface Props {
  onHandoverClick?: (issueId: number) => void;
}

export default function AgentActivityPanel({ onHandoverClick }: Props) {
  const [loading, setLoading] = useState(true);
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [handovers, setHandovers] = useState<PendingHandover[]>([]);
  const { currentProject } = useProject();

  useEffect(() => {
    const load = async () => {
      if (!currentProject) return;
      setLoading(true);
      try {
        const res = await agentStatusApi.get(currentProject.id);
        setAgents(res.data.agents);
        setHandovers(res.data.pending_handovers);
      } catch (err) {
        console.error("Failed to load agent status:", err);
      } finally {
        setLoading(false);
      }
    };

    load();
    const timer = setInterval(load, 60000); // 每60秒刷新
    return () => clearInterval(timer);
  }, [currentProject]);

  if (loading) return <Spin size="small" />;

  return (
    <Card
      title={
        <span>
          <RobotOutlined /> Agent 协作看板
        </span>
      }
      style={{ marginBottom: 24 }}
    >
      {/* Agent 卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {agents.map((agent) => {
          const cfg = statusConfig[agent.status] || statusConfig.offline;
          return (
            <Col span={8} key={agent.identity}>
              <Card
                size="small"
                style={{ borderLeft: `4px solid ${cfg.color}` }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <Badge color={cfg.color} />
                  <strong>{agent.identity}</strong>
                  <Tag color={roleColors[agent.role] || "default"} style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px" }}>
                    {roleLabels[agent.role] || agent.role}
                  </Tag>
                </div>
                <div style={{ fontSize: 12, color: "#666" }}>
                  <div>
                    <CheckCircleOutlined /> 今日创建: {agent.today_created}
                  </div>
                  <div>
                    <ClockCircleOutlined /> 今日完成: {agent.today_completed}
                  </div>
                  {agent.today_reviewed > 0 && (
                    <div>
                      <MessageOutlined /> 今日审查: {agent.today_reviewed}
                    </div>
                  )}
                  <div style={{ marginTop: 4, color: agent.pending_tasks > 0 ? "#cf1322" : "#666" }}>
                    待办: {agent.pending_tasks}
                  </div>
                </div>
              </Card>
            </Col>
          );
        })}
        {agents.length === 0 && (
          <Col span={24}>
            <Empty description="暂无 Agent 活动数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          </Col>
        )}
      </Row>

      {/* 待交接任务 */}
      {handovers.length > 0 && (
        <div>
          <div style={{ fontWeight: "bold", marginBottom: 8 }}>
            <MessageOutlined /> 待交接任务
          </div>
          <div style={{ maxHeight: 200, overflowY: "auto" }}>
            {handovers.map((h) => (
              <div
                key={`${h.issue_id}-${h.created_at}`}
                style={{
                  padding: "8px 12px",
                  borderBottom: "1px solid #f0f0f0",
                  cursor: onHandoverClick ? "pointer" : "default",
                }}
                onClick={() => onHandoverClick?.(h.issue_id)}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Tag style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px" }}>Issue #{h.issue_id}</Tag>
                  <span style={{ flex: 1 }}>{h.title}</span>
                  <Tag color="default" style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px" }}>
                    {h.from_role}
                  </Tag>
                  <ArrowRightOutlined style={{ color: "#999" }} />
                  <Tag color="processing" style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px" }}>
                    @{h.to_role}
                  </Tag>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
