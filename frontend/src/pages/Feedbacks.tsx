import { useEffect, useState } from "react";
import {
  Table,
  Tag,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Typography,
  Card,
  Statistic,
  Row,
  Col,
  Tooltip,
} from "antd";
import {
  PlusOutlined,
  CheckCircleOutlined,
  EyeOutlined,
  DeleteOutlined,
  BarChartOutlined,
} from "@ant-design/icons";
import { feedbackApi, type Feedback, type CreateFeedbackRequest, type FeedbackStats } from "../api/feedback";
import { useAuth } from "../hooks/useAuth";

const { Text, Paragraph } = Typography;

const categoryConfig: Record<string, { label: string; color: string }> = {
  bug: { label: "Bug", color: "red" },
  feature_request: { label: "功能请求", color: "blue" },
  improvement: { label: "改进建议", color: "orange" },
  ux: { label: "使用体验", color: "purple" },
  workflow: { label: "工作流", color: "cyan" },
  other: { label: "其他", color: "default" },
};

const statusConfig: Record<string, { label: string; color: string }> = {
  open: { label: "待处理", color: "blue" },
  acknowledged: { label: "已确认", color: "orange" },
  in_progress: { label: "处理中", color: "processing" },
  resolved: { label: "已解决", color: "green" },
  wont_fix: { label: "不修复", color: "default" },
};

const priorityColors: Record<string, string> = {
  P0: "red",
  P1: "orange",
  P2: "blue",
  P3: "default",
};

