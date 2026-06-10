import { useState } from "react";
import { Table, Tag, Button, Space, Modal, Form, Input, Select, message, Popconfirm, Progress } from "antd";
import { PlusOutlined, CheckOutlined, CloseOutlined, RobotOutlined, TeamOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { plansApi } from "../api/plans";
import type { Plan } from "../api/plans";
import { useProject } from "../hooks/useProject";
import { usePlans } from "../hooks/usePlans";
import LoadingState from "../components/ui/LoadingState";
import ErrorState from "../components/ui/ErrorState";
import { queryClient } from "../queries/queryClient";
import { planKeys } from "../queries/planQueries";

const { Option } = Select;

const statusColors: Record<string, string> = {
  draft: "default",
  pending_approval: "warning",
  active: "processing",
  completed: "success",
  abandoned: "default",
};

export default function Plans() {
  const navigate = useNavigate();
  const { currentProject } = useProject();
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const { data: plans, isLoading, error } = usePlans(currentProject?.id);

  if (isLoading) {
    return <LoadingState message="加载 Plans..." />;
  }

  if (error) {
    return (
      <ErrorState
        error={error}
        onRetry={() => queryClient.invalidateQueries({ queryKey: planKeys.all })}
      />
    );
  }

  const handleCreate = async (values: any) => {
    try {
      const payload = { ...values };
      if (currentProject) payload.project_id = currentProject.id;
      await plansApi.create(payload);
      message.success("创建成功");
      setModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: planKeys.all });
    } catch {
      message.error("创建失败");
    }
  };

  const handleApprove = async (id: number) => {
    try {
      await plansApi.approve(id);
      message.success("审批通过");
      queryClient.invalidateQueries({ queryKey: planKeys.all });
    } catch {
      message.error("审批失败");
    }
  };

  const handleReject = async (id: number) => {
    Modal.confirm({
      title: "拒绝计划",
      content: "确认拒绝此计划？",
      okText: "确认拒绝",
      okType: "danger",
      onOk: async () => {
        try {
          await plansApi.reject(id);
          message.success("已拒绝");
          queryClient.invalidateQueries({ queryKey: planKeys.all });
        } catch {
          message.error("操作失败");
        }
      },
    });
  };

  const handleDelete = async (id: number) => {
    try {
      await plansApi.remove(id);
      message.success("删除成功");
      queryClient.invalidateQueries({ queryKey: planKeys.all });
    } catch {
      message.error("删除失败");
    }
  };

  const columns = [
    {
      title: "标题",
      dataIndex: "title",
      render: (text: string, record: Plan) => (
        <a onClick={() => navigate(currentProject ? `/projects/${currentProject.slug}/plans/${record.id}` : `/plans/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 120,
      render: (s: string) => <Tag color={statusColors[s]}>{s}</Tag>,
    },
    {
      title: "提议者",
      dataIndex: "proposed_by",
      width: 120,
      render: (s: string) => {
        if (s === "ai_agent") return <Tag icon={<RobotOutlined />} color="purple">AI</Tag>;
        if (s === "collaborative") return <Tag icon={<TeamOutlined />} color="cyan">协作</Tag>;
        return <Tag>用户</Tag>;
      },
    },
    {
      title: "审批人",
      dataIndex: "approved_by",
      width: 100,
      render: (s?: string) => s || "-",
    },
    {
      title: "进度",
      width: 140,
      render: (_: any, record: Plan) => {
        const total = record.item_count ?? 0;
        const done = record.item_done_count ?? 0;
        if (total === 0) return <span style={{ color: "#999" }}>无任务</span>;
        const percent = Math.round((done / total) * 100);
        return <Progress percent={percent} size="small" format={() => `${done}/${total}`} />;
      },
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 180,
    },
    {
      title: "操作",
      width: 200,
      render: (_: any, record: Plan) => (
        <Space>
          {record.status === "pending_approval" && (
            <>
              <Button
                type="primary"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => handleApprove(record.id)}
              >
                通过
              </Button>
              <Button
                size="small"
                icon={<CloseOutlined />}
                danger
                onClick={() => handleReject(record.id)}
              >
                拒绝
              </Button>
            </>
          )}
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger size="small">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <h2>Plans</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          新建 Plan
        </Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={plans || []} loading={isLoading} pagination={{ pageSize: 20 }} />

      <Modal title="新建 Plan" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} onFinish={handleCreate} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue="draft">
            <Select>
              <Option value="draft">draft</Option>
              <Option value="active">active</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
