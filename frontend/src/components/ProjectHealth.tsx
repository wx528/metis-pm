import { Card, Progress, List, Tag, Space, Typography } from "antd";
import {
  CheckCircleOutlined,
  WarningOutlined,
  ClockCircleOutlined,
  FireOutlined,
} from "@ant-design/icons";

const { Text } = Typography;

interface HealthData {
  overall_score: number;
  level: string;
  color: string;
  dimensions: {
    issue: {
      score: number;
      details: {
        total: number;
        closed: number;
        open: number;
        in_progress: number;
        p0: number;
        p1: number;
        close_rate: number;
      };
    };
    plan: {
      score: number;
      details: {
        total: number;
        completed: number;
        pending: number;
        close_rate: number;
      };
    };
    activity: {
      score: number;
      details: {
        recent_7days: number;
      };
    };
  };
  suggestions: string[];
}

const levelLabels: Record<string, { text: string; icon: React.ReactNode }> = {
  excellent: { text: "优秀", icon: <CheckCircleOutlined /> },
  good: { text: "良好", icon: <CheckCircleOutlined /> },
  warning: { text: "警告", icon: <WarningOutlined /> },
  critical: { text: "危险", icon: <FireOutlined /> },
};

export default function ProjectHealth({ data }: { data: HealthData | null }) {
  if (!data) {
    return <Card title="项目健康度" loading />;
  }

  const level = levelLabels[data.level] || levelLabels.warning;

  return (
    <Card
      title={
        <Space>
          <span>项目健康度</span>
          <Tag color={data.color} icon={level.icon}>
            {level.text}
          </Tag>
        </Space>
      }
    >
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <Progress
          type="circle"
          percent={data.overall_score}
          format={() => `${data.overall_score}`}
          strokeColor={data.color}
          size={120}
        />
        <div style={{ marginTop: 8, fontSize: 14, color: "#666" }}>综合得分</div>
      </div>

      <List
        size="small"
        dataSource={[
          {
            title: "Issue 健康度",
            score: data.dimensions.issue.score,
            details: (
              <Space size={[0, 4]} wrap>
                <Tag color="blue">总计 {data.dimensions.issue.details.total}</Tag>
                <Tag color="green">已关闭 {data.dimensions.issue.details.closed}</Tag>
                <Tag color="orange">进行中 {data.dimensions.issue.details.in_progress}</Tag>
                {data.dimensions.issue.details.p0 > 0 && (
                  <Tag color="red">P0 {data.dimensions.issue.details.p0}</Tag>
                )}
                {data.dimensions.issue.details.p1 > 0 && (
                  <Tag color="orange">P1 {data.dimensions.issue.details.p1}</Tag>
                )}
                <Text type="secondary" style={{ fontSize: 12 }}>
                  关闭率 {data.dimensions.issue.details.close_rate}%
                </Text>
              </Space>
            ),
          },
          {
            title: "Plan 健康度",
            score: data.dimensions.plan.score,
            details: (
              <Space size={[0, 4]} wrap>
                <Tag color="blue">总计 {data.dimensions.plan.details.total}</Tag>
                <Tag color="green">已完成 {data.dimensions.plan.details.completed}</Tag>
                {data.dimensions.plan.details.pending > 0 && (
                  <Tag color="orange">待审批 {data.dimensions.plan.details.pending}</Tag>
                )}
                <Text type="secondary" style={{ fontSize: 12 }}>
                  完成率 {data.dimensions.plan.details.close_rate}%
                </Text>
              </Space>
            ),
          },
          {
            title: "活跃度",
            score: data.dimensions.activity.score,
            details: (
              <Space size={[0, 4]} wrap>
                <Tag color="blue">最近7天 {data.dimensions.activity.details.recent_7days} 次活动</Tag>
              </Space>
            ),
          },
        ]}
        renderItem={(item) => (
          <List.Item>
            <List.Item.Meta
              title={
                <Space>
                  <span>{item.title}</span>
                  <Progress
                    percent={item.score}
                    size="small"
                    style={{ width: 100 }}
                    strokeColor={item.score >= 80 ? "#52c41a" : item.score >= 60 ? "#1890ff" : item.score >= 40 ? "#faad14" : "#ff4d4f"}
                  />
                </Space>
              }
              description={item.details}
            />
          </List.Item>
        )}
      />

      {data.suggestions.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Text strong style={{ fontSize: 13 }}>建议：</Text>
          <ul style={{ marginTop: 8, paddingLeft: 20, fontSize: 13 }}>
            {data.suggestions.map((s, i) => (
              <li key={i} style={{ color: "#666", marginBottom: 4 }}>
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