export default function Feedbacks() {
  const { role } = useAuth();
  const isAdmin = role === "admin";

  const [feedbacks, setFeedbacks] = useState<Feedback[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  const [createOpen, setCreateOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [replyOpen, setReplyOpen] = useState(false);
  const [currentFeedback, setCurrentFeedback] = useState<Feedback | null>(null);
  const [createForm] = Form.useForm();
  const [replyForm] = Form.useForm();

  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [statsOpen, setStatsOpen] = useState(false);

  const fetch = async (p = page, cat = categoryFilter, st = statusFilter) => {
    setLoading(true);
    try {
      const params: Record<string, any> = { skip: (p - 1) * 20, limit: 20 };
      if (cat) params.category = cat;
      if (st) params.status = st;
      const data = await feedbackApi.list(params);
      setFeedbacks(data.items);
      setTotal(data.total);
    } catch {
      message.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    if (!isAdmin) return;
    try {
      const data = await feedbackApi.stats();
      setStats(data);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetch();
  }, [page, categoryFilter, statusFilter]);

  useEffect(() => {
    if (statsOpen) fetchStats();
  }, [statsOpen]);

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      await feedbackApi.create(values as CreateFeedbackRequest);
      message.success("意见已提交");
      setCreateOpen(false);
      createForm.resetFields();
      fetch();
    } catch {
      // validation error
    }
  };

  const handleReply = async () => {
    if (!currentFeedback) return;
    try {
      const values = await replyForm.validateFields();
      await feedbackApi.update(currentFeedback.id, {
        admin_reply: values.admin_reply,
        status: values.status || "acknowledged",
      });
      message.success("回复已保存");
      setReplyOpen(false);
      replyForm.resetFields();
      fetch();
    } catch {
      // validation error
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await feedbackApi.delete(id);
      message.success("已删除");
      fetch();
    } catch {
      message.error("删除失败");
    }
  };

  const handleStatusChange = async (id: number, status: string) => {
    try {
      await feedbackApi.update(id, { status });
      message.success("状态已更新");
      fetch();
    } catch {
      message.error("更新失败");
    }
  };

  const columns = [
    {
      title: "ID",
      dataIndex: "id",
      width: 60,
    },
    {
      title: "标题",
      dataIndex: "title",
      width: 200,
      ellipsis: true,
    },
    {
      title: "分类",
      dataIndex: "category",
      width: 100,
      render: (v: string) => {
        const cfg = categoryConfig[v] || categoryConfig.other;
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      render: (v: string, record: Feedback) => {
        const cfg = statusConfig[v] || statusConfig.open;
        if (isAdmin) {
          return (
            <Select
              value={v}
              size="small"
              style={{ width: 90 }}
              onChange={(val) => handleStatusChange(record.id, val)}
            >
              {Object.entries(statusConfig).map(([key, c]) => (
                <Select.Option key={key} value={key}>
                  {c.label}
                </Select.Option>
              ))}
            </Select>
          );
        }
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: "优先级",
      dataIndex: "priority",
      width: 80,
      render: (v: string) => <Tag color={priorityColors[v] || "default"}>{v}</Tag>,
    },
    {
      title: "提交者",
      dataIndex: "submitted_by",
      width: 120,
      ellipsis: true,
    },
    {
      title: "回复",
      dataIndex: "admin_reply",
      width: 80,
      render: (v: string | null) =>
        v ? (
          <Tooltip title={v.length > 50 ? v.slice(0, 50) + "..." : v}>
            <Tag color="green" icon={<CheckCircleOutlined />}>已回复</Tag>
          </Tooltip>
        ) : (
          <Tag>待回复</Tag>
        ),
    },
    {
      title: "时间",
      dataIndex: "created_at",
      width: 160,
      render: (v: string) => new Date(v).toLocaleString("zh-CN"),
    },
    {
      title: "操作",
      width: 150,
      render: (_: unknown, record: Feedback) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => {
              setCurrentFeedback(record);
              setDetailOpen(true);
            }}
          />
          {isAdmin && (
            <>
              <Button
                type="link"
                size="small"
                onClick={() => {
                  setCurrentFeedback(record);
                  replyForm.setFieldsValue({
                    admin_reply: record.admin_reply || "",
                    status: record.status,
                  });
                  setReplyOpen(true);
                }}
              >
                回复
              </Button>
              <Popconfirm title="确认删除?" onConfirm={() => handleDelete(record.id)}>
                <Button type="link" size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Space>
          <Select
            placeholder="分类筛选"
            allowClear
            style={{ width: 130 }}
            value={categoryFilter}
            onChange={(v) => {
              setCategoryFilter(v);
              setPage(1);
            }}
          >
            {Object.entries(categoryConfig).map(([key, cfg]) => (
              <Select.Option key={key} value={key}>{cfg.label}</Select.Option>
            ))}
          </Select>
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 120 }}
            value={statusFilter}
            onChange={(v) => {
              setStatusFilter(v);
              setPage(1);
            }}
          >
            {Object.entries(statusConfig).map(([key, cfg]) => (
              <Select.Option key={key} value={key}>{cfg.label}</Select.Option>
            ))}
          </Select>
        </Space>
        <Space>
          {isAdmin && (
            <Button icon={<BarChartOutlined />} onClick={() => setStatsOpen(true)}>
              统计
            </Button>
          )}
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            提交意见
          </Button>
        </Space>
      </div>

      <Table
        dataSource={feedbacks}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 20,
          onChange: setPage,
          showTotal: (t) => `共 ${t} 条`,
        }}
        size="small"
      />

      {/* 提交意见 Modal */}
      <Modal
        title="提交意见"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => {
          setCreateOpen(false);
          createForm.resetFields();
        }}
        okText="提交"
        width={560}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true, message: "请输入标题" }]}>
            <Input placeholder="简短概括你的意见" maxLength={200} />
          </Form.Item>
          <Form.Item name="content" label="详细内容" rules={[{ required: true, message: "请输入内容" }]}>
            <Input.TextArea rows={4} placeholder="描述遇到的问题或改进建议..." />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="category" label="分类" initialValue="other">
                <Select>
                  {Object.entries(categoryConfig).map(([key, cfg]) => (
                    <Select.Option key={key} value={key}>{cfg.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="priority" label="优先级" initialValue="P2">
                <Select>
                  <Select.Option value="P0">P0 - 紧急</Select.Option>
                  <Select.Option value="P1">P1 - 高</Select.Option>
                  <Select.Option value="P2">P2 - 中</Select.Option>
                  <Select.Option value="P3">P3 - 低</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* 详情 Modal */}
      <Modal
        title={currentFeedback ? `意见 #${currentFeedback.id}` : ""}
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={600}
      >
        {currentFeedback && (
          <div>
            <div style={{ marginBottom: 12 }}>
              <Space>
                <Tag color={categoryConfig[currentFeedback.category]?.color}>
                  {categoryConfig[currentFeedback.category]?.label || currentFeedback.category}
                </Tag>
                <Tag color={statusConfig[currentFeedback.status]?.color}>
                  {statusConfig[currentFeedback.status]?.label || currentFeedback.status}
                </Tag>
                <Tag color={priorityColors[currentFeedback.priority]}>{currentFeedback.priority}</Tag>
              </Space>
            </div>
            <h3>{currentFeedback.title}</h3>
            <Paragraph>{currentFeedback.content}</Paragraph>
            <div style={{ color: "#999", fontSize: 12, marginBottom: 16 }}>
              提交者: {currentFeedback.submitted_by}
              {currentFeedback.submitted_by_role && ` (${currentFeedback.submitted_by_role})`}
              {" | "}
              {new Date(currentFeedback.created_at).toLocaleString("zh-CN")}
            </div>
            {currentFeedback.admin_reply ? (
              <Card size="small" title="管理员回复" style={{ background: "#f6ffed", borderColor: "#b7eb8f" }}>
                <Paragraph style={{ marginBottom: 4 }}>{currentFeedback.admin_reply}</Paragraph>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {currentFeedback.replied_by} | {currentFeedback.replied_at && new Date(currentFeedback.replied_at).toLocaleString("zh-CN")}
                </Text>
              </Card>
            ) : (
              <Card size="small" style={{ background: "#fafafa" }}>
                <Text type="secondary">管理员暂未回复</Text>
              </Card>
            )}
          </div>
        )}
      </Modal>

      {/* 回复 Modal (admin) */}
      <Modal
        title={`回复意见 #${currentFeedback?.id || ""}`}
        open={replyOpen}
        onOk={handleReply}
        onCancel={() => {
          setReplyOpen(false);
          replyForm.resetFields();
        }}
        okText="保存回复"
        width={560}
      >
        <Form form={replyForm} layout="vertical">
          <Form.Item name="status" label="状态" initialValue="acknowledged">
            <Select>
              {Object.entries(statusConfig).map(([key, cfg]) => (
                <Select.Option key={key} value={key}>{cfg.label}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="admin_reply" label="回复内容" rules={[{ required: true, message: "请输入回复" }]}>
            <Input.TextArea rows={4} placeholder="输入管理员回复..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* 统计 Modal (admin) */}
      <Modal
        title="意见箱统计"
        open={statsOpen}
        onCancel={() => setStatsOpen(false)}
        footer={null}
        width={600}
      >
        {stats && (
          <div>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={8}>
                <Statistic title="总反馈数" value={stats.total} />
              </Col>
              <Col span={8}>
                <Statistic title="待处理" value={stats.by_status.open || 0} valueStyle={{ color: "#1890ff" }} />
              </Col>
              <Col span={8}>
                <Statistic title="已解决" value={stats.by_status.resolved || 0} valueStyle={{ color: "#52c41a" }} />
              </Col>
            </Row>
            <h4>按分类</h4>
            <Row gutter={[8, 8]} style={{ marginBottom: 16 }}>
              {Object.entries(stats.by_category).map(([key, count]) => (
                <Col key={key} span={8}>
                  <Card size="small">
                    <Statistic
                      title={categoryConfig[key]?.label || key}
                      value={count}
                      valueStyle={{ fontSize: 20 }}
                    />
                  </Card>
                </Col>
              ))}
            </Row>
            {stats.by_submitter.length > 0 && (
              <>
                <h4>按提交者</h4>
                {stats.by_submitter.map((s) => (
                  <div key={s.submitter} style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <Text>{s.submitter}</Text>
                    <Text strong>{s.count}</Text>
                  </div>
                ))}
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
