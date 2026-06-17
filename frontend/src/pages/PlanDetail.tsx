import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  Descriptions,
  Tag,
  Button,
  List,
  Checkbox,
  Modal,
  Form,
  Input,
  message,
  Space,
  Divider,
} from "antd";
import { ArrowLeftOutlined, PlusOutlined, CheckOutlined, CloseOutlined, RobotOutlined } from "@ant-design/icons";
import { plansApi } from "../api/plans";
import type { Plan, PlanItem } from "../api";

const statusColors: Record<string, string> = {
  pending: "warning",
  approved: "processing",
  rejected: "default",
  in_progress: "processing",
  done: "success",
};

export default function PlanDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [items, setItems] = useState<PlanItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [itemModalOpen, setItemModalOpen] = useState(false);
  const [itemForm] = Form.useForm();

  const fetchPlan = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [planRes, itemsRes] = await Promise.all([
        plansApi.get(Number(id)),
        plansApi.listItems(Number(id)),
      ]);
      setPlan(planRes.data);
      setItems(itemsRes.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlan();
  }, [id]);

  const handleApprove = async () => {
    if (!id) return;
    try {
      await plansApi.approve(Number(id));
      message.success("审批通过");
      fetchPlan();
    } catch {
      message.error("审批失败");
    }
  };

  const handleReject = async () => {
    if (!id) return;
    try {
      await plansApi.reject(Number(id));
      message.success("已拒绝");
      fetchPlan();
    } catch {
      message.error("操作失败");
    }
  };

  const handleCreateItem = async (values: any) => {
    if (!id) return;
    try {
      await plansApi.createItem(Number(id), values);
      message.success("添加成功");
      setItemModalOpen(false);
      itemForm.resetFields();
      fetchPlan();
    } catch {
      message.error("添加失败");
    }
  };

  const handleToggleItem = async (item: PlanItem) => {
    const newStatus = item.status === "done" ? "pending" : "done";
    try {
      await plansApi.updateItem(item.plan_id, item.id, {
        status: newStatus,
        completed_by: newStatus === "done" ? "user" : undefined,
        completed_at: newStatus === "done" ? new Date().toISOString() : undefined,
      });
      fetchPlan();
    } catch {
      message.error("更新失败");
    }
  };

  if (!plan) return <div style={{ padding: 40 }}>加载中...</div>;

  const doneCount = items.filter((i) => i.status === "done").length;

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/plans")} style={{ marginBottom: 16 }}>
        返回
      </Button>

      <Card
        title={
          <Space>
            {plan.title}
            <Tag color={statusColors[plan.status]}>{plan.status}</Tag>
            {plan.proposed_by === "ai_agent" && <Tag icon={<RobotOutlined />} color="purple">AI Agent</Tag>}
          </Space>
        }
        extra={
          plan.status === "pending" ? (
            <Space>
              <Button type="primary" icon={<CheckOutlined />} onClick={handleApprove}>
                审批通过
              </Button>
              <Button icon={<CloseOutlined />} danger onClick={handleReject}>
                拒绝
              </Button>
            </Space>
          ) : null
        }
        loading={loading}
      >
        <Descriptions bordered column={2}>
          <Descriptions.Item label="描述" span={2}>
            {plan.description || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="提议者">{plan.proposed_by}</Descriptions.Item>
          <Descriptions.Item label="审批人">{plan.approved_by || "-"}</Descriptions.Item>
          <Descriptions.Item label="审批时间">{plan.approved_at || "-"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{plan.created_at}</Descriptions.Item>
        </Descriptions>

        <Divider />

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h4 style={{ margin: 0 }}>
            计划项 Checklist
            <Tag style={{ marginLeft: 8 }}>
              {doneCount}/{items.length} 完成
            </Tag>
          </h4>
          <Button type="primary" icon={<PlusOutlined />} size="small" onClick={() => setItemModalOpen(true)}>
            添加项
          </Button>
        </div>

        <List
          dataSource={items}
          renderItem={(item) => (
            <List.Item
              actions={[
                item.completed_by && (
                  <Tag color="purple" style={{ fontSize: 12 }}>
                    {item.completed_by === "ai_agent" ? "AI" : "用户"}
                  </Tag>
                ),
              ]}
            >
              <Checkbox
                checked={item.status === "done"}
                onChange={() => handleToggleItem(item)}
              >
                <span style={{ textDecoration: item.status === "done" ? "line-through" : "none", color: item.status === "done" ? "#999" : undefined }}>
                  {item.title}
                </span>
              </Checkbox>
            </List.Item>
          )}
        />
      </Card>

      <Modal title="添加计划项" open={itemModalOpen} onCancel={() => setItemModalOpen(false)} onOk={() => itemForm.submit()}>
        <Form form={itemForm} onFinish={handleCreateItem} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
