import { useEffect, useState } from "react";
import { Row, Col, Card, Statistic, List, Tag, Spin, Timeline, Progress, Select, Empty } from "antd";
import {
  BugOutlined,
  ProjectOutlined,
  ClockCircleOutlined,
  CloudServerOutlined,
  RobotOutlined,
  TeamOutlined,
  UserOutlined,
  PlusOutlined,
  EditOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PauseCircleOutlined,
  MessageOutlined,
} from "@ant-design/icons";
import { dashboardApi } from "../api/dashboard";
import { statsApi } from "../api/stats";
import type { DashboardData } from "../api";
import type { AgentProductivity, PlanCompletion } from "../api/stats";
import { useProject } from "../hooks/useProject";

const actionIcons: Record<string, React.ReactNode> = {
  created: <PlusOutlined />,
  updated: <EditOutlined />,
  approved: <CheckCircleOutlined style={{ color: "#52c41a" }} />,
  rejected: <CloseCircleOutlined style={{ color: "#ff4d4f" }} />,
  deferred: <PauseCircleOutlined style={{ color: "#faad14" }} />,
  commented: <MessageOutlined />,
  completed: <CheckCircleOutlined style={{ color: "#52c41a" }} />,
};

const actionLabels: Record<string, string> = {
  created: "创建",
  updated: "更新",
  approved: "审批通过",
  rejected: "拒绝",
  deferred: "暂缓",
  commented: "评论",
  completed: "完成",
};


