import { useEffect, useState } from "react";
import { Table, Tag, Button, Space, Modal, Form, Input, Select, message, Popconfirm, Card, Row, Col, Statistic, Typography } from "antd";
import { PlusOutlined, CheckCircleOutlined, DeleteOutlined, WarningOutlined, ExclamationCircleOutlined } from "@ant-design/icons";
import { riskAlertsApi, type RiskAlert, type RiskAlertCreate } from "../api/riskAlerts";

const { TextArea } = Input;
const { Text } = Typography;

const levelConfig: Record<string, { label: string; color: string }> = {
  critical: { label: "严重", color: "red" },
  high: { label: "高", color: "orange" },
  medium: { label: "中", color: "gold" },
  low: { label: "低", color: "blue" },
};

const statusConfig: Record<string, { label: string; color: string }> = {
  open: { label: "待处理", color: "blue" },
  acknowledged: { label: "已确认", color: "orange" },
  resolved: { label: "已解决", color: "green" },
  dismissed: { label: "已忽略", color: "default" },
};

const sourceConfig: Record<string, { label: string; color: string }> = {
  manual: { label: "手动", color: "default" },
  copilot: { label: "Copilot", color: "purple" },
  system: { label: "系统", color: "cyan" },
};

export default function RiskAlerts() {
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [levelFilter, setLevelFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm();

  const fetchAlerts = async (p = page, level = levelFilter, status = statusFilter) => {
    setLoading(true);
    try {
      const params: Record<string, any> = { skip: (p - 1) * 20, limit: 20 };
      if (level) params.level = level;
      if (status) params.status = status;
      const res = await riskAlertsApi.list(params);
      setAlerts(res.data.items);
      setTotal(res.data.total);
    } catch {
      message.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAlerts(); }, [page]);

  const handleCreate = async (values: RiskAlertCreate) => {
    try {
      await riskAlertsApi.create(values);
      message.success("创建成功");
      setCreateOpen(false);
      createForm.resetFields();
      fetchAlerts(1);
    } catch {
      message.error("创建失败");
    }
  };

  const handleResolve = async (id: number) => {
    try {
      await riskAlertsApi.resolve(id);
      message.success("已标记解决");
      fetchAlerts();
    } catch {
      message.error("操作失败");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await riskAlertsApi.remove(id);
      message.success("已删除");
      fetchAlerts();
    } catch {
      message.error("删除失败");
    }
  };

  const openCount = alerts.filter(a => a.status === "open").length;
  const criticalCount = alerts.filter(a => a.level === "critical" && a.status !== "resolved").length;

  const columns = [
    {
      title: "级别",
      dataIndex: "level",
      width: 80,
      render: (l: string) => {
        const cfg = levelConfig[l] || { label: l, color: "default" };
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: "标题",
      dataIndex: "title",
      ellipsis: true,
      render: (t: string, record: RiskAlert) => (
        <Space>
          {record.level === "critical" && <ExclamationCircleOutlined style={{ color: "#ff4d4f" }} />}
          <Text strong={record.status === "open"}>{t}</Text>
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      render: (s: string) => {
        const cfg = statusConfig[s] || { label: s, color: "default" };
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: "来源",
      dataIndex: "source",
      width: 100,
      render: (s: string) => {
        const cfg = sourceConfig[s] || { label: s, color: "default" };
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 160,
      render: (t: string) => t ? new Date(t).toLocaleString("zh-CN") : "-",
    },
    {
      title: "操作",
      width: 160,
      render: (_: unknown, record: RiskAlert) => (
        <Space>
          {record.status !== "resolved" && (
            <Button type="link" size="small" icon={<CheckCircleOutlined />} onClick={() => handleResolve(record.id)}>
              解决
            </Button>
          )}
          <Popconfirm title="确认删除?" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="待处理" value={openCount} prefix={<WarningOutlined />} valueStyle={{ color: openCount > 0 ? "#faad14" : undefined }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="严重告警" value={criticalCount} prefix={<ExclamationCircleOutlined />} valueStyle={{ color: criticalCount > 0 ? "#ff4d4f" : undefined }} />
          </Card>
        </Col>
      </Row>

      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Space>
          <Select placeholder="级别" allowClear style={{ width: 100 }} value={levelFilter} onChange={(v) => { setLevelFilter(v); setPage(1); fetchAlerts(1, v, statusFilter); }}>
            {Object.entries(levelConfig).map(([k, v]) => <Select.Option key={k} value={k}>{v.label}</Select.Option>)}
          </Select>
          <Select placeholder="状态" allowClear style={{ width: 100 }} value={statusFilter} onChange={(v) => { setStatusFilter(v); setPage(1); fetchAlerts(1, levelFilter, v); }}>
            {Object.entries(statusConfig).map(([k, v]) => <Select.Option key={k} value={k}>{v.label}</Select.Option>)}
          </Select>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新建告警</Button>
      </div>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={alerts}
        loading={loading}
        pagination={{ current: page, pageSize: 20, total, onChange: setPage }}
        size="middle"
      />

      <Modal title="新建风险告警" open={createOpen} onCancel={() => { setCreateOpen(false); createForm.resetFields(); }} onOk={() => createForm.submit()} destroyOnClose>
        <Form form={createForm} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="title" label="标题" rules={[{ required: true, message: "请输入标题" }]}>
            <Input maxLength={300} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} />
          </Form.Item>
          <Form.Item name="level" label="级别" initialValue="medium">
            <Select>
              {Object.entries(levelConfig).map(([k, v]) => <Select.Option key={k} value={k}>{v.label}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="source" label="来源" initialValue="manual">
            <Select>
              {Object.entries(sourceConfig).map(([k, v]) => <Select.Option key={k} value={k}>{v.label}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="suggested_action" label="建议措施">
            <TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
