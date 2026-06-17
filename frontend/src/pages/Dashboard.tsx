import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Row, Col, Card, Statistic, List, Tag, Empty } from "antd";
import { BugOutlined, ProjectOutlined } from "@ant-design/icons";
import { projectsApi, type ProjectWithStats } from "../api/projects";
import { issuesApi, type Issue } from "../api/issues";

const priorityColors: Record<string, string> = {
  P0: "red",
  P1: "orange",
  P2: "blue",
  P3: "default",
};

const statusColors: Record<string, string> = {
  open: "blue",
  in_progress: "processing",
  review: "purple",
  deferred: "warning",
  closed: "success",
  cancelled: "default",
};

export default function Dashboard() {
  const { projectSlug } = useParams<{ projectSlug: string }>();
  const slug = projectSlug || "default";
  const [project, setProject] = useState<ProjectWithStats | null>(null);
  const [recentIssues, setRecentIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const projRes = await projectsApi.get(slug);
        const projectData = projRes.data;
        setProject(projectData);
        const issuesRes = await issuesApi.list({ project_id: projectData.id, limit: 10 });
        setRecentIssues(issuesRes.data.items);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [slug]);

  if (loading) return <div style={{ textAlign: "center", padding: 40 }}>加载中...</div>;
  if (!project) return <Empty description="暂无数据" />;

  return (
    <div>
      <h2>仪表盘 — {project.name}</h2>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic title="总 Issues" value={project.issue_count} prefix={<BugOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="待处理 Issues"
              value={project.open_issue_count}
              valueStyle={{ color: "#1890ff" }}
              prefix={<BugOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="计划数" value={project.plan_count} prefix={<ProjectOutlined />} />
          </Card>
        </Col>
      </Row>

      <Card title="最近 Issues">
        <List
          dataSource={recentIssues}
          renderItem={(issue) => (
            <List.Item>
              <List.Item.Meta
                title={
                  <span>
                    <Tag color={priorityColors[issue.priority]}>{issue.priority}</Tag>
                    {issue.title}
                  </span>
                }
                description={<Tag color={statusColors[issue.status]}>{issue.status}</Tag>}
              />
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
}
