import { useEffect, useState } from "react";
import { Table, Tag, Button, Space, Modal, Form, Input, Select, message, Popconfirm } from "antd";
import { PlusOutlined, RobotOutlined, TeamOutlined, UserOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { issuesApi } from "../api/issues";
import { milestonesApi } from "../api/milestones";
import type { Issue, Milestone } from "../api";
import { useProject } from "../hooks/useProject";

const { Option } = Select;

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

const typeColors: Record<string, string> = {
  bug: "red",
  feature: "green",
  task: "blue",
  improvement: "purple",
  documentation: "default",
  idea: "gold",
};

export default function Issues() {
  const navigate = useNavigate();
  const { currentProject } = useProject();
  const [issues, setIssues] = useState<Issue[]>([]);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [filters, setFilters] = useState<Record<string, any>>({});
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [sortBy, setSortBy] = useState<string>("created_at_desc");

  const fetchIssues = async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { ...filters, skip: (page - 1) * pageSize, limit: pageSize, sort_by: sortBy };
      if (currentProject) params.project_id = currentProject.id;
      const res = await issuesApi.list(params);
      setIssues(res.data.items);
      setTotal(res.data.total);
    } finally {
      setLoading(false);
    }
  };

  const fetchMilestones = async () => {
    const params: Record<string, any> = {};
    if (currentProject) params.project_id = currentProject.id;
    const res = await milestonesApi.list(params);
    setMilestones(res.data);
  };

  useEffect(() => {
    fetchIssues();
    fetchMilestones();
  }, [filters, page, pageSize, sortBy, currentProject]);

  const handleCreate = async (values: any) => {
    try {
      const payload = { ...values };
      if (currentProject) payload.project_id = currentProject.id;
      await issuesApi.create(payload);
      message.success("创建成功");
      setModalOpen(false);
      form.resetFields();
      fetchIssues();
    } catch {
      message.error("创建失败");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await issuesApi.remove(id);
      message.success("删除成功");
      fetchIssues();
    } catch {
      message.error("删除失败");
    }
  };

  const columns = [
    {
      title: "优先级",
      dataIndex: "priority",
      width: 80,
      render: (p: string) => <Tag color={priorityColors[p]}>{p}</Tag>,
    },
    {
      title: "标题",
      dataIndex: "title",
      render: (text: string, record: Issue) => (
        <a onClick={() => navigate(currentProject ? `/projects/${currentProject.slug}/issues/${record.id}` : `/issues/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: "类型",
      dataIndex: "issue_type",
      width: 100,
      render: (t: string) => <Tag color={typeColors[t]}>{t}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      render: (s: string) => <Tag color={statusColors[s]}>{s}</Tag>,
    },
    {
      title: "来源",
      dataIndex: "source",
      width: 100,
      render: (s: string) => {
        if (s === "ai_agent") return <Tag icon={<RobotOutlined />} color="purple">AI</Tag>;
        if (s === "collaborative") return <Tag icon={<TeamOutlined />} color="cyan">协作</Tag>;
        return <Tag icon={<UserOutlined />}>用户</Tag>;
      },
    },
    {
      title: "Milestone",
      dataIndex: "milestone_id",
      width: 120,
      render: (id?: number) => milestones.find((m) => m.id === id)?.title || "-",
    },
    {
      title: "操作",
      width: 120,
      render: (_: any, record: Issue) => (
        <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
          <Button type="link" danger size="small">
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <h2>Issues</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          新建 Issue
        </Button>
      </div>

      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="优先级"
          allowClear
          style={{ width: 100 }}
          onChange={(v) => setFilters((f) => ({ ...f, priority: v }))}
        >
          <Option value="P0">P0</Option>
          <Option value="P1">P1</Option>
          <Option value="P2">P2</Option>
          <Option value="P3">P3</Option>
        </Select>
        <Select
          placeholder="状态"
          allowClear
          style={{ width: 120 }}
          onChange={(v) => setFilters((f) => ({ ...f, status: v }))}
        >
          <Option value="open">open</Option>
          <Option value="in_progress">in_progress</Option>
          <Option value="review">review</Option>
          <Option value="deferred">deferred</Option>
          <Option value="closed">closed</Option>
        </Select>
        <Select
          placeholder="来源"
          allowClear
          style={{ width: 120 }}
          onChange={(v) => setFilters((f) => ({ ...f, source: v }))}
        >
          <Option value="user">user</Option>
          <Option value="ai_agent">ai_agent</Option>
        </Select>
        <Select
          placeholder="Milestone"
          allowClear
          style={{ width: 150 }}
          onChange={(v) => setFilters((f) => ({ ...f, milestone_id: v }))}
        >
          {milestones.map((m) => (
            <Option key={m.id} value={m.id}>
              {m.title}
            </Option>
          ))}
        </Select>
        <Select
          placeholder="排序"
          style={{ width: 150 }}
          value={sortBy}
          onChange={(v) => setSortBy(v)}
        >
          <Option value="created_at_desc">最新创建</Option>
          <Option value="created_at_asc">最早创建</Option>
          <Option value="updated_at_desc">最新更新</Option>
          <Option value="updated_at_asc">最早更新</Option>
          <Option value="priority_asc">优先级 高→低</Option>
          <Option value="priority_desc">优先级 低→高</Option>
        </Select>
      </Space>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={issues}
        loading={loading}
        pagination={{
          current: page,
          pageSize: pageSize,
          total: total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => {
            setPage(p);
            setPageSize(ps);
          },
        }}
      />

      <Modal
        title="新建 Issue"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} onFinish={handleCreate} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="priority" label="优先级" initialValue="P2">
            <Select>
              <Option value="P0">P0</Option>
              <Option value="P1">P1</Option>
              <Option value="P2">P2</Option>
              <Option value="P3">P3</Option>
            </Select>
          </Form.Item>
          <Form.Item name="issue_type" label="类型" initialValue="task">
            <Select>
              <Option value="bug">bug</Option>
              <Option value="feature">feature</Option>
              <Option value="task">task</Option>
              <Option value="improvement">improvement</Option>
              <Option value="documentation">documentation</Option>
              <Option value="idea">idea</Option>
            </Select>
          </Form.Item>
          <Form.Item name="milestone_id" label="Milestone">
            <Select allowClear>
              {milestones.map((m) => (
                <Option key={m.id} value={m.id}>
                  {m.title}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
