import { useEffect, useState } from "react";
import { Card, Row, Col, Tag, Spin, Empty, Badge, Tabs, Timeline, Progress, Tooltip } from "antd";
import {
  RobotOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  MessageOutlined,
  ArrowRightOutlined,
  ThunderboltOutlined,
  TeamOutlined,
  FireOutlined,
} from "@ant-design/icons";
import { agentStatusApi } from "../api/agentStatus";
import type {
  AgentStatus,
  PendingHandover,
  CollaborationFlowItem,
  ActivityStreamItem,
  WorkloadIssue,
} from "../api/agentStatus";
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
  unassigned: "未分配",
};

const roleColors: Record<string, string> = {
  agent: "blue",
  mate: "purple",
  tester: "orange",
  registrar: "cyan",
  unassigned: "default",
};

const statusLabels: Record<string, string> = {
  open: "待处理",
  in_progress: "进行中",
  review: "审查中",
  closed: "已完成",
  cancelled: "已取消",
};

const priorityColors: Record<string, string> = {
  P0: "red",
  P1: "orange",
  P2: "blue",
  P3: "default",
};

const actionLabels: Record<string, string> = {
  created: "创建",
  status_changed: "状态变更",
  completed: "完成",
  approved: "通过",
  rejected: "驳回",
  updated: "更新",
  commented: "评论",
};

interface Props {
  onHandoverClick?: (issueId: number) => void;
  onIssueClick?: (issueId: number) => void;
}

