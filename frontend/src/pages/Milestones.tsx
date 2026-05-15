import { useEffect, useState } from "react";
import { Card, Row, Col, Tag, Button, Modal, Form, Input, DatePicker, message, Popconfirm, Statistic } from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { milestonesApi } from "../api/milestones";
import type { MilestoneWithStats } from "../api";

export default function Milestones() {
  const [milestones, setMilestones] = useState<MilestoneWithStats[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetch = async () => {
    setLoading(true);
    try {
      const listRes = await milestonesApi.list();
      const withStats = await Promise.all(
        listRes.data.map(async (m) => {
          const detailRes = await milestonesApi.get(m.id);
          return detailRes.data;
        })
      );
      setMilestones(withStats);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, []);

  const handleCreate = async (values: any) => {
    try {
      await milestonesApi.create({
        ...values,
        due_date: values.due_date?.format("YYYY-MM-DD"),
      });
      message.success("创建成功");
      setModalOpen(false);
      form.resetFields();
      fetch();
    } catch {
      message.error("创建失败");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await milestonesApi.remove(id);
      message.success("删除成功");
      fetch();
    } catch {
      message.error("删除失败");
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <h2>Milestones</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          新建 Milestone
        </Button>
      </div>

      <Row gutter={[16, 16]}>
        {milestones.map((m) => (
          <Col span={8} key={m.id}>
            <Card
              title={
                <span>
                  {m.title}
                  <Tag color={m.status === "open" ? "green" : "default"} style={{ marginLeft: 8 }}>
                    {m.status}
                  </Tag>
                  {m.phase && <Tag style={{ marginLeft: 8 }}>{m.phase}</Tag>}
                </span>
              }
              extra={
                <Popconfirm title="确认删除？" onConfirm={() => handleDelete(m.id)}>
                  <Button type="link" danger icon={<DeleteOutlined />} size="small" />
                </Popconfirm>
              }
              loading={loading}
            >
              <p style={{ color: "#666", minHeight: 40 }}>{m.description || "无描述"}</p>
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic title="总 Issues" value={m.total_issues} valueStyle={{ fontSize: 20 }} />
                </Col>
                <Col span={8}>
                  <Statistic title="进行中" value={m.open_issues} valueStyle={{ fontSize: 20, color: "#1890ff" }} />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="已暂缓"
                    value={m.deferred_issues}
                    valueStyle={{ fontSize: 20, color: "#faad14" }}
                  />
                </Col>
              </Row>
              {m.due_date && <p style={{ marginTop: 8, color: "#999" }}>截止: {m.due_date}</p>}
            </Card>
          </Col>
        ))}
      </Row>

      {milestones.length === 0 && !loading && (
        <div style={{ textAlign: "center", padding: 60, color: "#999" }}>暂无 Milestone</div>
      )}

      <Modal title="新建 Milestone" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} onFinish={handleCreate} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="phase" label="分期标识">
            <Input placeholder="如 phase-1, MVP" />
          </Form.Item>
          <Form.Item name="due_date" label="截止日期">
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
