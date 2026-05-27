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
} from "antd";
import {
  PlusOutlined,
  FolderOpenOutlined,
  EditOutlined,
  DeleteOutlined,
} from "@ant-design/icons";
import { projectRegistrationsApi, type ProjectRegistration, type ProjectRegistrationCreate, type ProjectRegistrationUpdate } from "../api/projectRegistrations";

const { Text } = Typography;

const statusColors: Record<string, string> = {
  active: "green",
  archived: "default",
  stale: "orange",
};

export default function ProjectRegistrations() {
  const [registrations, setRegistrations] = useState<ProjectRegistration[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("active");
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingReg, setEditingReg] = useState<ProjectRegistration | null>(null);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  const fetch = async (p = page, status = statusFilter) => {
    setLoading(true);
    try {
      const params: Record<string, any> = { skip: (p - 1) * 50, limit: 50 };
      if (status) params.status = status;
      const data = await projectRegistrationsApi.list(params);
      setRegistrations(data.items);
      setTotal(data.total);
    } catch {
      message.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, [page, statusFilter]);

  const handleCreate = async (values: ProjectRegistrationCreate) => {
    try {
      await projectRegistrationsApi.create(values);
      message.success("登记成功");
      setCreateOpen(false);
      createForm.resetFields();
      fetch();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      message.error(detail || "登记失败");
    }
  };

  const handleEdit = async (values: ProjectRegistrationUpdate) => {
    if (!editingReg) return;
    try {
      await projectRegistrationsApi.update(editingReg.id, values);
      message.success("更新成功");
      setEditOpen(false);
      setEditingReg(null);
      editForm.resetFields();
      fetch();
    } catch {
      message.error("更新失败");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await projectRegistrationsApi.delete(id);
      message.success("删除成功");
      fetch();
    } catch {
      message.error("删除失败");
    }
  };

  const openEdit = (reg: ProjectRegistration) => {
    setEditingReg(reg);
    editForm.setFieldsValue({
      name: reg.name,
      description: reg.description || "",
      tech_stack: reg.tech_stack || "",
      repo_url: reg.repo_url || "",
      language: reg.language || "",
      framework: reg.framework || "",
      status: reg.status,
      notes: reg.notes || "",
    });
    setEditOpen(true);
  };

  const columns = [
    {
      title: "项目名称",
      dataIndex: "name",
      width: 180,
      render: (text: string) => (
        <Space>
          <FolderOpenOutlined />
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: "路径",
      dataIndex: "path",
      ellipsis: true,
      render: (text: string) => (
        <Text code style={{ fontSize: 12 }}>{text}</Text>
      ),
    },
    {
      title: "语言/框架",
      width: 160,
      render: (_: any, record: ProjectRegistration) => (
        <Space size={4}>
          {record.language && <Tag>{record.language}</Tag>}
          {record.framework && <Tag color="blue">{record.framework}</Tag>}
        </Space>
      ),
    },
    {
      title: "技术栈",
      dataIndex: "tech_stack",
      width: 160,
      ellipsis: true,
      render: (text: string | null) =>
        text ? (
          <Space size={4}>
            {text.split(",").map((t) => (
              <Tag key={t.trim()} style={{ fontSize: 11 }}>{t.trim()}</Tag>
            ))}
          </Space>
        ) : "-",
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 80,
      render: (s: string) => <Tag color={statusColors[s]}>{s}</Tag>,
    },
    {
      title: "登记人",
      dataIndex: "registered_by",
      width: 100,
      render: (t: string | null) => t || "-",
    },
    {
      title: "操作",
      width: 120,
      render: (_: any, record: ProjectRegistration) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger size="small" icon={<DeleteOutlined />}>
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
        <h2 style={{ margin: 0 }}>
          <FolderOpenOutlined style={{ marginRight: 8 }} />
          项目登记
        </h2>
        <Space>
          <Select
            value={statusFilter}
            onChange={(v) => { setStatusFilter(v); setPage(1); }}
            style={{ width: 120 }}
            options={[
              { value: "active", label: "活跃" },
              { value: "archived", label: "归档" },
              { value: "stale", label: "过期" },
              { value: "", label: "全部" },
            ]}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            登记项目
          </Button>
        </Space>
      </div>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={registrations}
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 50,
          onChange: (p) => setPage(p),
          showTotal: (t) => `共 ${t} 项`,
          size: "small",
        }}
      />

      {/* 新建弹窗 */}
      <Modal title="登记项目" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={() => createForm.submit()}>
        <Form form={createForm} onFinish={handleCreate} layout="vertical">
          <Form.Item name="name" label="项目名称" rules={[{ required: true }]}>
            <Input placeholder="如 my-project" />
          </Form.Item>
          <Form.Item name="path" label="项目路径" rules={[{ required: true }]}>
            <Input placeholder="如 D:/Projects/my-project" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="项目简介" />
          </Form.Item>
          <Form.Item name="language" label="主要语言">
            <Input placeholder="如 Python, TypeScript" />
          </Form.Item>
          <Form.Item name="framework" label="框架">
            <Input placeholder="如 FastAPI, Next.js" />
          </Form.Item>
          <Form.Item name="tech_stack" label="技术栈">
            <Input placeholder="逗号分隔，如 Python,React,SQLite" />
          </Form.Item>
          <Form.Item name="repo_url" label="仓库地址">
            <Input placeholder="https://github.com/..." />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑弹窗 */}
      <Modal title="编辑项目" open={editOpen} onCancel={() => { setEditOpen(false); setEditingReg(null); }} onOk={() => editForm.submit()}>
        <Form form={editForm} onFinish={handleEdit} layout="vertical">
          <Form.Item name="name" label="项目名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="language" label="主要语言">
            <Input />
          </Form.Item>
          <Form.Item name="framework" label="框架">
            <Input />
          </Form.Item>
          <Form.Item name="tech_stack" label="技术栈">
            <Input placeholder="逗号分隔" />
          </Form.Item>
          <Form.Item name="repo_url" label="仓库地址">
            <Input />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select>
              <Select.Option value="active">active</Select.Option>
              <Select.Option value="archived">archived</Select.Option>
              <Select.Option value="stale">stale</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