export default function AgentActivityPanel({ onHandoverClick, onIssueClick }: Props) {
  const [loading, setLoading] = useState(true);
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [handovers, setHandovers] = useState<PendingHandover[]>([]);
  const [flow, setFlow] = useState<CollaborationFlowItem[]>([]);
  const [activity, setActivity] = useState<ActivityStreamItem[]>([]);
  const [workload, setWorkload] = useState<Record<string, WorkloadIssue[]>>({});
  const { currentProject } = useProject();

  useEffect(() => {
    const load = async () => {
      if (!currentProject) return;
      setLoading(true);
      try {
        const res = await agentStatusApi.get(currentProject.id, {
          include_flow: true,
          include_activity: true,
          activity_limit: 30,
        });
        setAgents(res.data.agents);
        setHandovers(res.data.pending_handovers);
        setFlow(res.data.collaboration_flow || []);
        setActivity(res.data.activity_stream || []);
        setWorkload(res.data.workload || {});
      } catch (err) {
        console.error("Failed to load agent status:", err);
      } finally {
        setLoading(false);
      }
    };

    load();
    const timer = setInterval(load, 30000); // 30秒刷新
    return () => clearInterval(timer);
  }, [currentProject]);

  if (loading) return <Spin />;

  // 计算工作负载统计
  const totalWorkload = Object.values(workload).flat().length;
  const maxWorkload = Math.max(...Object.values(workload).map(w => w.length), 1);

  const tabItems = [
    {
      key: "overview",
      label: (
        <span>
          <TeamOutlined /> 概览
        </span>
      ),
      children: (
        <>
          {/* Agent 状态卡片 */}
          <Row gutter={16} style={{ marginBottom: 24 }}>
            {agents.map((agent) => {
              const cfg = statusConfig[agent.status] || statusConfig.offline;
              return (
                <Col span={6} key={agent.identity}>
                  <Card
                    size="small"
                    style={{ borderLeft: `4px solid ${cfg.color}` }}
                    hoverable
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                      <Badge color={cfg.color} />
                      <strong>{agent.identity}</strong>
                      <Tag
                        color={roleColors[agent.role] || "default"}
                        style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px" }}
                      >
                        {roleLabels[agent.role] || agent.role}
                      </Tag>
                    </div>
                    <Row gutter={8}>
                      <Col span={8}>
                        <div style={{ textAlign: "center" }}>
                          <div style={{ fontSize: 20, fontWeight: "bold", color: "#1890ff" }}>
                            {agent.today_created}
                          </div>
                          <div style={{ fontSize: 11, color: "#666" }}>创建</div>
                        </div>
                      </Col>
                      <Col span={8}>
                        <div style={{ textAlign: "center" }}>
                          <div style={{ fontSize: 20, fontWeight: "bold", color: "#52c41a" }}>
                            {agent.today_completed}
                          </div>
                          <div style={{ fontSize: 11, color: "#666" }}>完成</div>
                        </div>
                      </Col>
                      <Col span={8}>
                        <div style={{ textAlign: "center" }}>
                          <div
                            style={{
                              fontSize: 20,
                              fontWeight: "bold",
                              color: agent.today_reviewed > 0 ? "#722ed1" : "#666",
                            }}
                          >
                            {agent.today_reviewed}
                          </div>
                          <div style={{ fontSize: 11, color: "#666" }}>审查</div>
                        </div>
                      </Col>
                    </Row>
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

          {/* 工作负载分布 */}
          <Card title="工作负载" size="small" style={{ marginBottom: 24 }}>
            <Row gutter={16}>
              {Object.entries(workload).map(([role, issues]) => (
                <Col span={6} key={role}>
                  <div style={{ marginBottom: 8 }}>
                    <Tag color={roleColors[role]}>{roleLabels[role] || role}</Tag>
                    <span style={{ fontWeight: "bold" }}>{issues.length}</span>
                    <span style={{ color: "#999", marginLeft: 4 }}>个任务</span>
                  </div>
                  <Progress
                    percent={Math.round((issues.length / maxWorkload) * 100)}
                    strokeColor={role === "unassigned" ? "#d9d9d9" : undefined}
                    size="small"
                  />
                  <div style={{ maxHeight: 120, overflowY: "auto", marginTop: 8 }}>
                    {issues.slice(0, 5).map((issue) => (
                      <div
                        key={issue.id}
                        style={{
                          fontSize: 12,
                          padding: "4px 0",
                          cursor: onIssueClick ? "pointer" : "default",
                          color: "#1890ff",
                        }}
                        onClick={() => onIssueClick?.(issue.id)}
                      >
                        <Tag
                          color={priorityColors[issue.priority]}
                          style={{ fontSize: 10, lineHeight: "14px", padding: "0 2px" }}
                        >
                          {issue.priority}
                        </Tag>
                        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          #{issue.id} {issue.title}
                        </span>
                      </div>
                    ))}
                    {issues.length > 5 && (
                      <div style={{ fontSize: 11, color: "#999" }}>还有 {issues.length - 5} 个...</div>
                    )}
                  </div>
                </Col>
              ))}
              {Object.keys(workload).length === 0 && (
                <Col span={24}>
                  <Empty description="暂无进行中的任务" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                </Col>
              )}
            </Row>
          </Card>

          {/* 待交接任务 */}
          {handovers.length > 0 && (
            <Card title="待交接任务" size="small">
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
                    <Tag style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px" }}>
                      Issue #{h.issue_id}
                    </Tag>
                    <span style={{ flex: 1 }}>{h.title}</span>
                    <Tag color="default" style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px" }}>
                      {roleLabels[h.from_role] || h.from_role}
                    </Tag>
                    <ArrowRightOutlined style={{ color: "#999" }} />
                    <Tag color="processing" style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px" }}>
                      {roleLabels[h.to_role] || h.to_role}
                    </Tag>
                  </div>
                </div>
              ))}
            </Card>
          )}
        </>
      ),
    },
    {
      key: "flow",
      label: (
        <span>
          <ThunderboltOutlined /> 协作流程
        </span>
      ),
      children: (
        <Card size="small">
          {flow.length > 0 ? (
            <Timeline
              items={flow.map((item) => ({
                color: item.action === "completed" || item.action === "approved" ? "green" :
                       item.action === "rejected" ? "red" : "blue",
                children: (
                  <div>
                    <div style={{ marginBottom: 4 }}>
                      <Tag color={roleColors[item.from_role]} style={{ fontSize: 10, lineHeight: "14px", padding: "0 4px" }}>
                        {roleLabels[item.from_role] || item.from_role}
                      </Tag>
                      <ArrowRightOutlined style={{ color: "#999", margin: "0 4px" }} />
                      <Tag color={roleColors[item.to_role]} style={{ fontSize: 10, lineHeight: "14px", padding: "0 4px" }}>
                        {roleLabels[item.to_role] || item.to_role}
                      </Tag>
                      <Tag style={{ fontSize: 10, lineHeight: "14px", padding: "0 4px", marginLeft: 8 }}>
                        {actionLabels[item.action] || item.action}
                      </Tag>
                    </div>
                    <div
                      style={{ cursor: onIssueClick ? "pointer" : "default", color: "#1890ff" }}
                      onClick={() => onIssueClick?.(item.issue_id)}
                    >
                      Issue #{item.issue_id}
                      {item.old_status && item.new_status && (
                        <span style={{ marginLeft: 8, color: "#666" }}>
                          {statusLabels[item.old_status] || item.old_status}
                          <ArrowRightOutlined style={{ margin: "0 4px", fontSize: 10 }} />
                          {statusLabels[item.new_status] || item.new_status}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 11, color: "#999", marginTop: 4 }}>
                      {item.actor} · {new Date(item.created_at).toLocaleString()}
                    </div>
                  </div>
                ),
              }))}
            />
          ) : (
            <Empty description="暂无协作流程数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>
      ),
    },
    {
      key: "activity",
      label: (
        <span>
          <FireOutlined /> 实时活动
        </span>
      ),
      children: (
        <Card size="small">
          {activity.length > 0 ? (
            <Timeline
              items={activity.map((item) => ({
                color: item.action === "completed" || item.action === "approved" ? "green" :
                       item.action === "rejected" ? "red" : "gray",
                children: (
                  <div>
                    <div style={{ marginBottom: 4 }}>
                      <Tag color={roleColors[item.role]} style={{ fontSize: 10, lineHeight: "14px", padding: "0 4px" }}>
                        {item.actor}
                      </Tag>
                      <Tag style={{ fontSize: 10, lineHeight: "14px", padding: "0 4px" }}>
                        {actionLabels[item.action] || item.action}
                      </Tag>
                      <Tag style={{ fontSize: 10, lineHeight: "14px", padding: "0 4px" }}>
                        {item.entity_type}
                      </Tag>
                    </div>
                    <div
                      style={{ cursor: onIssueClick ? "pointer" : "default", color: "#1890ff" }}
                      onClick={() => onIssueClick?.(item.entity_id)}
                    >
                      {item.entity_type} #{item.entity_id}
                    </div>
                    <div style={{ fontSize: 11, color: "#999", marginTop: 4 }}>
                      {new Date(item.created_at).toLocaleString()}
                    </div>
                  </div>
                ),
              }))}
            />
          ) : (
            <Empty description="暂无活动记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>
      ),
    },
  ];

  return (
    <Card
      title={
        <span>
          <RobotOutlined /> Agent 协作看板
          {totalWorkload > 0 && (
            <Tag color="processing" style={{ marginLeft: 8 }}>
              {totalWorkload} 个进行中
            </Tag>
          )}
        </span>
      }
      style={{ marginBottom: 24 }}
    >
      <Tabs items={tabItems} />
    </Card>
  );
}
