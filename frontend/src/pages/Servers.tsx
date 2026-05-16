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
  Descriptions,
} from "antd";
import {
  PlusOutlined,
  CloudServerOutlined,
  KeyOutlined,
  LockOutlined,
} from "@ant-design/icons";
import { serversApi } from "../api/servers";
import type { Server, ServerCredentials } from "../api";
import { useProject } from "../hooks/useProject";

const { Option } = Select;

const statusColors: Record<string, string> = {
  active: "success",
  maintenance: "warning",
  offline: "error",
  decommissioned: "default",
};

const envColors: Record<string, string> = {
  production: "red",
  staging: "orange",
  development: "blue",
};

export default function Servers() {
  const { currentProject } = useProject();
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [credOpen, setCredOpen] = useState(false);
  const [credentials, setCredentials] = useState<ServerCredentials | null>(null);
  const [form] = Form.useForm();

  const fetch = async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = {};
      if (currentProject) params.project_id = currentProject.id;
      const res = await serversApi.list(params);
      setServers(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, [currentProject]);

  const handleCreate = async (values: any) => {
    try {
      const payload = { ...values };
      if (currentProject) payload.project_id = currentProject.id;
      await serversApi.create(payload);
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
      await serversApi.remove(id);
      message.success("删除成功");
      fetch();
    } catch {
      message.error("删除失败");
    }
  };

  const handleViewCredentials = async (id: number) => {
    try {
      const res = await serversApi.getCredentials(id);
      setCredentials(res.data);
      setCredOpen(true);
    } catch {
      message.error("获取凭据失败");
    }
  };

  const columns = [
    {
      title: "名称",
      dataIndex: "name",
      render: (text: string, _record: Server) => (
        <Space>
          <CloudServerOutlined />
          <span>{text}</span>
        </Space>
      ),
    },
    {
      title: "IP",
      dataIndex: "ip_address",
      width: 140,
      render: (s?: string) => s || "-",
    },
    {
      title: "端口",
      dataIndex: "port",
      width: 80,
      render: (s?: number) => s ?? "-",
    },
    {
      title: "类型",
      dataIndex: "server_type",
      width: 80,
    },
    {
      title: "环境",
      dataIndex: "environment",
      width: 100,
      render: (s: string) => <Tag color={envColors[s]}>{s}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      render: (s: string) => <Tag color={statusColors[s]}>{s}</Tag>,
    },
    {
      title: "凭据",
      width: 100,
      render: (_: any, record: Server) => (
        <Space size={4}>
          {record.has_password && <Tag icon={<LockOutlined />} color="blue">密码</Tag>}
          {record.has_ssh_key && <Tag icon={<KeyOutlined />} color="purple">SSH</Tag>}
          {!record.has_password && !record.has_ssh_key && <span style={{ color: "#999" }}>无</span>}
        </Space>
      ),
    },
    {
      title: "操作",
      width: 200,
      render: (_: any, record: Server) => (
        <Space>
          {(record.has_password || record.has_ssh_key) && (
            <Button type="link" size="small" onClick={() => handleViewCredentials(record.id)}>
              查看凭据
            </Button>
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
        <h2>Servers</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          添加服务器
        </Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={servers} loading={loading} pagination={{ pageSize: 20 }} />

      <Modal
        title="添加服务器"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} onFinish={handleCreate} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="ip_address" label="IP 地址">
            <Input />
          </Form.Item>
          <Form.Item name="port" label="端口">
            <Input type="number" />
          </Form.Item>
          <Form.Item name="username" label="用户名">
            <Input />
          </Form.Item>
          <Form.Item name="password" label="密码">
            <Input.Password />
          </Form.Item>
          <Form.Item name="ssh_key" label="SSH Key">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="server_type" label="类型" initialValue="other">
            <Select>
              <Option value="web">web</Option>
              <Option value="db">db</Option>
              <Option value="cache">cache</Option>
              <Option value="worker">worker</Option>
              <Option value="other">other</Option>
            </Select>
          </Form.Item>
          <Form.Item name="environment" label="环境" initialValue="development">
            <Select>
              <Option value="production">production</Option>
              <Option value="staging">staging</Option>
              <Option value="development">development</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="服务器凭据"
        open={credOpen}
        onCancel={() => setCredOpen(false)}
        footer={null}
      >
        {credentials && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="名称">{credentials.name}</Descriptions.Item>
            <Descriptions.Item label="IP">{credentials.ip_address || "-"}</Descriptions.Item>
            <Descriptions.Item label="端口">{credentials.port ?? "-"}</Descriptions.Item>
            <Descriptions.Item label="用户名">{credentials.username || "-"}</Descriptions.Item>
            <Descriptions.Item label="密码">
              {credentials.password ? <Input.Password defaultValue={credentials.password} readOnly /> : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="SSH Key">
              {credentials.ssh_key ? (
                <Input.TextArea defaultValue={credentials.ssh_key} readOnly rows={3} />
              ) : (
                "-"
              )}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
}