export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DashboardData | null>(null);
  const [productivity, setProductivity] = useState<AgentProductivity | null>(null);
  const [planCompletion, setPlanCompletion] = useState<PlanCompletion | null>(null);
  const [period, setPeriod] = useState<string>("all");
  const { currentProject } = useProject();

  useEffect(() => {
    if (!currentProject) return;
    const fetch = async () => {
      setLoading(true);
      try {
        const [dashboardRes, prodRes, planRes] = await Promise.all([
          dashboardApi.get({ project_id: currentProject.id }),
          statsApi.agentProductivity(currentProject.id, period),
          statsApi.planCompletion(currentProject.id),
        ]);
        setData(dashboardRes.data);
        setProductivity(prodRes);
        setPlanCompletion(planRes);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [currentProject, period]);

  if (loading || !data) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  const priorityColor: Record<string, string> = {
    P0: "red",
    P1: "orange",
    P2: "blue",
    P3: "default",
  };

  const statusColor: Record<string, string> = {
    open: "blue",
    in_progress: "processing",
    review: "purple",
    deferred: "warning",
    closed: "success",
    cancelled: "default",
  };

  const actorColorMap: Record<string, string> = {};
  const barColors = ["#1890ff", "#52c41a", "#722ed1", "#fa8c16", "#eb2f96", "#13c2c2"];
  productivity?.agents.forEach((a, i) => {
    actorColorMap[a.actor] = barColors[i % barColors.length];
  });

  return (
    <div>
      <h2>仪表盘{currentProject ? ` — ${currentProject.name}` : ""}</h2>

      {/* Issues 统计 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={4}>
          <Card>
            <Statistic
              title="P0 紧急"
              value={data.issues.p0}
              valueStyle={{ color: "#cf1322" }}
              prefix={<BugOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="P1 高优"
              value={data.issues.p1}
              valueStyle={{ color: "#fa8c16" }}
              prefix={<BugOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="进行中"
              value={data.issues.in_progress}
              valueStyle={{ color: "#1890ff" }}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="已暂缓"
              value={data.issues.deferred}
              valueStyle={{ color: "#faad14" }}
              prefix={<PauseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="AI 发现"
              value={data.issues.ai_agent}
              prefix={<RobotOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="总 Issues" value={data.issues.total} prefix={<BugOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* Agent 产出对比 + Plan 完成率 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={14}>
          <Card
            title="Agent 产出对比"
            extra={
              <Select value={period} onChange={setPeriod} size="small" style={{ width: 100 }}>
                <Select.Option value="week">本周</Select.Option>
                <Select.Option value="month">本月</Select.Option>
                <Select.Option value="all">全部</Select.Option>
              </Select>
            }
          >
            {productivity && productivity.agents.length > 0 ? (
              <div>
                <div style={{ marginBottom: 12, fontSize: 12, color: "#999" }}>
                  <span style={{ display: "inline-block", width: 10, height: 10, background: "#1890ff", borderRadius: 2, marginRight: 4, verticalAlign: "middle" }} />
                  创建
                  <span style={{ display: "inline-block", width: 10, height: 10, background: "#52c41a", borderRadius: 2, marginLeft: 16, marginRight: 4, verticalAlign: "middle" }} />
                  完成
                </div>
                {(() => {
                  const maxVal = Math.max(...productivity.agents.flatMap((a) => [a.created, a.completed]), 1);
                  return productivity.agents.map((agent) => (
                    <div key={agent.actor} style={{ marginBottom: 12 }}>
                      <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>
                        <Tag color={actorColorMap[agent.actor] || "blue"}>{agent.actor}</Tag>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                        <span style={{ width: 36, fontSize: 11, color: "#999" }}>创建</span>
                        <div style={{ flex: 1, background: "#f0f0f0", borderRadius: 4, height: 16, overflow: "hidden" }}>
                          <div style={{ height: "100%", width: `${(agent.created / maxVal) * 100}%`, background: "#1890ff", borderRadius: 4, transition: "width 0.3s", minWidth: agent.created > 0 ? 4 : 0 }} />
                        </div>
                        <span style={{ width: 30, fontSize: 12, fontWeight: 500 }}>{agent.created}</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span style={{ width: 36, fontSize: 11, color: "#999" }}>完成</span>
                        <div style={{ flex: 1, background: "#f0f0f0", borderRadius: 4, height: 16, overflow: "hidden" }}>
                          <div style={{ height: "100%", width: `${(agent.completed / maxVal) * 100}%`, background: "#52c41a", borderRadius: 4, transition: "width 0.3s", minWidth: agent.completed > 0 ? 4 : 0 }} />
                        </div>
                        <span style={{ width: 30, fontSize: 12, fontWeight: 500 }}>{agent.completed}</span>
                      </div>
                    </div>
                  ));
                })()}
              </div>
            ) : (
              <Empty description="暂无产出数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
        <Col span={10}>
          <Card title="Plan 完成率">
            {planCompletion && planCompletion.total_plans > 0 ? (
              <div>
                <div style={{ textAlign: "center", marginBottom: 16 }}>
                  <Progress
                    type="circle"
                    percent={planCompletion.overall_completion_rate}
                    format={() => `${planCompletion.overall_completion_rate}%`}
                    size={100}
                  />
                  <div style={{ marginTop: 8, fontSize: 13, color: "#666" }}>
                    {planCompletion.total_done_items} / {planCompletion.total_items} 项已完成
                  </div>
                </div>
                <div style={{ maxHeight: 200, overflowY: "auto" }}>
                  {planCompletion.plans.slice(0, 5).map((plan) => (
                    <div key={plan.id} style={{ marginBottom: 8 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                        <span>{plan.title}</span>
                        <span style={{ color: "#999" }}>{plan.done_items}/{plan.total_items}</span>
                      </div>
                      <Progress percent={plan.completion_rate} size="small" />
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <Empty description="暂无计划数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
      </Row>

      {/* Plans + Servers */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="待审批计划"
              value={data.plans.pending_approval}
              valueStyle={{ color: data.plans.pending_approval > 0 ? "#cf1322" : undefined }}
              prefix={<ProjectOutlined />}
              suffix={`/ ${data.plans.total}`}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="活跃计划"
              value={data.plans.active}
              prefix={<ProjectOutlined />}
              suffix={`/ ${data.plans.total}`}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="服务器状态"
              value={data.servers.active}
              prefix={<CloudServerOutlined />}
              suffix={
                <span style={{ fontSize: 14 }}>
                  <Tag color="success">{data.servers.active} 正常</Tag>
                  {data.servers.maintenance > 0 && <Tag color="warning">{data.servers.maintenance} 维护</Tag>}
                  {data.servers.offline > 0 && <Tag color="error">{data.servers.offline} 离线</Tag>}
                </span>
              }
            />
          </Card>
        </Col>
      </Row>

      {/* 列表区域 */}
      <Row gutter={16}>
        <Col span={8}>
          <Card title="待审批计划" extra={data.pending_plans.length > 0 ? <Tag color="red">需处理</Tag> : null}>
            {data.pending_plans.length === 0 ? (
              <div style={{ color: "#999", textAlign: "center", padding: 24 }}>暂无待审批计划</div>
            ) : (
              <List
                dataSource={data.pending_plans}
                renderItem={(plan) => (
                  <List.Item>
                    <List.Item.Meta
                      title={
                        <span>
                          {plan.title}
                          {plan.proposed_by === "ai_agent" && (
                            <Tag color="purple" style={{ marginLeft: 8 }}>
                              <RobotOutlined /> AI
                            </Tag>
                          )}
                          {plan.proposed_by === "collaborative" && (
                            <Tag color="cyan" style={{ marginLeft: 8 }}>
                              <TeamOutlined /> 协作
                            </Tag>
                          )}
                        </span>
                      }
                      description={plan.description || "无描述"}
                    />
                    <Tag color="warning">待审批</Tag>
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>
        <Col span={8}>
          <Card title="最近 Issues">
            <List
              dataSource={data.recent_issues}
              renderItem={(issue) => (
                <List.Item>
                  <List.Item.Meta
                    title={
                      <span>
                        <Tag color={priorityColor[issue.priority]}>{issue.priority}</Tag>
                        {issue.title}
                      </span>
                    }
                    description={
                      <span>
                        <Tag color={statusColor[issue.status]}>{issue.status}</Tag>
                        {issue.source === "ai_agent" && <Tag color="purple">AI</Tag>}
                        {issue.source === "collaborative" && <Tag color="cyan">协作</Tag>}
                      </span>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="最近活动">
            {data.recent_activities.length === 0 ? (
              <div style={{ color: "#999", textAlign: "center", padding: 24 }}>暂无活动</div>
            ) : (
              <Timeline
                mode="left"
                items={data.recent_activities.map((log) => ({
                  dot: actionIcons[log.action] || <EditOutlined />,
                  label: new Date(log.created_at).toLocaleString("zh-CN", {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  }),
                  children: (
                    <div>
                      <Tag color={log.actor === "ai_agent" ? "purple" : "blue"} style={{ fontSize: 12 }}>
                        {log.actor === "ai_agent" ? <RobotOutlined /> : <UserOutlined />}
                      </Tag>{" "}
                      {actionLabels[log.action] || log.action}
                      <span style={{ color: "#999" }}> {log.entity_type}#{log.entity_id}</span>
                    </div>
                  ),
                }))}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
