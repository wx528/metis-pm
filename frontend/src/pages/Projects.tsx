import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card,
  Row,
  Col,
  Tag,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Statistic,
  Typography,
  Tooltip,
} from "antd";
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  FolderOutlined,
  LinkOutlined,
  RightOutlined,
} from "@ant-design/icons";
import { projectsApi, type Project, type ProjectCreate, type ProjectUpdate } from "../api/projects";
import { useProject } from "../hooks/useProject";

const { Text, Paragraph } = Typography;

const statusColors: Record<string, string> = {
  active: "green",
  archived: "default",
};

export default function Projects() {
  const navigate = useNavigate();
  const { currentProject, setCurrentProject, refreshProjects } = useProject();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  const fetch = async () => {
    setLoading(true);
    try {
      const data = await projectsApi.list();
      setProjects(data);
    } catch {
      message.error("加载项目列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, []);

  const handleCreate = async (values: ProjectCreate) => {
    try {
      await projectsApi.create(values);
      message.success("项目创建成功");
      setCreateOpen(false);
      createForm.resetFields();
      fetch();
      refreshProjects();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      message.error(detail || "创建失败");
    }
  };

  const handleEdit = async (values: ProjectUpdate) => {
    if (!editingProject) return;
    try {
      await projectsApi.update(editingProject.slug, values);
      message.success("项目更新成功");
      setEditOpen(false);
      setEditingProject(null);
      editForm.resetFields();
      fetch();
      refreshProjects();
    } catch {
      message.error("更新失败");
    }
  };

  const handleDelete = async (slug: string) => {
    try {
      await projectsApi.delete(slug);
      message.success("项目删除成功");
      // 如果删除的是当前项目，切回 default
      if (currentProject?.slug === slug) {
        const remaining = projects.filter((p) => p.slug !== slug);
        const next = remaining.find((p) => p.slug === "default") || remaining[0] || null;
        setCurrentProject(next);
        if (next) {
          navigate(`/projects/${next.slug}/dashboard`);
        }
      }
      fetch();
      refreshProjects();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      message.error(detail || "删除失败");
    }
  };

  const openEdit = (project: Project) => {
    setEditingProject(project);
    editForm.setFieldsValue({
      name: project.name,
      description: project.description || "",
      repo_url: project.repo_url || "",
      status: project.status,
      owner: project.owner || "",
    });
    setEditOpen(true);
  };

  const enterProject = (project: Project) => {
    setCurrentProject(project);
    navigate(`/projects/${project.slug}/dashboard`);
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>
          <FolderOutlined style={{ marginRight: 8 }} />
          项目管理
        </h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          新建项目
        </Button>
      </div>

      <Row gutter={[16, 16]}>
        {projects.map((p) => (
          <Col span={8} key={p.id}>
            <Card
              title={
                <Space>
                  <FolderOutlined />
                  <span>{p.name}</span>
                  <Tag color={statusColors[p.status]}>{p.status}</Tag>
                </Space>
              }
              extra={
                <Space size={4}>
                  <Tooltip title="编辑">
                    <Button type="text" icon={<EditOutlined />} size="small" onClick={() => openEdit(p)} />
                  </Tooltip>
                  <Popconfirm
                    title="确认删除此项目？"
                    description="有关联数据时无法删除"
                    onConfirm={() => handleDelete(p.slug)}
                  >
                    <Tooltip title="删除">
                      <Button type="text" danger icon={<DeleteOutlined />} size="small" />
                    </Tooltip>
                  </Popconfirm>
                </Space>
              }
              loading={loading}
              hoverable
              style={{ cursor: "pointer" }}
              onClick={() => enterProject(p)}
            >
              <div style={{ minHeight: 48, marginBottom: 12 }}>
                {p.description ? (
                  <Paragraph type="secondary" ellipsis={{ rows: 2 }} style={{ marginBottom: 0 }}>
                    {p.description}
                  </Paragraph>
                ) : (
                  <Text type="secondary">无描述</Text>
                )}
              </div>

              {p.repo_url && (
                <div style={{ marginBottom: 12 }}>
                  <LinkOutlined style={{ marginRight: 4, color: "#999" }} />
                  <a href={p.repo_url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
                    {p.repo_url.replace(/^https?:\/\//, "")}
                  </a>
                </div>
              )}

              <Row gutter={8}>
                <Col span={6}>
                  <Statistic title="Issues" value={p.issue_count || 0} valueStyle={{ fontSize: 18 }} />
                </Col>
                <Col span={6}>
                  <Statistic title="进行中" value={p.open_issue_count || 0} valueStyle={{ fontSize: 18, color: "#1890ff" }} />
                </Col>
                <Col span={6}>
                  <Statistic title="Plans" value={p.plan_count || 0} valueStyle={{ fontSize: 18 }} />
                </Col>
                <Col span={6}>
                  <Statistic title="Milestones" value={p.milestone_count || 0} valueStyle={{ fontSize: 18 }} />
                </Col>
              </Row>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginTop: 12,
                  borderTop: "1px solid #f0f0f0",
                  paddingTop: 8,
                }}
              >
                <Text type="secondary" style={{ fontSize: 12 }}>
                  slug: {p.slug}
                  {p.owner ? ` · owner: ${p.owner}` : ""}
                </Text>
                <Button type="link" size="small" icon={<RightOutlined />}>
                  进入
                </Button>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {projects.length === 0 && !loading && (
        <div style={{ textAlign: "center", padding: 60, color: "#999" }}>暂无项目</div>
      )}

      {/* 新建项目弹窗 */}
      <Modal
        title="新建项目"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => createForm.submit()}
      >
        <Form form={createForm} onFinish={handleCreate} layout="vertical">
          <Form.Item
            name="name"
            label="项目名称"
            rules={[{ required: true, message: "请输入项目名称" }]}
          >
            <Input placeholder="如 My Project" />
          </Form.Item>
          <Form.Item
            name="slug"
            label="Slug（URL 标识）"
            rules={[
              { required: true, message: "请输入 slug" },
              { pattern: /^[a-z0-9][a-z0-9\-]*[a-z0-9]$/, message: "仅小写字母、数字、连字符，首尾须为字母或数字" },
            ]}
            extra="用于 URL 路径，如 my-project，创建后不可修改"
          >
            <Input placeholder="如 my-project" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="项目简介" />
          </Form.Item>
          <Form.Item name="repo_url" label="仓库地址">
            <Input placeholder="https://github.com/..." />
          </Form.Item>
          <Form.Item name="owner" label="负责人">
            <Input placeholder="如 admin" />
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue="active">
            <Select>
              <Select.Option value="active">active</Select.Option>
              <Select.Option value="archived">archived</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑项目弹窗 */}
      <Modal
        title="编辑项目"
        open={editOpen}
        onCancel={() => {
          setEditOpen(false);
          setEditingProject(null);
        }}
        onOk={() => editForm.submit()}
      >
        <Form form={editForm} onFinish={handleEdit} layout="vertical">
          <Form.Item name="name" label="项目名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="repo_url" label="仓库地址">
            <Input placeholder="https://github.com/..." />
          </Form.Item>
          <Form.Item name="owner" label="负责人">
            <Input />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select>
              <Select.Option value="active">active</Select.Option>
              <Select.Option value="archived">archived</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
